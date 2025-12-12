import pandas as pd
import os
import random
from uav_variant import UAVVariant, all_variants
import process_uav_data
import naca_reader
from optimizer_utils import optimize_with_dual_annealing
import json
import numpy as np
from power_required import calculate_flight_power_units

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

# Load processed dataframes
partsdict = process_uav_data.init()
edf_summary = partsdict.get('edf')
battery_summary = partsdict.get('battery')

if edf_summary is None:
    print("EDF summary not found in processed data.")
if battery_summary is None:
    print("Battery summary not found in processed data.")

# --- Fitness Functions ---

def edf_fitness_function(optimization_params, target_variant: UAVVariant):
    """
    Calculates the fitness of an EDF configuration against a target UAV variant.
    This is the first pass of the optimization.
    """
    try:
        edf_index = int(round(optimization_params[0]))
        num_engines_map = {0: 1, 1: 2, 2: 4}
        num_engines = num_engines_map[int(round(optimization_params[1]))]

        selected_edf = edf_summary.iloc[edf_index]

        # Get properties from the selected EDF, multiplied by the number of engines
        total_thrust_n = selected_edf.get('Thrust (N)', 0) * num_engines
        total_power_w = selected_edf.get('Power (W)', 0) * num_engines
        propulsion_weight_kg = (selected_edf.get('Weight_g', 0) / 1000) * num_engines
        
        # Use estimated battery weight for this first pass
        estimated_battery_weight_kg = selected_edf.get('Estimated Battery Weight (kg)', 0) * num_engines

        # --- Compare to Target Variant ---
        target_payload_kg = process_uav_data.convert_weight_to_kg(getattr(target_variant, 'Payload_Capacity', '0 kg'))
        target_range_km = float(getattr(target_variant, 'Range', '0 km').replace(' km', ''))
        target_takeoff_weight_kg = process_uav_data.convert_weight_to_kg(getattr(target_variant, 'Takeoff_Weight', '0 kg'))

        # Estimate total UAV weight
        # This is a simplification; a more detailed model would include airframe weight etc.
        # For now, we use the estimated MTOW from the preprocessing step.
        estimated_mtow_kg = selected_edf.get('Estimated MTOW (kg)', 0) * num_engines
        
        # Calculate differences
        thrust_diff = abs(total_thrust_n - (target_takeoff_weight_kg * 9.81 * 0.5)) / (target_takeoff_weight_kg * 9.81 * 0.5)
        weight_diff = abs(estimated_mtow_kg - target_takeoff_weight_kg) / target_takeoff_weight_kg
        
        # TWR score
        twr = total_thrust_n / (estimated_mtow_kg * 9.81) if estimated_mtow_kg > 0 else 0
        target_twr = 0.5
        twr_error = abs(twr - target_twr) / target_twr

        # Power consumption penalty (penalize high power draw)
        power_penalty = total_power_w / 10000 # Increased penalty

        fitness = thrust_diff + weight_diff + twr_error + power_penalty

        score_details = {
            'edf_index': edf_index,
            'num_engines': num_engines,
            'total_thrust_n': total_thrust_n,
            'total_power_w': total_power_w,
            'estimated_mtow_kg': estimated_mtow_kg,
            'fitness': fitness
        }

        return fitness, score_details

    except IndexError:
        return float('inf'), None
    except Exception as e:
        print(f"Error in edf_fitness_function: {e}")
        return float('inf'), None


def battery_fitness_function(optimization_params, best_edf_config, target_variant: UAVVariant, uav_geometry):
    """
    Calculates the fitness of a battery for a given EDF configuration.
    This is the second pass of the optimization.
    A perfect fit for range and weight results in a score of 0 for those components.
    Deviations from target are measured as a factor of the target value.
    The overall fitness is a combination of penalties and scores, where lower is better.
    """
    try:
        battery_index = int(round(optimization_params[0]))
        num_batteries_map = {0: 1, 1: 2, 2: 4}
        num_batteries = num_batteries_map[int(round(optimization_params[1]))]
        selected_battery = battery_summary.iloc[battery_index]

        # Recalculate MTOW with the actual battery weight
        edf_index = best_edf_config['edf_index']
        num_engines = best_edf_config['num_engines']
        selected_edf = edf_summary.iloc[edf_index]
        estimated_battery_weight_from_edf = selected_edf.get('Estimated Battery Weight (kg)', 0) * num_engines
        uav_weight_without_battery = best_edf_config['estimated_mtow_kg'] - estimated_battery_weight_from_edf
        battery_weight_kg = (selected_battery.get('weight_g', 0) / 1000) * num_batteries
        new_mtow = uav_weight_without_battery + battery_weight_kg

        # Get cruise speed and calculate power required
        cruise_speed_ms = best_edf_config.get('estimated_cruise_speed_kmh', 90) * 1000 / 3600
        
        power_required_w = calculate_flight_power_units(
            mass_plane_kg=new_mtow,
            wing_span_m=uav_geometry['wing_span_m'],
            wing_area_m2=uav_geometry['wing_area_m2'],
            velocity_flight_ms=cruise_speed_ms,
            zero_lift_drag_coefficient=uav_geometry['cd0']
        )

        battery_capacity_ah = selected_battery.get('capacity_Ah', 0) * num_batteries
        battery_voltage = selected_battery.get('nominalV', 0)

        if pd.isna(battery_voltage) or battery_voltage == 0 or power_required_w == 0:
            return float('inf'), None

        # Calculate actual endurance and range
        battery_energy_wh = battery_capacity_ah * battery_voltage
        endurance_h = battery_energy_wh / power_required_w if power_required_w > 0 else 0
        range_km = (cruise_speed_ms * 3600 / 1000) * endurance_h

        # --- Compare to Target Variant ---
        target_range_km = float(getattr(target_variant, 'Range', '0 km').replace(' km', ''))
        target_takeoff_weight_kg = process_uav_data.convert_weight_to_kg(getattr(target_variant, 'Takeoff_Weight', '0 kg'))

        # --- Fitness Calculation based on Deviation ---
        min_endurance_h = 10 / 60  # 10 minutes
        endurance_penalty = max(0, (min_endurance_h - endurance_h) / min_endurance_h * 10)
        range_score = max(0, (target_range_km - range_km) / target_range_km) if target_range_km > 0 else 0
        weight_score = max(0, (new_mtow - target_takeoff_weight_kg) / target_takeoff_weight_kg) if target_takeoff_weight_kg > 0 else 0

        fitness = endurance_penalty + range_score + weight_score

        score_details = {
            'battery_index': battery_index,
            'num_batteries': num_batteries,
            'range_km': range_km,
            'endurance_h': endurance_h,
            'battery_weight_kg': battery_weight_kg,
            'power_required_w': power_required_w,
            'fitness': fitness
        }

        return fitness, score_details

    except IndexError:
        return float('inf'), None
    except Exception as e:
        print(f"Error in battery_fitness_function: {e}")
        return float('inf'), None


# --- Main Execution ---
if __name__ == "__main__":
    print("Running test script for EDF data processing...")
    
    if edf_summary is not None and battery_summary is not None:
        print("\nProcessing UAV variants for EDF optimization...")
        
        # Define UAV geometry based on variant class (example values)
        uav_geometries = {
            "0.1kW": {"wing_span_m": 1.5, "wing_area_m2": 0.15, "cd0": 0.04},
            "0.4kW": {"wing_span_m": 2.0, "wing_area_m2": 0.4, "cd0": 0.035},
            "0.8kW": {"wing_span_m": 2.5, "wing_area_m2": 0.6, "cd0": 0.03},
            "2.1kW": {"wing_span_m": 3.0, "wing_area_m2": 1.0, "cd0": 0.028},
            "5.1kW": {"wing_span_m": 4.0, "wing_area_m2": 1.8, "cd0": 0.025},
        }

        for target_variant in all_variants:
            print(f"\n--- Processing variant: {target_variant.Name} ({target_variant.Class}) ---")
            
            uav_geometry = uav_geometries.get(target_variant.Class, {"wing_span_m": 2, "wing_area_m2": 0.4, "cd0": 0.035})

            # --- Step 1: Optimize EDF and Number of Engines ---
            edf_bounds = [(0, len(edf_summary) - 1), (0, 2)]
            
            def edf_optimization_func(params):
                fitness, _ = edf_fitness_function(params, target_variant)
                return fitness

            best_edf_params, _ = optimize_with_dual_annealing(edf_optimization_func, edf_bounds)
            _, best_edf_score_details = edf_fitness_function(best_edf_params, target_variant)
            best_edf = edf_summary.iloc[best_edf_score_details['edf_index']]
            
            print(f"Best EDF Found: {best_edf.get('Model ID', 'N/A')} with {best_edf_score_details['num_engines']} engine(s)")

            # --- Step 2: Optimize Battery ---
            best_edf_score_details['estimated_cruise_speed_kmh'] = best_edf.get('Estimated Cruise Speed (knots)', 50) * 1.852
            battery_bounds = [(0, len(battery_summary) - 1), (0, 2)]
            
            def battery_optimization_func(params):
                fitness, _ = battery_fitness_function(params, best_edf_score_details, target_variant, uav_geometry)
                return fitness

            best_battery_params, _ = optimize_with_dual_annealing(battery_optimization_func, battery_bounds)
            _, best_battery_score_details = battery_fitness_function(best_battery_params, best_edf_score_details, target_variant, uav_geometry)
            best_battery = battery_summary.iloc[best_battery_score_details['battery_index']]
            
            print(f"Best Battery Found: {best_battery.get('ID', 'N/A')} ({best_battery_score_details['num_batteries']}x)")

            # --- Final Report ---
            print("\n--- Final Optimized Configuration ---")
            final_details = {
                "Variant": target_variant.Name,
                "Class": target_variant.Class,
                "EDF Configuration": best_edf_score_details,
                "Battery Configuration": best_battery_score_details
            }
            print(json.dumps(convert_numpy_types(final_details), indent=2))

    else:
        print("Dataframes for EDF or Battery not loaded correctly.")
