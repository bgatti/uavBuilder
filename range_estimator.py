
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from breguet_range import calculate_propeller_range_fuel_uav


# Data gathered from research (Power in Watts, Speed in Knots)
# Sources: RC forums, manufacturer specs for popular models (Freewing, E-flite).
# 1. Small 70mm EDF jet (e.g., F-16/T-7A): ~1800W, ~80-90 kts
# 2. Freewing Avanti S (90mm 6S): ~2700W, ~100-110 kts
# 3. Freewing Avanti S (90mm 8S): ~3100W, ~120-130 kts
# 4. High-performance custom build (e.g., Habu 32): >5000W, >170 kts
real_world_data = {
    'power_w': [1800, 2670, 3100, 5300, 8000],
    'speed_kts': [85, 105, 125, 175, 210] # Added a hypothetical 10kW point based on trend
}
df_real = pd.DataFrame(real_world_data)

# Develop a new speed estimation model based on a power-law fit of real data.
# speed = a * power^b  => log(speed) = log(a) + b * log(power)
log_power = np.log(df_real['power_w'])
log_speed = np.log(df_real['speed_kts'])
b, log_a = np.polyfit(log_power, log_speed, 1)
a = np.exp(log_a)

def refined_estimate_electric_speed(power_w):
    """
    Estimates cruise speed for an EDF jet based on a power-law relationship
    derived from real-world performance data.
    """
    # Clamps prevent nonsensical results for very low/high power
    power_w = np.clip(power_w, 200, 20000)
    
    # speed = a * power^b
    estimated_speed_kts = a * (power_w ** b)
    return estimated_speed_kts

def estimate_electric_performance(thrust_n, power_w):
    """
    Consolidated estimation of all key performance metrics for electric propulsion,
    including the detailed flight path segments. This is the single source of truth.
    """
    if pd.isna(thrust_n) or pd.isna(power_w) or thrust_n <= 0 or power_w <= 0:
        return {}

    # --- Stage 1: Basic Aircraft Sizing & Energy ---
    estimated_knots = refined_estimate_electric_speed(power_w)
    twr = 0.6
    mtow_kg = (thrust_n / 9.80665) / twr
    log_mtow = np.log10(max(1, mtow_kg))

    min_ld, max_ld, center_ld, steep_ld = 7.0, 12.0, 3.0, 1.8
    sigmoid_ld = 1 / (1 + np.exp(-steep_ld * (log_mtow - center_ld)))
    ld_ratio = min_ld + (max_ld - min_ld) * sigmoid_ld

    max_ewf, min_ewf, center_ewf, steep_ewf = 0.65, 0.40, 4.0, 1.2
    sigmoid_ewf = 1 / (1 + np.exp(-steep_ewf * (log_mtow - center_ewf)))
    ew_fraction = max_ewf - (max_ewf - min_ewf) * sigmoid_ewf
    empty_weight_kg = mtow_kg * ew_fraction

    min_bf, max_bf, center_bf, steep_bf = 0.35, 0.65, 1.2, 1.5
    sigmoid_bf = 1 / (1 + np.exp(-steep_bf * (log_mtow - center_bf)))
    battery_fraction_of_empty = min_bf + (max_bf - min_bf) * sigmoid_bf
    battery_weight_kg = empty_weight_kg * battery_fraction_of_empty

    payload_kg = mtow_kg - empty_weight_kg - battery_weight_kg
    payload_kg = max(0, payload_kg)
    mtow_kg = empty_weight_kg + battery_weight_kg + payload_kg

    total_efficiency = 0.80
    battery_specific_energy_Wh_kg = 200
    propulsive_energy_J = battery_weight_kg * battery_specific_energy_Wh_kg * 3600 * total_efficiency

    # --- Stage 2: Flight Dynamics (Ceiling and Climb) ---
    g = 9.80665
    knots_to_mps = 0.514444
    weight_n = mtow_kg * g
    indicated_airspeed_mps = estimated_knots * knots_to_mps
    drag_n_base = weight_n / ld_ratio
    
    service_ceiling_roc_mps = 0.508
    altitude_m = 0
    for alt_step_m in np.arange(100, 25000, 250):
        sigma = (1 - (alt_step_m / 44330))**4.256
        power_available_at_alt = power_w * (sigma**0.8)
        true_airspeed_at_alt = indicated_airspeed_mps / np.sqrt(sigma)
        power_required_at_alt = (drag_n_base * true_airspeed_at_alt) / total_efficiency
        excess_power = power_available_at_alt - power_required_at_alt
        if excess_power <= 0: break
        rate_of_climb_mps = (excess_power * total_efficiency) / weight_n
        if rate_of_climb_mps < service_ceiling_roc_mps: break
        altitude_m = alt_step_m
    
    true_airspeed_mps = indicated_airspeed_mps / np.sqrt((1 - (altitude_m / 44330))**4.256)
    climb_speed_mps = true_airspeed_mps * 0.8
    
    total_climb_time_s, total_climb_dist_km, total_energy_for_climb_J = 0, 0, 0
    climb_x_coords_km, climb_y_coords_ft = [0], [0]
    
    if altitude_m > 0:
        num_climb_segments = 3
        segment_alt_m = altitude_m / num_climb_segments
        for i in range(num_climb_segments):
            mid_segment_alt = (i * segment_alt_m) + (segment_alt_m / 2)
            sigma_segment = (1 - (mid_segment_alt / 44330))**4.256
            power_available_segment_W = power_w * (sigma_segment**0.8)
            power_required_climb_W = (drag_n_base * climb_speed_mps) / total_efficiency
            excess_power_W = power_available_segment_W - power_required_climb_W
            rate_of_climb_mps = (excess_power_W * total_efficiency) / weight_n if excess_power_W > 0 else 0
            if rate_of_climb_mps <= 0: break
            
            segment_time_s = segment_alt_m / rate_of_climb_mps
            total_climb_time_s += segment_time_s
            total_climb_dist_km += (climb_speed_mps * segment_time_s) / 1000
            total_energy_for_climb_J += power_available_segment_W * segment_time_s
            
            climb_x_coords_km.append(total_climb_dist_km)
            climb_y_coords_ft.append(((i + 1) * segment_alt_m) * 3.28084)

    # --- Stage 3: Cruise and Descent ---
    energy_for_cruise_J = max(0, propulsive_energy_J - total_energy_for_climb_J)
    power_required_cruise_W = (drag_n_base * true_airspeed_mps) / total_efficiency
    cruise_time_s = energy_for_cruise_J / power_required_cruise_W if power_required_cruise_W > 0 else 0
    cruise_dist_km = (true_airspeed_mps * cruise_time_s) / 1000
    
    cruise_alt_ft = climb_y_coords_ft[-1] if climb_y_coords_ft else 0
    descent_dist_km = (cruise_alt_ft * 0.3048 / 1000) / np.tan(np.deg2rad(3.0)) if cruise_alt_ft > 0 else 0
    total_range_km = total_climb_dist_km + cruise_dist_km + descent_dist_km

    # --- Stage 4: Package Results ---
    return {
        "total_range_km": total_range_km,
        "useful_load_kg": mtow_kg - empty_weight_kg,
        "estimated_knots": estimated_knots,
        "battery_weight_kg": battery_weight_kg,
        "mtow_kg": mtow_kg,
        "payload_kg": payload_kg,
        "climb_dist_km": total_climb_dist_km,
        "cruise_dist_km": cruise_dist_km,
        "descent_dist_km": descent_dist_km,
        "climb_x_coords_km": climb_x_coords_km,
        "climb_y_coords_ft": climb_y_coords_ft,
        "cruise_alt_ft": cruise_alt_ft
    }

def calculate_electric_flight_path(performance_data, thrust_n, power_w):
    """
    Formats the detailed performance data into plottable coordinates.
    This function no longer performs any physics calculations.
    """
    if not performance_data or performance_data.get("total_range_km", 0) < 1:
        # Return a structure that won't break the plotting loop
        return [0] * 6, [0] * 6, "Invalid/Negligible Range"

    nm_per_km = 0.539957

    # Unpack the pre-calculated data
    climb_x_km = performance_data["climb_x_coords_km"]
    climb_y_ft = performance_data["climb_y_coords_ft"]
    climb_dist_km = performance_data["climb_dist_km"]
    cruise_dist_km = performance_data["cruise_dist_km"]
    total_range_km = performance_data["total_range_km"]
    cruise_alt_ft = performance_data["cruise_alt_ft"]

    # Assemble the full path from the calculated segments
    x_coords_km = list(climb_x_km)
    x_coords_km.append(climb_dist_km + cruise_dist_km)
    x_coords_km.append(total_range_km)

    y_coords_ft = list(climb_y_ft)
    y_coords_ft.append(cruise_alt_ft)
    y_coords_ft.append(0)

    # Convert X-axis to nautical miles for the plot
    x_coords_nm = [d * nm_per_km for d in x_coords_km]
    
    label = f"{power_w/1000:.1f}kW ({thrust_n:.0f}N)"
    return x_coords_nm, y_coords_ft, label

# --- Dynamic Scaling Factor Models from previous step ---
def estimate_sfc_from_power(engine_type, horsepower):
    if engine_type == '2-stroke': return 0.45
    elif engine_type == '4-stroke': return max(0.25, 0.30 - 0.05 * np.log10(horsepower / 100))
    elif engine_type == 'turboprop': return 0.28
    elif engine_type == 'high_bypass_fan': return 0.22
    return 0.3

def estimate_propulsive_efficiency(engine_type, cruise_knots):
    if 'stroke' in engine_type or engine_type == 'turboprop':
        return max(0.2, 0.85 - 0.3 * (cruise_knots / 400)**2)
    elif engine_type == 'high_bypass_fan': return 0.75
    return 0.7

def estimate_ld_ratio(mtow_kg):
    log_mtow = np.log10(max(1, mtow_kg))
    min_ld, max_ld, center, steepness = 8.0, 18.0, 3.5, 1.5
    sigmoid = 1 / (1 + np.exp(-steepness * (log_mtow - center)))
    return min_ld + (max_ld - min_ld) * sigmoid

def estimate_empty_weight_fraction(mtow_kg):
    log_mtow = np.log10(max(1, mtow_kg))
    max_ewf, min_ewf, center, steepness = 0.70, 0.50, 4.0, 1.2
    sigmoid = 1 / (1 + np.exp(-steepness * (log_mtow - center)))
    return max_ewf - (max_ewf - min_ewf) * sigmoid

def estimate_altitude_and_speed(mtow_kg, engine_type):
    log_mtow = np.log10(max(1, mtow_kg))
    if 'stroke' in engine_type:
        alt_ft = 5000 + 2000 * log_mtow
        speed_knots = 70 + 30 * log_mtow
    elif engine_type == 'turboprop':
        alt_ft = 10000 + 5000 * log_mtow
        speed_knots = 150 + 50 * log_mtow
    else: # high_bypass_fan
        alt_ft = 25000 + 4000 * log_mtow
        speed_knots = 400 + 20 * log_mtow
    return min(alt_ft, 45000), min(speed_knots, 480)

def estimate_thrust_from_hp(power_hp, knots, propulsive_efficiency):
    if power_hp is None or knots <= 0: return 0
    power_watts = power_hp * 745.7
    speed_mps = knots * 0.514444
    return (power_watts * propulsive_efficiency) / speed_mps

# --- New function to calculate the full flight path ---
def estimate_performance_from_hp(engine_hp, engine_type):
    """
    Estimates key performance metrics based on engine horsepower and type.
    This function encapsulates the core logic demonstrated in the original __main__ block.
    """
    if pd.isna(engine_hp) or engine_hp <= 0:
        return None, None, None, None, None, None

    # 1. Converge on performance profile
    estimated_knots = 100 if 'stroke' in engine_type else 250
    prop_eff = 0.7  # Initial guess
    for _ in range(3):
        prop_eff = estimate_propulsive_efficiency(engine_type, estimated_knots)
        thrust_n = estimate_thrust_from_hp(engine_hp, estimated_knots, prop_eff)
        twr = 0.5 if engine_type == 'high_bypass_fan' else 0.25
        mtow_kg = (thrust_n / 9.80665) / twr if twr > 0 else 0
        _, estimated_knots = estimate_altitude_and_speed(mtow_kg, engine_type)

    # 2. Final performance calculation
    ld_ratio = estimate_ld_ratio(mtow_kg)
    ew_fraction = estimate_empty_weight_fraction(mtow_kg)
    w_empty_kg = mtow_kg * ew_fraction
    w_fuel_kg = (mtow_kg - w_empty_kg) * 0.8
    
    total_range_km = calculate_propeller_range_fuel_uav(
        V_km_hr=estimated_knots * 1.852,
        propeller_efficiency=prop_eff,
        psfc_kg_per_kW_hr=estimate_sfc_from_power(engine_type, engine_hp),
        L_D=ld_ratio,
        W_empty_kg=w_empty_kg,
        W_fuel_kg=w_fuel_kg
    )
    
    # Estimate useful load (payload)
    w_payload_kg = mtow_kg - w_empty_kg - w_fuel_kg

    return total_range_km, w_payload_kg, estimated_knots, w_fuel_kg, mtow_kg, thrust_n

# --- New function to calculate the full flight path ---
def calculate_flight_path(engine_hp, engine_type):
    """
    Calculates the climb, cruise, and descent segments of a flight.
    """
    # 1. Get performance metrics
    total_range_km, _, estimated_knots, _, mtow_kg, thrust_n = estimate_performance_from_hp(engine_hp, engine_type)
    if total_range_km is None:
        return [0, 0, 0, 0], [0, 0, 0, 0], "Invalid Input"

    # 2. Get additional parameters for geometry
    altitude_ft, _ = estimate_altitude_and_speed(mtow_kg, engine_type)
    ld_ratio = estimate_ld_ratio(mtow_kg)

    # 3. Geometry Calculation
    altitude_m = altitude_ft * 0.3048
    weight_n = mtow_kg * 9.80665
    drag_n = weight_n / ld_ratio
    
    # Climb
    excess_thrust = thrust_n - drag_n
    climb_angle_rad = np.arcsin(excess_thrust / weight_n) if excess_thrust > 0 and weight_n > 0 else np.deg2rad(1)
    climb_dist_km = (altitude_m / 1000) / np.tan(climb_angle_rad) if climb_angle_rad > 0 else 0
    
    # Descent
    descent_angle_rad = np.deg2rad(3.0)
    descent_dist_km = (altitude_m / 1000) / np.tan(descent_angle_rad)
    
    # Cruise
    cruise_dist_km = total_range_km - climb_dist_km - descent_dist_km
    if cruise_dist_km < 0: # Handle cases where climb/descent is the whole trip
        climb_dist_km = total_range_km / 2
        descent_dist_km = total_range_km / 2
        cruise_dist_km = 0

    # 4. Convert to Nautical Miles for plotting
    nm_per_km = 0.539957
    climb_dist_nm = climb_dist_km * nm_per_km
    cruise_dist_nm = cruise_dist_km * nm_per_km
    descent_dist_nm = descent_dist_km * nm_per_km

    # 5. Create path coordinates
    x_coords = [0, climb_dist_nm, climb_dist_nm + cruise_dist_nm, climb_dist_nm + cruise_dist_nm + descent_dist_nm]
    y_coords = [0, altitude_ft, altitude_ft, 0]
    
    return x_coords, y_coords, f"{engine_type.replace('_',' ').title()} ({engine_hp} HP)"

if __name__ == "__main__":
    # --- Demonstration of the new estimate_performance_from_hp function ---
    print("--- Performance Estimation Demonstration ---")
    demo_hp = 160
    demo_type = "4-stroke"
    range_km, payload_kg, speed_knots, fuel_kg, mtow, thrust = estimate_performance_from_hp(demo_hp, demo_type)
    print(f"Performance for a {demo_hp} HP {demo_type} engine:")
    print(f"  - Estimated MTOW: {mtow:.2f} kg")
    print(f"  - Estimated Thrust: {thrust:.2f} N")
    print(f"  - Estimated Range: {range_km:.2f} km")
    print(f"  - Estimated Cruise Speed: {speed_knots:.2f} knots")
    print(f"  - Estimated Fuel Capacity: {fuel_kg:.2f} kg")
    print(f"  - Estimated Payload: {payload_kg:.2f} kg")
    print("-" * 40)
    
    # --- Electric Performance Demonstration ---
    print("--- Electric Performance Estimation Demonstration ---")
    demo_thrust = 100
    demo_power = 1000
    perf_data = estimate_electric_performance(demo_thrust, demo_power)
    if perf_data:
        print(f"Performance for an electric propulsion system ({demo_thrust}N, {demo_power}W):")
        print(f"  - Estimated MTOW: {perf_data['mtow_kg']:.2f} kg")
        print(f"  - Estimated Range: {perf_data['total_range_km']:.2f} km")
        print(f"  - Estimated Cruise Speed: {perf_data['estimated_knots']:.2f} knots")
        print(f"  - Estimated Cruise Altitude: {perf_data['cruise_alt_ft']:.0f} ft")
        print(f"  - Estimated Battery Weight: {perf_data['battery_weight_kg']:.2f} kg")
        print(f"  - Estimated Payload: {perf_data['payload_kg']:.2f} kg")
    print("-" * 40)

    # --- Gas Engine Flight Path Simulation ---
    gas_scenarios = [
        {"hp": 5, "type": "2-stroke"},
        {"hp": 100, "type": "4-stroke"},
        {"hp": 160, "type": "4-stroke"},
        {"hp": 1200, "type": "turboprop"},
        {"hp": 4000, "type": "high_bypass_fan"},
    ]
    fig, ax = plt.subplots(figsize=(14, 8))
    plt.style.use('seaborn-v0_8-whitegrid')
    colors = plt.cm.viridis(np.linspace(0, 1, len(gas_scenarios)))
    for i, scenario in enumerate(gas_scenarios):
        x_path, y_path, label = calculate_flight_path(scenario['hp'], scenario['type'])
        ax.plot(x_path, y_path, marker='o', linestyle='-', color=colors[i], label=label, lw=2.5)
        if len(y_path) > 1 and y_path[1] > 0:
            ax.text(x_path[1], y_path[1] + 1500, f"{y_path[1]:,.0f} ft", ha='center', fontsize=10, color=colors[i])
        if len(x_path) > 3 and x_path[3] > 0:
            ax.text(x_path[-1], -2000, f"{x_path[-1]:,.0f} nm", ha='center', fontsize=10, color=colors[i])
    ax.set_title("Simulated Flight Profiles by Propulsion Technology", fontsize=18)
    ax.set_xlabel("Range (Nautical Miles)", fontsize=14)
    ax.set_ylabel("Altitude (Feet)", fontsize=14)
    ax.legend(fontsize=12, loc='upper left')
    ax.grid(which='major', linestyle='-', linewidth='0.5', color='gray')
    ax.set_ylim(bottom=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    from matplotlib.ticker import FuncFormatter
    ax.get_yaxis().set_major_formatter(FuncFormatter(lambda x, p: format(int(x), ',')))
    plt.tight_layout()
    plt.savefig("processed_uav_data/gas_engine_range_estimation.png")
    plt.close()

    # --- Electric Flight Path and Performance Simulation ---
    electric_scenarios = [
        {"thrust": 20, "power": 200},
        {"thrust": 50, "power": 500},
        {"thrust": 100, "power": 1000},
        {"thrust": 200, "power": 2000},
        {"thrust": 400, "power": 4000},
        {"thrust": 800, "power": 10000},
    ]
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 14), gridspec_kw={'height_ratios': [3, 2]})
    plt.style.use('seaborn-v0_8-whitegrid')
    colors = plt.cm.plasma(np.linspace(0, 1, len(electric_scenarios)))
    
    cruise_speeds = []
    labels = []

    for i, scenario in enumerate(electric_scenarios):
        thrust = scenario['thrust']
        power = scenario['power']
        
        performance_data = estimate_electric_performance(thrust, power)
        if not performance_data: continue
        
        x_path, y_path, label = calculate_electric_flight_path(performance_data, thrust, power)
        
        cruise_speeds.append(performance_data["estimated_knots"])
        labels.append(label)
        
        ax1.plot(x_path, y_path, marker='o', linestyle='-', color=colors[i], label=label, lw=2.5)
        
        # Add text labels for cruise altitude and total range
        cruise_alt_ft = performance_data["cruise_alt_ft"]
        if cruise_alt_ft > 0:
            # Find the x-coordinate for the start of cruise
            cruise_start_x = x_path[len(performance_data["climb_x_coords_km"])-1]
            ax1.text(cruise_start_x, cruise_alt_ft + 1200, f"{cruise_alt_ft:,.0f} ft", ha='center', fontsize=10, color=colors[i])
        
        total_range_nm = x_path[-1]
        if total_range_nm > 0:
            ax1.text(total_range_nm, -1800, f"{total_range_nm:,.0f} nm", ha='center', fontsize=10, color=colors[i])

    # Finalize the first plot (Flight Profiles)
    ax1.set_title("Simulated Flight Profiles for Electric Propulsion Systems", fontsize=18)
    ax1.set_xlabel("Range (Nautical Miles)", fontsize=14)
    ax1.set_ylabel("Altitude (Feet)", fontsize=14)
    ax1.legend(fontsize=12, loc='upper left')
    ax1.grid(which='major', linestyle='-', linewidth='0.5', color='gray')
    ax1.set_ylim(bottom=-3000)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))

    # Create the second plot (Cruise Speeds)
    ax2.bar(labels, cruise_speeds, color=colors, edgecolor='black')
    ax2.set_title("Estimated Cruise Speed by Propulsion System", fontsize=18)
    ax2.set_xlabel("Propulsion System", fontsize=14)
    ax2.set_ylabel("Cruise Speed (Knots)", fontsize=14)
    ax2.tick_params(axis='x', rotation=45, labelsize=10)
    for i, speed in enumerate(cruise_speeds):
        ax2.text(i, speed + 2, f"{speed:.0f}", ha='center', fontsize=11)

    # Finalize the first plot (Flight Profiles)
    ax1.set_title("Simulated Flight Profiles for Electric Propulsion Systems", fontsize=18)
    ax1.set_xlabel("Range (Nautical Miles)", fontsize=14)
    ax1.set_ylabel("Altitude (Feet)", fontsize=14)
    ax1.legend(fontsize=12, loc='upper left')
    ax1.grid(which='major', linestyle='-', linewidth='0.5', color='gray')
    ax1.set_ylim(bottom=-3000)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, p: format(int(x), ',')))

    # Create the second plot (Cruise Speeds)
    ax2.bar(labels, cruise_speeds, color=colors, edgecolor='black')
    ax2.set_title("Estimated Cruise Speed by Propulsion System", fontsize=18)
    ax2.set_xlabel("Propulsion System", fontsize=14)
    ax2.set_ylabel("Cruise Speed (Knots)", fontsize=14)
    ax2.tick_params(axis='x', rotation=45, labelsize=10)
    for i, speed in enumerate(cruise_speeds):
        ax2.text(i, speed + 2, f"{speed:.0f}", ha='center', fontsize=11)

    # Finalize the combined figure
    plt.tight_layout(pad=3.0)
    plt.savefig("processed_uav_data/electric_propulsion_range_estimation.png")
    plt.show()
