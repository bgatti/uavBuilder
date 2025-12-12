# edf_mission.py (Updated for new physics model)

import numpy as np
import matplotlib.pyplot as plt
import os
import math

try:
    from edf_config import generate_aircraft_scenarios, Aircraft
except ImportError as e: exit(f"CRITICAL ERROR: {e}")

G = 9.80665; RHO_SL_KGM3 = 1.225

class FlightPath:
    def __init__(self):
        self.time_s, self.dist_m, self.alt_ft, self.ias_kts, self.battery_pct = [0], [0], [1], [0], [100]
        self.climb_rate_fpm, self.cruise_power_pct, self.total_time_min, self.total_distance_km, self.max_altitude_ft = 0.0, 0.0, 0.0, 0.0, 0.0

    def record_step(self, dt, dist_step, alt_step, ias, battery_drain):
        self.time_s.append(self.time_s[-1] + dt); self.dist_m.append(self.dist_m[-1] + dist_step)
        self.alt_ft.append(self.alt_ft[-1] + alt_step); self.ias_kts.append(ias)
        self.battery_pct.append(self.battery_pct[-1] - battery_drain)

def calculate_takeoff_distance(aircraft: Aircraft, mu=0.04) -> (float, float):
    """Calculates takeoff ground roll distance and time."""
    weight_n = aircraft.weight_n
    thrust = aircraft.edf.static_thrust_n
    v_r_mps = aircraft.vr_ias_mps  # At sea level, IAS = TAS for takeoff
    
    # Average net force during takeoff roll
    # Drag at 0.7 * Vr
    avg_velocity = v_r_mps * 0.7
    drag_at_70_percent_vr = 0.5 * RHO_SL_KGM3 * (avg_velocity**2) * (aircraft.wing_area_m2 / aircraft.ld_ratio) # Simplified drag
    rolling_friction = mu * weight_n
    net_force = thrust - drag_at_70_percent_vr - rolling_friction
    
    if net_force <= 0: return float('inf'), float('inf') # Cannot take off
    
    acceleration = net_force / aircraft.mtow_kg
    distance_m = (v_r_mps**2) / (2 * acceleration)
    time_s = v_r_mps / acceleration
    return distance_m, time_s

def run_mission_simulation(aircraft: Aircraft) -> FlightPath:
    path = FlightPath()
    weight_n = aircraft.mtow_kg * G
    total_energy_j = aircraft.battery.total_energy_j

    # Phase 1: Takeoff at Sea Level
    takeoff_dist_m, takeoff_time_s = calculate_takeoff_distance(aircraft)
    if takeoff_dist_m == float('inf'):
        print(f"WARNING: {aircraft.params.name} cannot generate enough thrust to take off. Skipping mission.")
        return path
    # Assume power consumption during takeoff is at 100% for the duration
    takeoff_energy_drain_pct = (aircraft.edf.power_w * takeoff_time_s / total_energy_j) * 100
    path.record_step(takeoff_time_s, takeoff_dist_m, 0, aircraft.vr_ias_mps * 1.94384, takeoff_energy_drain_pct)

    # Phase 2: Climb at Vy until 25% battery is used (75% remaining)
    climb_ias_mps = aircraft.vy_ias_mps
    alt_step_ft = 250.0

    while path.battery_pct[-1] > 75.0 and path.alt_ft[-1] < 45000: # Max altitude constraint
        current_alt_m = path.alt_ft[-1] * 0.3048
        # ISA model for density
        temp_k = 288.15 - 0.0065 * current_alt_m
        pressure_pa = 101325 * (1 - 0.0065 * current_alt_m / 288.15)**5.256
        rho = pressure_pa / (287.05 * temp_k)
        
        tas_mps = climb_ias_mps * math.sqrt(RHO_SL_KGM3 / rho)
        
        # Power required to overcome drag at Vy (TAS)
        d_min_n = weight_n / aircraft.ld_ratio
        v_ratio = tas_mps / (aircraft.best_glide_ias_mps * math.sqrt(RHO_SL_KGM3 / rho))
        drag_at_vy = d_min_n * 0.5 * (v_ratio**2 + (1/v_ratio)**2)
        power_required_drag = drag_at_vy * tas_mps
        
        # Power available from the motor, derated by air density
        density_ratio = rho / RHO_SL_KGM3
        power_available_elec = aircraft.edf.power_w * density_ratio
        power_available_prop = power_available_elec * aircraft.edf.get_propulsive_efficiency(tas_mps)
        
        # Excess power for climbing
        excess_power_w = power_available_prop - power_required_drag
        
        if excess_power_w <= 0: break # Cannot climb further
        
        roc_mps = excess_power_w / weight_n
        if path.climb_rate_fpm == 0: path.climb_rate_fpm = roc_mps * 196.85

        time_to_climb_s = (alt_step_ft * 0.3048) / roc_mps
        dist_step_m = tas_mps * time_to_climb_s
        energy_drain_pct = (power_available_elec * time_to_climb_s / total_energy_j) * 100
        
        path.record_step(time_to_climb_s, dist_step_m, alt_step_ft, climb_ias_mps * 1.94384, energy_drain_pct)

    # Phase 3: Cruise at altitude until 90% battery is used (10% remaining)
    usable_cruise_energy_j = ((path.battery_pct[-1] - 10.0) / 100.0) * total_energy_j
    if usable_cruise_energy_j > 0:
        cruise_alt_m = path.alt_ft[-1] * 0.3048
        temp_k = 288.15 - 0.0065 * cruise_alt_m
        pressure_pa = 101325 * (1 - 0.0065 * cruise_alt_m / 288.15)**5.256
        rho = pressure_pa / (287.05 * temp_k)
        
        cruise_tas_mps = aircraft.cruise_ias_mps / math.sqrt(rho / RHO_SL_KGM3)
        thrust_req_cruise = weight_n / aircraft.ld_ratio
        power_req_prop_cruise = thrust_req_cruise * cruise_tas_mps
        power_req_elec_cruise = power_req_prop_cruise / aircraft.edf.get_propulsive_efficiency(cruise_tas_mps)
        
        path.cruise_power_pct = (power_req_elec_cruise / aircraft.edf.power_w) * 100
        
        if power_req_elec_cruise > 0:
            cruise_time_s = usable_cruise_energy_j / power_req_elec_cruise
            dist_step_m = cruise_tas_mps * cruise_time_s
            battery_drain_pct = path.battery_pct[-1] - 10.0
            path.record_step(cruise_time_s, dist_step_m, 0, aircraft.cruise_ias_kts, battery_drain_pct)

    # Phase 4: Descend at best glide speed
    descent_ias_mps = aircraft.best_glide_ias_mps
    descent_alt_ft = path.alt_ft[-1]
    
    # Simplified descent calculation
    glide_angle_rad = math.atan(1 / aircraft.ld_ratio)
    descent_dist_m = descent_alt_ft * 0.3048 / math.tan(glide_angle_rad)
    
    # Estimate time to descend
    avg_alt_m = (descent_alt_ft / 2) * 0.3048
    temp_k = 288.15 - 0.0065 * avg_alt_m
    pressure_pa = 101325 * (1 - 0.0065 * avg_alt_m / 288.15)**5.256
    rho = pressure_pa / (287.05 * temp_k)
    avg_tas_mps = descent_ias_mps * math.sqrt(RHO_SL_KGM3 / rho)
    sink_rate_mps = avg_tas_mps * math.sin(glide_angle_rad)
    descent_time_s = (descent_alt_ft * 0.3048) / sink_rate_mps if sink_rate_mps > 0 else 0

    path.record_step(descent_time_s, descent_dist_m, -descent_alt_ft, descent_ias_mps * 1.94384, 0)

    path.total_distance_km = path.dist_m[-1] / 1000
    path.total_time_min = path.time_s[-1] / 60
    path.max_altitude_ft = max(path.alt_ft)
    return path

def print_mission_summary(aircraft: Aircraft, mission_path: FlightPath):
    speeds = {"Stall": aircraft.stall_speed_ias_mps * 1.94, "Vy": aircraft.vy_ias_mps * 1.94, "Cruise": aircraft.cruise_ias_kts, "Glide": aircraft.best_glide_ias_mps * 1.94}
    header = f"--- MISSION PERFORMANCE: {aircraft.params.name} ---"
    print(header)
    print(f"\n  Calculated Speeds (IAS):\n    {' | '.join([f'{k}: {v:.0f} kts' for k, v in speeds.items()])}")
    print(f"\n  Mission Results:")
    print(f"    Initial Rate of Climb: {mission_path.climb_rate_fpm:,.0f} fpm")
    print(f"    Cruise Power Required: {mission_path.cruise_power_pct:.1f}% of motor's max power")
    print(f"    Max Altitude Reached:  {mission_path.max_altitude_ft:,.0f} ft")
    print(f"    Total Mission Range:   {mission_path.total_distance_km:.1f} km")
    print(f"    Total Mission Time:    {mission_path.total_time_min:.1f} min")
    print("-" * len(header))

if __name__ == "__main__":
    # (The main plotting block remains unchanged)
    os.makedirs('processed_uav_data', exist_ok=True)
    print("--- EDF Mission Simulation (Physics-First Model) ---")
    configured_aircraft = generate_aircraft_scenarios()
    if not configured_aircraft: print("\nNo aircraft configurations were generated."); exit()
    fig, ax = plt.subplots(figsize=(16, 10))
    cmap = plt.cm.viridis(np.linspace(0, 1, len(configured_aircraft)))
    for i, aircraft in enumerate(configured_aircraft):
        mission_path = run_mission_simulation(aircraft)
        print_mission_summary(aircraft, mission_path)
        name = f"{aircraft.edf.name.split(' ')[0]} {'Endur' if aircraft.params.endurance.percent > 50 else 'Sprint'}"
        dist_km = np.array(mission_path.dist_m) / 1000
        sc = ax.scatter(dist_km, mission_path.alt_ft, c=mission_path.ias_kts, s=20, cmap='plasma', label=name)
        ax.plot(dist_km, mission_path.alt_ft, color=cmap[i], alpha=0.3, lw=1.5)
    cbar = fig.colorbar(sc, ax=ax); cbar.set_label('Indicated Airspeed (knots)')
    ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xlabel("Distance (km)"); ax.set_ylabel("Altitude (ft)")
    ax.set_title("Simulated Mission Profiles (Physics-First Model)", fontsize=16)
    ax.grid(True, which='both', linestyle='--', linewidth=0.5); ax.legend()
    from matplotlib.ticker import ScalarFormatter
    ax.xaxis.set_major_formatter(ScalarFormatter())
    plt.tight_layout()
    save_path = "processed_uav_data/mission_profiles_final.png"
    plt.savefig(save_path)
    print(f"\nMission profile plot saved to '{save_path}'")
    plt.show()
