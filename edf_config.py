import numpy as np
import matplotlib.pyplot as plt
import os
import math

try:
    from uav_parameters import FixedWingParameters
    from lipo import Battery
    from edf_speed import estimate_modified_cruise_speed
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import required modules. {e}")
    exit()

# Represents a realistic assumption for EDF propulsive efficiency during the design phase.
PROPULSIVE_EFFICIENCY_ASSUMPTION = 0.60

class EDF:
    def __init__(self, name: str, power_w: float, static_thrust_n: float, weight_kg: float, diameter_m: float):
        self.name, self.power_w, self.static_thrust_n, self.weight_kg, self.diameter_m = name, power_w, static_thrust_n, weight_kg, diameter_m
        self.design_speed_mps = 25 + (self.power_w / 150)

    @classmethod
    def from_power(cls, power_w: float):
        name = f"{power_w/1000:.1f}kW EDF"
        weight_kg = 0.05 + 0.020 * (power_w ** 0.75)
        static_thrust_n = 0.7 * (power_w ** 0.88)
        # Estimate diameter based on power (Area ~ Thrust ~ Power^0.88 => Diameter ~ Power^0.44)
        diameter_m = 0.03 * (power_w ** 0.44)
        return cls(name, power_w, static_thrust_n, weight_kg, diameter_m)

    def get_propulsive_efficiency(self, tas_mps: float) -> float:
        """Models a wider, more realistic efficiency curve for the EDF."""
        speed_ratio = tas_mps / self.design_speed_mps
        # Widened the efficiency curve by changing denominator from 0.5 to 0.8
        return max(0.1, 0.70 * math.exp(-((speed_ratio - 1)**2) / 0.8))

class Aircraft:
    def __init__(self, edf: EDF, battery: Battery, params: FixedWingParameters):
        self.edf, self.battery, self.params = edf, battery, params

        self.battery.check_power_output(self.edf.power_w)
        power_system_weight = self.edf.weight_kg + self.battery.weight_kg

        # The original airframe weight model was unstable for large power systems.
        # It could produce negative weight multipliers. Replaced with a simple linear factor.
        # Per user feedback, reducing this ratio to make the airframe lighter.
        airframe_to_power_system_ratio = 0.8
        self.airframe_weight_kg = 0.4 + (power_system_weight * airframe_to_power_system_ratio)
        empty_weight_kg = self.edf.weight_kg + self.battery.weight_kg + self.airframe_weight_kg
        
        # Decouple payload from empty weight to break feedback loop. Base it on power class instead.
        self.payload_weight_kg = 0.20 * (self.edf.power_w / 100)
        self.mtow_kg = empty_weight_kg + self.payload_weight_kg
        self.weight_n = self.mtow_kg * 9.80665

        self.thrust_to_weight_ratio = self.edf.static_thrust_n / self.weight_n
        self.ld_ratio = 7.0 + (self.params.endurance.percent / 100.0) * 5.0
        self.cruise_ias_kts = estimate_modified_cruise_speed(edf.power_w, params)
        self.cruise_ias_mps = self.cruise_ias_kts * 0.514444
        
        self.wing_area_m2 = (2 * self.weight_n) / (1.225 * self.cruise_ias_mps**2 * 0.4)
        self.stall_speed_ias_mps = math.sqrt((2 * self.weight_n) / (1.225 * self.wing_area_m2 * 1.5))
        self.vr_ias_mps = self.stall_speed_ias_mps * 1.10
        # Per user feedback, Vy was overestimated for a prop-driven aircraft.
        # Reducing the factor from 1.40 (jet-like) to 1.20 (prop-like).
        self.vy_ias_mps = self.stall_speed_ias_mps * 1.20
        self.best_glide_ias_mps = self.stall_speed_ias_mps * 1.31

        # --- FINAL PERFORMANCE CALCULATION (Now with a correctly sized motor) ---
        self.rate_of_climb_fpm = self.calculate_rate_of_climb()

        # Correctly calculate the cruise power percentage.
        # This was previously comparing aerodynamic power to electric power, missing the efficiency term.
        power_required_aero_cruise = (self.weight_n / self.ld_ratio) * self.cruise_ias_mps
        power_required_elec_cruise = power_required_aero_cruise / self.edf.get_propulsive_efficiency(self.cruise_ias_mps)
        self.cruise_power_percent = (power_required_elec_cruise / self.edf.power_w) * 100

        if self.cruise_power_percent > 90.0:
            # print(f"DEBUG: {self.params.name} cruise requires {self.cruise_power_percent:.1f}% power, which is > 90%.")
            pass

        if self.thrust_to_weight_ratio < 0.3:
            # print(f"DEBUG: {self.params.name} has a TWR of {self.thrust_to_weight_ratio:.2f}, which is < 0.3.")
            pass

    @classmethod
    def with_virtual_battery(cls, edf: EDF, params: FixedWingParameters, c_rating: int, b_m_ratio: float):
        """Creates an Aircraft instance with a virtual battery estimated from EDF and rules."""
        battery_weight_kg = edf.weight_kg * b_m_ratio
        virtual_battery = Battery.from_c_and_weight(c_rating=c_rating, max_weight_kg=battery_weight_kg)
        return cls(edf, virtual_battery, params)

    def calculate_rate_of_climb(self):
        """Calculates the rate of climb in FPM and prints debug info if ROC is zero."""
        power_available_climb = self.edf.power_w * self.edf.get_propulsive_efficiency(self.vy_ias_mps)
        
        d_min_n = self.weight_n / self.ld_ratio
        v_ratio = self.vy_ias_mps / self.best_glide_ias_mps if self.best_glide_ias_mps > 0 else 1
        drag_at_vy = d_min_n * 0.5 * (v_ratio**2 + (1/v_ratio)**2)
        power_required_climb = drag_at_vy * self.vy_ias_mps

        excess_power_watts = power_available_climb - power_required_climb
        rate_of_climb_fpm = max(0, (excess_power_watts / self.weight_n) * 196.85)

        if rate_of_climb_fpm == 0:
            print(f"\n--- ROC DEBUG for {self.params.name} (ROC is Zero) ---")
            print(f"  Motor Power (W): {self.edf.power_w:.2f}")
            print(f"  Vy (m/s): {self.vy_ias_mps:.2f}")
            print(f"  Propulsive Eff @ Vy: {self.edf.get_propulsive_efficiency(self.vy_ias_mps):.3f}")
            print(f"  Power Available Climb (W): {power_available_climb:.2f}")
            print(f"  Weight (N): {self.weight_n:.2f}")
            print(f"  L/D Ratio: {self.ld_ratio:.2f}")
            print(f"  Best Glide Speed (m/s): {self.best_glide_ias_mps:.2f}")
            print(f"  Drag @ Vy (N): {drag_at_vy:.2f}")
            print(f"  Power Required Climb (W): {power_required_climb:.2f}")
            print(f"  Excess Power (W): {excess_power_watts:.2f}")
            print(f"--- END ROC DEBUG ---")
            
        return rate_of_climb_fpm

    @classmethod
    def design_from_mission(cls, params: FixedWingParameters, rules: dict, initial_mtow_guess_kg: float, battery: Battery):
        """
        This revised design method re-introduces a fixed cruise speed calculated from the start,
        which was found to be critical for maintaining realistic airspeed scaling (Vs, Vr, Vy, etc.).
        The convergence loop was made more robust by refining the aerodynamic power calculation
        and ensuring the propulsive efficiency is estimated at the correct, fixed cruise speed.
        This prevents the model from diverging into unrealistic flight regimes.
        """
        mtow_guess_kg = initial_mtow_guess_kg

        # FIX: Re-establish a fixed cruise speed based on the initial weight class.
        # This is essential for maintaining realistic scaling between different operational airspeeds.
        # The dynamic calculation within the loop was making the model unstable.
        representative_notional_power = initial_mtow_guess_kg * (220 if rules["cruise_power_target"] > 80 else 150)
        cruise_ias_kts = estimate_modified_cruise_speed(representative_notional_power, params)
        cruise_ias_mps = cruise_ias_kts * 0.514444

        # Estimate the propulsive efficiency for the target cruise speed *once*.
        # This requires a notional motor to get a representative efficiency curve.
        notional_edf = EDF.from_power(representative_notional_power)
        propulsive_eff_at_cruise = notional_edf.get_propulsive_efficiency(cruise_ias_mps)

        for i in range(15):
            ld_ratio = 7.0 + (params.endurance.percent / 100.0) * 5.0
            
            # Calculate the required aerodynamic power at the *fixed* cruise speed.
            power_req_aero = ((mtow_guess_kg * 9.80665) / ld_ratio) * cruise_ias_mps
            
            # Use the pre-calculated propulsive efficiency to find the required *electrical* power.
            power_req_elec = power_req_aero / propulsive_eff_at_cruise
            
            target_cruise_power_ratio = rules["cruise_power_target"]
            required_motor_power_w = power_req_elec / (target_cruise_power_ratio / 100.0)
            
            edf = EDF.from_power(required_motor_power_w)
            
            # Create a temporary aircraft to find its new MTOW based on the required motor.
            temp_aircraft = cls(edf, battery, params)
            new_mtow_kg = temp_aircraft.mtow_kg
            
            if abs(new_mtow_kg - mtow_guess_kg) / mtow_guess_kg < 0.01:
                return temp_aircraft
            
            mtow_guess_kg = mtow_guess_kg * 0.5 + new_mtow_kg * 0.5
            
        # print(f"WARNING: Design for {params.name} did not converge. Final diff: {abs(new_mtow_kg - mtow_guess_kg):.2f} kg")
        return temp_aircraft

    def get_summary(self):
        speeds = f"Vs:{self.stall_speed_ias_mps*1.94:.0f}|Vr:{self.vr_ias_mps*1.94:.0f}|Vg:{self.best_glide_ias_mps*1.94:.0f}|Vy:{self.vy_ias_mps*1.94:.0f}|Vc:{self.cruise_ias_kts:.0f}"
        wing_loading_kg_m2 = self.mtow_kg / self.wing_area_m2 if self.wing_area_m2 > 0 else 0
        return [f"--- CONFIG: {'Endurance' if 'Endurance' in self.params.name else 'Sprint'} (Class: {self.edf.power_w/1000:.1f}kW) ---", f"  Performance: TWR {self.thrust_to_weight_ratio:.2f}, L/D {self.ld_ratio:.1f}, ROC: {self.rate_of_climb_fpm:.0f} FPM", f"  Speeds (kts): {speeds}", f"  Weights: MTOW {self.mtow_kg:.2f} kg, Wing Loading: {wing_loading_kg_m2:.2f} kg/m^2", f"  Power: Cruise requires {self.cruise_power_percent:.1f}% of rated motor power.", f"  Battery: {self.battery!r}"]

def generate_aircraft_scenarios():
    # This function is no longer compatible with the new Aircraft design process
    # and will be removed or refactored in a future version.
    # For now, it will return an empty list to avoid errors.
    return []

def plot_all_speeds(ax, aircraft_list):
    labels = [f"{ac.edf.power_w/1000:.1f}kW\n{'E' if 'Endurance' in ac.params.name else 'S'}" for ac in aircraft_list]
    x = np.arange(len(labels)); width = 0.15
    s_stall = [ac.stall_speed_ias_mps * 1.94384 for ac in aircraft_list]; s_rotate = [ac.vr_ias_mps * 1.94384 for ac in aircraft_list]; s_glide = [ac.best_glide_ias_mps * 1.94384 for ac in aircraft_list]; s_climb = [ac.vy_ias_mps * 1.94384 for ac in aircraft_list]; s_cruise = [ac.cruise_ias_kts for ac in aircraft_list]
    ax.bar(x - 2*width, s_stall, width, label='Vs'); ax.bar(x - width, s_rotate, width, label='Vr'); ax.bar(x, s_glide, width, label='Vg'); ax.bar(x + width, s_climb, width, label='Vy'); ax.bar(x + 2*width, s_cruise, width, label='Vc')
    ax.set_ylabel("Speed (knots IAS)"); ax.set_title("Operational Airspeeds"); ax.set_xticks(x, labels); ax.legend(); ax.grid(axis='y', linestyle='--', alpha=0.7)

def plot_rate_of_climb(ax, aircraft_list):
    labels = [f"{ac.edf.power_w/1000:.1f}kW\n{'E' if 'Endurance' in ac.params.name else 'S'}" for ac in aircraft_list]
    roc = [ac.rate_of_climb_fpm for ac in aircraft_list]; colors = ['blue' if 'E' in s else 'red' for s in labels]
    bars = ax.bar(labels, roc, color=colors); ax.bar_label(bars, fmt='%.0f')
    ax.set_ylabel("Rate of Climb (FPM)"); ax.set_title("Best Rate of Climb (at Vy)"); ax.grid(axis='y', linestyle='--', alpha=0.7)

def plot_mass_breakdown(ax, aircraft_list):
    labels = [f"{ac.edf.power_w/1000:.1f}kW\n{'E' if 'Endurance' in ac.params.name else 'S'}" for ac in aircraft_list]
    p = lambda w, m: w / m
    motor_p = [p(ac.edf.weight_kg, ac.mtow_kg) for ac in aircraft_list]; batt_p = [p(ac.battery.weight_kg, ac.mtow_kg) for ac in aircraft_list]; airframe_p = [p(ac.airframe_weight_kg, ac.mtow_kg) for ac in aircraft_list]; payload_p = [p(ac.payload_weight_kg, ac.mtow_kg) for ac in aircraft_list]
    ax.bar(labels, motor_p, label='Motor'); ax.bar(labels, batt_p, bottom=motor_p, label='Battery'); ax.bar(labels, airframe_p, bottom=np.array(motor_p)+np.array(batt_p), label='Airframe'); ax.bar(labels, payload_p, bottom=np.array(motor_p)+np.array(batt_p)+np.array(airframe_p), label='Payload')
    ax.set_ylabel("Mass Fraction"); ax.set_yticklabels(['{:,.0%}'.format(x) for x in ax.get_yticks()]); ax.set_title("MTOW Mass Fraction"); ax.legend()

def plot_cruise_power_level(ax, aircraft_list):
    labels = [f"{ac.edf.power_w/1000:.1f}kW\n{'E' if 'Endurance' in ac.params.name else 'S'}" for ac in aircraft_list]
    x = np.arange(len(labels))
    width = 0.25

    # Primary Y-axis: Cruise Power
    power_percent = [ac.cruise_power_percent for ac in aircraft_list]
    colors = ['blue' if 'E' in s else 'red' for s in labels]
    bars1 = ax.bar(x - width, power_percent, width, color=colors, label='Cruise Power %')
    ax.set_ylabel("Power Level (% of Max)", color='black')
    ax.tick_params(axis='y', labelcolor='black')
    ax.axhline(y=50, color='blue', linestyle='--', alpha=0.5)
    ax.axhline(y=90, color='red', linestyle='--', alpha=0.5)
    ax.bar_label(bars1, fmt='%.0f%%', label_type='edge', fontsize=8)

    # Secondary Y-axis: TWR and Wing Loading
    ax2 = ax.twinx()
    twr = [ac.thrust_to_weight_ratio for ac in aircraft_list]
    wing_loading = [ac.mtow_kg / ac.wing_area_m2 if ac.wing_area_m2 > 0 else 0 for ac in aircraft_list]
    
    bars2 = ax2.bar(x, twr, width, color='purple', alpha=0.6, label='TWR')
    bars3 = ax2.bar(x + width, wing_loading, width, color='green', alpha=0.6, label='Wing Loading (kg/m²)')
    
    ax2.set_ylabel("TWR & Wing Loading", color='black')
    ax2.tick_params(axis='y', labelcolor='black')
    ax2.bar_label(bars2, fmt='%.2f', label_type='edge', fontsize=8)
    ax2.bar_label(bars3, fmt='%.1f', label_type='edge', fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_title("Cruise Performance: Power, TWR, and Wing Loading")
    
    # Combine legends
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels + labels2, loc='upper left')
    
    ax.grid(axis='y', linestyle='--', alpha=0.7)

if __name__ == "__main__":
    os.makedirs('processed_uav_data', exist_ok=True)
    aircraft_to_analyze = generate_aircraft_scenarios()
    if aircraft_to_analyze:
        print("="*80, "\nGenerated Summaries (Corrected Top-Down Design)\n", "="*80)
        for ac in aircraft_to_analyze:
            for line in ac.get_summary(): print(line)
            print("-" * 40)

        fig, axes = plt.subplots(2, 2, figsize=(24, 16))
        plot_all_speeds(axes[0, 0], aircraft_to_analyze)
        plot_rate_of_climb(axes[0, 1], aircraft_to_analyze)
        plot_mass_breakdown(axes[1, 0], aircraft_to_analyze)
        plot_cruise_power_level(axes[1, 1], aircraft_to_analyze)
        
        fig.suptitle("UAV Design Analysis (Corrected Top-Down Mission Model)", fontsize=22)
        plt.tight_layout(rect=[0, 0.03, 1, 0.96])
        output_path = "processed_uav_data/final_mission_based_analysis.png"
        plt.savefig(output_path)
        print(f"\nGenerated analysis plots at: {output_path}")
        plt.show()
