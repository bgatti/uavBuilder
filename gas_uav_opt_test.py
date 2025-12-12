import pandas as pd
import os
import random
from uav_variant import UAVVariant, all_variants
import process_uav_data
import naca_reader
from optimizer_utils import optimize_with_dual_annealing, score_propeller
import re # Import re for parsing (still needed for target variant parsing)
import json # Import json for pretty printing
import numpy as np # Import numpy to check for numpy types

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

# Load processed dataframes using process_uav_data.init()
try:
    partsdict = process_uav_data.init()
    print("Processed data loaded successfully using process_uav_data.init().")
except AttributeError:
    print("Error: process_uav_data does not have an 'init' function.")
    partsdict = {}
except Exception as e:
    print(f"Error loading processed data: {e}")
    partsdict = {}

# Load the gas engine summary
gas_engine_summary = partsdict.get('rc_gasoline_engines')
if gas_engine_summary is None:
    print("Gas engine summary not found in processed data.")
else:
    print("Gas engine summary loaded successfully.")

    if gas_engine_summary is not None:
        print("Gas Engine Summary (head):")
        print(gas_engine_summary.head())


# Load the wing profiles
try:
    wing_profiles = naca_reader.init()
except AttributeError:
    print("Error calling naca_reader.init().")
    wing_profiles = None
except FileNotFoundError:
    print("naca.csv not found by naca_reader.init().")
    wing_profiles = None

if wing_profiles is None:
    print("Wing profiles failed to load.")

# Load Propellers data (Fuel Tank is now a scalar in optimization)
propellers_df = partsdict.get('Propellers')

if propellers_df is None:
    print("Propellers data not found in processed data.")

if gas_engine_summary is None:
    print("gas_engine dataframe not loaded for fitness calculation.")
#    return float('inf') # Return infinity if data is missing


def engine_fitness_function(optimization_params, target_variant: UAVVariant, propeller_weight_kg: float):
    """
    Calculates the fitness of a given engine against a target UAV variant.
    This function focuses on engine-specific metrics.
    """
    try:
        engine_index = int(round(optimization_params[0]))
        selected_engine = gas_engine_summary.iloc[engine_index]

        # --- Compare Selected Part Properties and Fuel Weight to Target Variant Properties ---
        target_payload_capacity_kg = process_uav_data.convert_weight_to_kg(getattr(target_variant, 'Payload_Capacity', '0 kg'))
        target_range_km = float(getattr(target_variant, 'Range', '0 km').replace(' km', '')) if isinstance(getattr(target_variant, 'Range', '0 km'), str) else getattr(target_variant, 'Range', 0)

        useful_load_kg = selected_engine.get('Estimated Useful Load (kg)', 0)
        max_fuel_kg = selected_engine.get('Estimated Max Fuel (kg)', 0)
        max_range_km = selected_engine.get('Estimated Range (km)', 0)
        mtow_km = selected_engine.get('Estimated MTOW (kg)', 0)
        engine_thrust_N = selected_engine.get('Estimated Thrust (N)', 0)
        engine_weight_kg = selected_engine.get('Weight_kg', 0)
        estimated_cruise_speed_knots = selected_engine.get('Estimated Cruise Speed (knots)', 0) # Assuming this key

        payload_potential_kg = useful_load_kg - max_fuel_kg
        
        # Total selected parts weight (engine + avg propeller)
        selected_parts_weight_kg = engine_weight_kg + propeller_weight_kg

        # Simplified total UAV weight for engine selection
        total_uav_weight_kg = mtow_km - (payload_potential_kg - target_payload_capacity_kg)

        # Extract target variant properties
        target_thrust_N = float(getattr(target_variant, 'engine_thrust', '0 N').replace(' N', '')) if isinstance(getattr(target_variant, 'engine_thrust', '0 N'), str) else getattr(target_variant, 'engine_thrust', 0)
        target_takeoff_weight_kg = process_uav_data.convert_weight_to_kg(getattr(target_variant, 'Takeoff_Weight', '0 kg'))
        
        # Calculate target cruise speed from Range and Endurance
        target_range_km = float(getattr(target_variant, 'Range', '0 km').replace(' km', '')) if isinstance(getattr(target_variant, 'Range', '0 km'), str) else getattr(target_variant, 'Range', 0)
        target_endurance_minutes = float(getattr(target_variant, 'Endurance', '0 minutes').replace(' minutes', '')) if isinstance(getattr(target_variant, 'Endurance', '0 minutes'), str) else getattr(target_variant, 'Endurance', 0)

        target_range_m = target_range_km * 1000 # Convert km to meters
        target_endurance_seconds = target_endurance_minutes * 60 # Convert minutes to seconds

        target_cruise_speed_mps = 0
        if target_endurance_seconds > 0:
            target_cruise_speed_mps = target_range_m / target_endurance_seconds # Calculate speed in mps

        target_cruise_speed_kmh = target_cruise_speed_mps * 3600 / 1000 # Convert mps to km/h


        # Convert estimated cruise speed from knots to mps
        estimated_cruise_speed_mps = estimated_cruise_speed_knots * 0.514444 # Convert knots to mps

        # Calculate differences
        thrust_diff = abs(engine_thrust_N - target_thrust_N) / target_thrust_N if target_thrust_N > 0 else float('inf')
        weight_diff = abs(total_uav_weight_kg - target_takeoff_weight_kg) / target_takeoff_weight_kg if target_takeoff_weight_kg > 0 else float('inf')
        
        # Calculate cruise speed error
        cruise_speed_error = abs(estimated_cruise_speed_mps - target_cruise_speed_mps) / target_cruise_speed_mps if target_cruise_speed_mps > 0 else float('inf')


        # --- Thrust-to-Weight Ratio Scoring ---
        thrust_to_weight_ratio = engine_thrust_N / (total_uav_weight_kg * 9.81) if total_uav_weight_kg > 0 else 0
        target_twr = 0.25
        twr_error = 0.0
        if thrust_to_weight_ratio < target_twr:
            twr_error = abs(target_twr - thrust_to_weight_ratio) / target_twr * 4.0
        else:
            twr_error = abs(target_twr - thrust_to_weight_ratio) / target_twr
            
        fitness = thrust_diff + weight_diff + twr_error + cruise_speed_error # Add cruise speed error to fitness

        score_details = {
            'engine_index': engine_index,
            'thrust_diff': thrust_diff,
            'weight_diff': weight_diff,
            'twr_error': twr_error,
            'engine_rpm': selected_engine.get('Speed (RPM)', 0),
            'estimated_cruise_speed_knots': estimated_cruise_speed_knots, # Add estimated cruise speed (knots)
            'estimated_cruise_speed_mps': estimated_cruise_speed_mps, # Add estimated cruise speed (mps)
            'target_cruise_speed_kmh': target_cruise_speed_kmh, # Add target cruise speed (km/h)
            'target_cruise_speed_mps': target_cruise_speed_mps, # Add target cruise speed (mps)
            'cruise_speed_error': cruise_speed_error, # Add cruise speed error
            'fitness': fitness
        }

        return fitness, score_details

    except IndexError:
        return float('inf'), None
    except Exception as e:
        print(f"Error during engine fitness calculation: {e}")
        return float('inf'), None

def propeller_fitness_function(optimization_params, engine_score_details, target_variant: UAVVariant):
    """
    Calculates the fitness of a given propeller for a selected engine.
    The fitness is the propeller's overall score (lower is better).
    """
    try:
        propeller_index = int(round(optimization_params[0]))
        selected_propeller = propellers_df.iloc[propeller_index]

        # --- Propeller Scoring ---
        engine_rpm = engine_score_details.get('engine_rpm', 0) # Access from score_details
        propeller_diameter_inches = selected_propeller.get('Diameter (in)', 0)
        propeller_pitch_inches = selected_propeller.get('Pitch (in)', 0)
        propeller_price_usd = selected_propeller.get('Price (USD)', 0.0)
        propeller_length_inches = selected_propeller.get('Length (in)', propeller_diameter_inches)
        propeller_material = selected_propeller.get('Material', 'Unknown')
        propeller_number_of_blades = selected_propeller.get('Number of Blades', 0)
        cruise_speed_mps = engine_score_details.get('estimated_cruise_speed_mps', 0)
        target_thrust_N = float(getattr(target_variant, 'engine_thrust', '0 N').replace(' N', '')) if isinstance(getattr(target_variant, 'engine_thrust', '0 N'), str) else getattr(target_variant, 'engine_thrust', 0)
        
        propeller_score_details = score_propeller(
            engine_rpm,
            propeller_diameter_inches,
            propeller_pitch_inches,
            propeller_number_of_blades,
            cruise_speed_mps,
            target_thrust_N,
            price_usd=propeller_price_usd
        )

        # The optimizer minimizes, so we return the score directly
        fitness = propeller_score_details.get('overall_score', float('inf'))

        return fitness, propeller_score_details

    except IndexError:
        return float('inf'), None
    except Exception as e:
        print(f"Error during propeller fitness calculation: {e}")
        return float('inf'), None


def fitness_function(optimization_params, target_variant: UAVVariant) -> float:
    """
    Calculates the fitness of a given combination of parts
    against a target UAV variant.

    Args:
        optimization_params (list): A list of parameters being optimized
                                    [gas_engine_index, propeller_index].
                                    Indices refer to the *filtered* lists of parts.
        target_variant (UAVVariant): The target UAV variant.

    Returns:
        float: for each metric - calculate the over/under as a percent of the magnitude. Lower is better fitness.
    """

    try:
        # Map indices to selected parts from the full dataframes (will need adjustment for filtering)
        engine_index = int(round(optimization_params[0]))

        propeller_index = int(round(optimization_params[1]))

        selected_engine = gas_engine_summary.iloc[engine_index]
        selected_propeller = propellers_df.iloc[propeller_index]

        print("Selected Engine:")
        print(selected_engine)

        # --- Compare Selected Part Properties and Fuel Weight to Target Variant Properties ---
        target_payload_capacity_kg = process_uav_data.convert_weight_to_kg(getattr(target_variant, 'Payload_Capacity', '0 kg'))
        target_range_km = float(getattr(target_variant, 'Range', '0 km').replace(' km', '')) if isinstance(getattr(target_variant, 'Range', '0 km'), str) else getattr(target_variant, 'Range', 0)

        useful_load_kg = selected_engine.get('Estimated Useful Load (kg)', 0)
        max_fuel_kg = selected_engine.get('Estimated Max Fuel (kg)', 0)
        max_range_km = selected_engine.get('Estimated Range (km)', 0)
        mtow_km = selected_engine.get('Estimated MTOW (kg)', 0)
        engine_thrust_N = selected_engine.get('Estimated Thrust (N)', 0)
        engine_weight_kg = selected_engine.get('Weight_kg', 0)
        cruise_speed_knots = selected_engine.get('Estimated Cruise Speed (knots)', 0)


        payload_potential_kg = useful_load_kg - max_fuel_kg
        
        # Extract relevant properties from selected parts (using cleaned data from process_uav_data)
        propeller_weight_g = selected_propeller.get('Weight (g)', 0)

        # Total selected parts weight (excluding fuel tank)
        selected_parts_weight_kg = engine_weight_kg + (propeller_weight_g / 1000)

        # Total UAV weight (simplification: parts + fuel + assumed payload/structure)
        # Need to derive assumed payload/structure from target variant or define a constant
        # For now, let's compare total selected parts weight + fuel_kg to target takeoff weight
        # Correcting access to payload capacity based on UAVVariant class and mock.json
        total_uav_weight_kg = mtow_km - (payload_potential_kg -target_payload_capacity_kg) # slight adjustment based on payload


        # Extract target variant properties (handle units and potential missing data)
        target_thrust_N = float(getattr(target_variant, 'engine_thrust', '0 N').replace(' N', '')) if isinstance(getattr(target_variant, 'engine_thrust', '0 N'), str) else getattr(target_variant, 'engine_thrust', 0)
        target_takeoff_weight_kg = process_uav_data.convert_weight_to_kg(getattr(target_variant, 'Takeoff_Weight', '0 kg'))

        # Target fuel capacity is not directly available, need to derive from Range/Endurance if possible
        # For now, we'll compare fuel_kg to a value proportional to target range
        approx_fuel_needed_for_target_range_kg = max_fuel_kg/max_range_km * target_range_km
        

        # Calculate differences (absolute difference)
        # Compare selected engine thrust to target thrust
        thrust_diff = abs(engine_thrust_N - target_thrust_N)/target_thrust_N

        # Compare total UAV weight (parts + fuel) to target takeoff weight
        weight_diff = abs(total_uav_weight_kg - target_takeoff_weight_kg)/target_takeoff_weight_kg




        # --- Thrust-to-Weight Ratio Scoring ---
        # Calculate thrust-to-weight ratio (N/kg)
        thrust_to_weight_ratio = engine_thrust_N / (total_uav_weight_kg * 9.81) # Convert kg to Newtons (approx. using 9.81 m/s^2)

        # Target thrust-to-weight ratio (25% or 0.25)
        target_twr = 0.25

        # Calculate thrust-to-weight ratio error
        twr_error = 0.0
        if thrust_to_weight_ratio < target_twr:
            twr_error = abs(target_twr - thrust_to_weight_ratio) / target_twr * 4.0 # Multiply error by 4x if less than 25%
        else:
            twr_error = abs(target_twr - thrust_to_weight_ratio) / target_twr
            

#        print(f"  Thrust-to-Weight Ratio: {thrust_to_weight_ratio:.2f} (Target: {target_twr:.2f}), TWR Error: {twr_error:.2f}")
        
        # --- Propeller Scoring ---
        # Extract necessary data for propeller scoring
        # Assuming relevant keys are available in selected_engine and selected_propeller
        engine_rpm = selected_engine.get('Speed (RPM)', 0) # Placeholder key, adjust if needed
        propeller_diameter_inches = selected_propeller.get('Diameter (in)', 0) # Placeholder key, adjust if needed
        propeller_pitch_inches = selected_propeller.get('Pitch (in)', 0) # Placeholder key, adjust if needed
        propeller_price_usd = selected_propeller.get('Price (USD)', 0.0) # Placeholder key, adjust if needed
        propeller_length_inches = selected_propeller.get('Length (in)', propeller_diameter_inches) # Placeholder key, assuming length is diameter if not specified
        propeller_material = selected_propeller.get('Material', 'Unknown') # Placeholder key, adjust if needed
        propeller_number_of_blades = selected_propeller.get('Number of Blades', 0) # Placeholder key, adjust if needed
        cruise_speed_mps =cruise_speed_knots * 0.514444 # Convert knots to mps (1 knot = 0.514444 m/s)
        expected_thrust_N = target_thrust_N # Using the already extracted target thrust

        # Calculate propeller score and get details
        propeller_score_details = score_propeller(
            engine_rpm,
            propeller_diameter_inches,
            propeller_pitch_inches,
            propeller_number_of_blades,
            cruise_speed_mps,
            target_thrust_N,
            price_usd=propeller_price_usd
        )

        # Extract the overall score from the details
        propeller_overall_score = propeller_score_details.get('overall_score', 0)

#        print(f"  Propeller Overall Score: {propeller_overall_score:.2f}")

        # Simple sum of differences and errors as fitness score (lower is better)
        # Consider weighting these differences and the propeller score based on importance if needed
        # We need to minimize the fitness function, so we should subtract the propeller overall score
        fitness = thrust_diff + weight_diff + twr_error + propeller_overall_score

        # print(f"  Evaluating: Engine Index {engine_index}, Propeller Index {propeller_index}, Fuel (kg) {approx_fuel_needed_for_target_range_kg:.2f}")
        # print(f"  Config Thrust: {engine_thrust_N:.2f} N, Total UAV Weight (parts+fuel): {total_uav_weight_kg:.2f} kg, Fuel (calculated): {approx_fuel_needed_for_target_range_kg:.2f} kg")
        # print(f"  Target Thrust: {target_thrust_N:.2f} N, Target Takeoff Weight: {target_takeoff_weight_kg:.2f} kg, Approx Fuel Needed for Target Range: {approx_fuel_needed_for_target_range_kg:.2f} kg")
        # print(f"  Thrust-to-Weight Ratio: {thrust_to_weight_ratio:.2f} (Target: {target_twr:.2f}), TWR Error: {twr_error:.2f}")
        # print(f"  Fitness Score (including propeller overall score): {fitness:.2f}")


        # Create a score object to preserve calculated values
        score_details = {
            'engine_index': engine_index,
            'propeller_index': propeller_index,
            'fuel_kg': approx_fuel_needed_for_target_range_kg,
            'engine_thrust_N': engine_thrust_N,
            'engine_weight_kg': engine_weight_kg,
            'engine_HP': selected_engine.get('Power (HP)', 0),
            'propeller_weight_g': propeller_weight_g,
            'selected_parts_weight_kg': selected_parts_weight_kg,
            'total_uav_weight_kg': total_uav_weight_kg,
            'target_payload_capacity_kg': target_payload_capacity_kg,
            'target_thrust_N': target_thrust_N,
            'target_takeoff_weight_kg': target_takeoff_weight_kg,
            'target_range_km': target_range_km,
            'approx_fuel_needed_for_target_range_kg': approx_fuel_needed_for_target_range_kg,
            'thrust_diff': thrust_diff,
            'weight_diff': weight_diff,
            'thrust_to_weight_ratio': thrust_to_weight_ratio,
            'target_thrust_to_weight_ratio': target_twr,
            'twr_error': twr_error,
            'propeller_overall_score': propeller_overall_score, # Use overall score here
            'propeller_score_details': propeller_score_details, # Include the full propeller score details
            'fitness': fitness # Include the final fitness in the score object
        }

        return fitness, score_details

    except IndexError:
        print(f"Error: Invalid optimization parameters {optimization_params}. Index out of bounds for part dataframes.")
        # Return infinity for fitness and None for score_details in case of error
        return float('inf'), None
    except Exception as e:
        print(f"Error during fitness calculation: {e}")
        # Return infinity for fitness and None for score_details in case of error
        return float('inf'), None


# Example of accessing loaded data (for demonstration)
# print("Loaded partsdict keys:", partsdict.keys())
# if gas_engine_summary is not None:
#     print("Gas engine summary loaded successfully.")
# if wing_profiles is not None:
#     print("Wing profiles loaded successfully.")

# --- Process Variants ---
if 'all_variants' in globals() and all_variants:
    print("\nProcessing UAV variants...")
    # Select the first variant
    first_variant = all_variants[0]
    print(f"Processing first variant: {first_variant}")

    # TODO: Implement part filtering based on first_variant
    # For now, use all parts from the relevant dataframes
    available_engines = gas_engine_summary
    available_propellers = propellers_df

    if available_engines is not None and available_propellers is not None:
        # --- Sequential Optimization ---
        # 1. Optimize Engine
        print("\n--- Step 1: Optimizing Engine ---")
        avg_propeller_weight_kg = available_propellers['Weight (g)'].mean() / 1000
        engine_bounds = [(0, len(available_engines) - 1)]
        
        # Capture both fitness and score_details from engine_fitness_function
        def engine_optimization_func(params):
            fitness, score_details = engine_fitness_function(params, first_variant, avg_propeller_weight_kg)
            return fitness

        best_engine_params, best_engine_fitness = optimize_with_dual_annealing(
            engine_optimization_func,
            engine_bounds
        )
        
        best_engine_index = int(round(best_engine_params[0]))
        best_engine = available_engines.iloc[best_engine_index]
        
        # Get the score_details for the best engine
        _, best_engine_score_details = engine_fitness_function(best_engine_params, first_variant, avg_propeller_weight_kg)
        
        print(f"Best Engine Found: {best_engine.get('ModelID', 'N/A')} with fitness {best_engine_fitness:.2f}")

        # 2. Optimize Propeller for the Best Engine
        print("\n--- Step 2: Optimizing Propeller for the Best Engine ---")
        propeller_bounds = [(0, len(available_propellers) - 1)]
        
        best_propeller_params, best_propeller_fitness = optimize_with_dual_annealing(
            lambda params: propeller_fitness_function(params, best_engine_score_details, first_variant)[0],
            propeller_bounds
        )
        
        best_propeller_index = int(round(best_propeller_params[0]))
        best_propeller = available_propellers.iloc[best_propeller_index]
        print(f"Best Propeller Found: {best_propeller.get('ModelID', 'N/A')} with score {best_propeller_fitness:.2f}")

        # --- Final Configuration and Details ---
        print("\n--- Final Optimized Configuration ---")
        # Recalculate final details with the best combination
        # Note: The original fitness_function can be used here to get the combined score details,
        # or we can manually construct the final details object.
        final_params = [best_engine_index, best_propeller_index]
        final_fitness, final_score_details = fitness_function(final_params, first_variant)

        print(f"Best Engine: {best_engine.get('ModelID', 'N/A')}")
        print(f"- Propeller: {best_propeller.get('ModelID', 'N/A')}")
        
        # Print the final score details
        print("\nFinal Score Details:")
        if final_score_details:
            serializable_score_details = convert_numpy_types(final_score_details)
            print(json.dumps(serializable_score_details, indent=2))
        else:
            print("Could not retrieve final score details.")

        # --- Generate Top 5 Propeller Report ---
        print("\n--- Generating Top 5 Propeller Report ---")
        propeller_scores = []
        for i, propeller in available_propellers.iterrows():
            fitness, score_details = propeller_fitness_function([i], best_engine_score_details, first_variant)
            propeller_scores.append((propeller.get('ModelID', f'Index {i}'), fitness, score_details))

        # Sort by fitness (lower is better)
        propeller_scores.sort(key=lambda x: x[1])

        print("\n--- Top 5 Scoring Propellers ---")
        for i, (model_id, fitness, score_details) in enumerate(propeller_scores[:5]):
            print(f"\n{i+1}. Model: {model_id} (Score: {fitness:.4f})")
            # Pretty print the score details for each of the top propellers
            serializable_details = convert_numpy_types(score_details)
            print(json.dumps(serializable_details, indent=2))
            
    else:
        print("Bounds for optimization could not be determined. Check if part dataframes were loaded correctly.")

else:
    print("No variants found in all_variants.")
