import pandas as pd
import os
import json
import numpy as np
import matplotlib.pyplot as plt

import process_uav_data
from edf_config import Aircraft, EDF
from lipo import Battery
from uav_parameters import FixedWingParameters
from edf_fitness import fitness as calculate_fitness, set_range
from edf_mission import run_mission_simulation

def convert_numpy_types(obj):
    """Recursively converts NumPy types to standard Python types."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(elem) for elem in obj]
    else:
        return obj

def find_best_edf(target_params, edf_summary):
    """
    Stage 1: Find the best EDF by evaluating it with a virtual battery.
    """
    best_edf_config = None
    best_fitness = -1

    # Define rules for the virtual battery estimation
    rules = {"c_rating": 50, "batt_motor_ratio": 2.5}

    for _, edf_row in edf_summary.iterrows():
        try:
            edf = EDF(
                name=edf_row.get('Model ID', 'N/A'),
                power_w=edf_row.get('Power (W)', 0),
                static_thrust_n=edf_row.get('Thrust (N)', 0),
                weight_kg=edf_row.get('Weight_g', 0) / 1000,
                diameter_m=edf_row.get('Diameter (mm)', 0) / 1000
            )

            # Create an aircraft with a virtual battery
            aircraft = Aircraft.with_virtual_battery(edf, target_params, rules["c_rating"], rules["batt_motor_ratio"])
            
            fitness_result = calculate_fitness(target_params, aircraft)

            if fitness_result.fitness_score > best_fitness:
                best_fitness = fitness_result.fitness_score
                best_edf_config = {
                    "edf": edf,
                    "virtual_battery": aircraft.battery,
                    "fitness": fitness_result
                }
        except (ValueError, IndexError):
            continue
            
    return best_edf_config

def find_best_real_battery(target_params, best_edf, virtual_battery, battery_summary):
    """
    Stage 2: Find the best real battery for the selected EDF.
    """
    best_real_config = None
    best_fitness = -1
    
    max_battery_weight = virtual_battery.weight_kg * 2

    for _, battery_row in battery_summary.iterrows():
        for num_batteries in range(1, 11): # Test up to 10 batteries
            try:
                real_battery = Battery.from_df_row(battery_row, num_batteries=num_batteries)
                
                if real_battery.weight_kg > max_battery_weight:
                    break # Stop if battery weight exceeds the limit

                aircraft = Aircraft(edf=best_edf, battery=real_battery, params=target_params)
                
                fitness_result = calculate_fitness(target_params, aircraft)

                if fitness_result.fitness_score > best_fitness:
                    best_fitness = fitness_result.fitness_score
                    best_real_config = {
                        "aircraft": aircraft,
                        "fitness": fitness_result
                    }
            except (ValueError, IndexError):
                continue

    return best_real_config

if __name__ == "__main__":
    partsdict = process_uav_data.init()
    edf_summary = partsdict.get('edf')
    battery_summary = partsdict.get('battery')

    if edf_summary is None or battery_summary is None:
        print("Could not load EDF or Battery data. Exiting.")
        exit()

    target_params = FixedWingParameters()
    target_params.name = "Optimized EDF UAV"
    set_range(target_params.takeoff_weight, 5, 25)
    set_range(target_params.cruise_speed, 100, 200)
    set_range(target_params.endurance, 0.5, 2)
    set_range(target_params.payload_capacity, 1, 5)

    print("--- Starting Stage 1: Finding Best EDF with Virtual Battery ---")
    best_edf_config = find_best_edf(target_params, edf_summary)

    if not best_edf_config:
        print("No suitable EDF found.")
        exit()

    print("\n--- Best EDF Found ---")
    print(f"  EDF Model: {best_edf_config['edf'].name}")
    print(f"  Ideal Virtual Battery: {best_edf_config['virtual_battery']!r}")
    print(f"  Fitness Score: {best_edf_config['fitness'].fitness_score:.3f}")

    print("\n--- Starting Stage 2: Finding Best Real Battery ---")
    best_edf = best_edf_config['edf']
    virtual_battery = best_edf_config['virtual_battery']
    
    final_config = find_best_real_battery(target_params, best_edf, virtual_battery, battery_summary)

    if not final_config:
        print("No suitable real battery configuration found.")
        exit()

    print("\n--- Final Optimized Configuration ---")
    best_aircraft = final_config['aircraft']
    best_fitness = final_config['fitness']

    print("\nAircraft Summary:")
    for line in best_aircraft.get_summary():
        print(line)
    
    print(f"\nFinal Fitness Score: {best_fitness.fitness_score:.3f}")
    print("Parameter Scores:")
    for name, score in best_fitness.parameter_scores.items():
        print(f"  - {name:<20}: {score:.3f}")

    final_aircraft_data = {
        "name": best_aircraft.params.name,
        "mtow_kg": best_aircraft.mtow_kg,
        "payload_weight_kg": best_aircraft.payload_weight_kg,
        "cruise_speed_kmh": best_aircraft.cruise_ias_kts * 1.852,
        "edf": {
            "name": best_aircraft.edf.name,
            "power_w": best_aircraft.edf.power_w,
            "thrust_n": best_aircraft.edf.static_thrust_n,
            "weight_kg": best_aircraft.edf.weight_kg
        },
        "battery": {
            "model": best_aircraft.battery.model_number,
            "quantity": best_aircraft.battery.num_batteries,
            "weight_kg": best_aircraft.battery.weight_kg,
            "capacity_ah": best_aircraft.battery.capacity_ah,
            "voltage": best_aircraft.battery.voltage,
            "c_rating": best_aircraft.battery.c_rating
        }
    }
    
    final_aircraft_data = convert_numpy_types(final_aircraft_data)
    output_filename = "optimized_uav_configuration.json"
    with open(output_filename, 'w') as f:
        json.dump(final_aircraft_data, f, indent=2)

    print(f"\nOptimized aircraft configuration saved to {output_filename}")

    # --- Stage 3: Run and Plot Mission Scenarios ---
    print("\n--- Running Mission Scenarios for Optimized Hardware ---")
    
    # 1. Optimized Mission (already have this)
    optimized_mission_path = run_mission_simulation(best_aircraft)

    # 2. Least Values Mission
    least_params = FixedWingParameters()
    least_params.name = "Least Values"
    for param in [least_params.takeoff_weight, least_params.cruise_speed, least_params.endurance, least_params.payload_capacity, least_params.wingspan]:
        param.percent = 0
    least_aircraft = Aircraft(edf=best_aircraft.edf, battery=best_aircraft.battery, params=least_params)
    least_mission_path = run_mission_simulation(least_aircraft)
    print("Ran 'Least Values' mission simulation.")

    # 3. Most Values Mission
    most_params = FixedWingParameters()
    most_params.name = "Most Values"
    for param in [most_params.takeoff_weight, most_params.cruise_speed, most_params.endurance, most_params.payload_capacity, most_params.wingspan]:
        param.percent = 100
    most_aircraft = Aircraft(edf=best_aircraft.edf, battery=best_aircraft.battery, params=most_params)
    most_mission_path = run_mission_simulation(most_aircraft)
    print("Ran 'Most Values' mission simulation.")

    # 4. Plotting
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Plot Least and Most paths
    ax.plot(np.array(least_mission_path.dist_m) / 1000, least_mission_path.alt_ft, label='Least Values Mission', color='blue', linestyle='--', lw=2)
    ax.plot(np.array(most_mission_path.dist_m) / 1000, most_mission_path.alt_ft, label='Most Values Mission', color='red', linestyle='--', lw=2)
    
    # Plot Optimized path with a thicker line
    ax.plot(np.array(optimized_mission_path.dist_m) / 1000, optimized_mission_path.alt_ft, label='Optimized Mission', color='green', lw=4)

    ax.set_title(f"Mission Profiles for Optimized Hardware ({best_aircraft.edf.name})", fontsize=16)
    ax.set_xlabel("Distance (km)", fontsize=12)
    ax.set_ylabel("Altitude (ft)", fontsize=12)
    ax.legend()
    ax.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    plot_filename = "optimized_mission_profiles.png"
    plt.savefig(plot_filename)
    print(f"\nMission profile comparison plot saved to {plot_filename}")
    plt.show()
