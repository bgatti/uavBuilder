import os
import json
import pandas as pd
import re
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from range_estimator import (
    estimate_performance_from_hp, calculate_flight_path,
    estimate_electric_performance, calculate_electric_flight_path
)

def parse_rpm(rpm_str):
    """
    Extracts the highest numerical value from an RPM string, handling ranges and '-'.

    Args:
        rpm_str: The input RPM string (e.g., '7500', '2000-10000', '-').

    Returns:
        The highest numerical value (float) or None if the string is '-' or invalid.
    """
    if isinstance(rpm_str, str):
        rpm_str = rpm_str.strip()
        if rpm_str == '-':
            return None

        match_range = re.search(r'(\d+)\s*-\s*(\d+)', rpm_str)
        if match_range:
            try:
                # Return the highest value in the range
                return float(max(int(match_range.group(1)), int(match_range.group(2))))
            except ValueError:
                return None
        else:
            try:
                # Return the single value
                return float(rpm_str)
            except ValueError:
                return None
    return None

def parse_power(power_str):
    """
    Extracts the numerical value and unit (kW or HP) from a power string.

    Args:
        power_str: The input power string (e.g., '20 kW', '19 hp', '15 - 18 HP', '-').

    Returns:
        A tuple containing the numerical value (float) and the unit (str),
        or (None, None) if the string format is not recognized.
    """
    if isinstance(power_str, str):
        power_str = power_str.strip()
        if power_str == '-':
            return None, None

        match_kw = re.search(r'(\d+\.?\d*)\s*kW', power_str)
        if match_kw:
            return float(match_kw.group(1)), 'kW'

        match_hp_paren = re.search(r'\((\d+\.?\d*)\s*HP\)', power_str) or re.search(r'\((\d+\.?\d*)\s*hp\)', power_str)
        if match_hp_paren:
            return float(match_hp_paren.group(1)), 'HP'

        # Corrected regex: removed trailing backslash
        match_hp = re.search(r'(\d+\.?\d*)\s*HP', power_str) or re.search(r'(\d+\.?\d*)\s*hp', power_str)
        if match_hp:
             return float(match_hp.group(1)), 'HP'

        match_range = re.search(r'(\d+\.?\d*)\s*-\s*(\d+\.?\d*)\s*HP', power_str)
        if match_range:
            try:
                avg_hp = (float(match_range.group(1)) + float(match_range.group(2))) / 2
                return avg_hp, 'HP'
            except ValueError:
                return None, None

    return None, None

def estimate_hp_from_displacement(displacement_cc):
    """
    Estimates power in HP from engine displacement in cubic centimeters (cc).
    This is a rough estimation based on typical power density of small gasoline engines.
    A common rule of thumb is around 0.05 to 0.1 HP per cc for RC engines.
    Using an average of 0.075 HP/cc for estimation.
    """
    if pd.isna(displacement_cc) or displacement_cc <= 0:
        return None
    return displacement_cc * 0.075 # Placeholder estimation

def convert_to_hp(value, unit):
    """Converts power value to HP based on the unit."""
    if value is None:
        return None
    if unit == 'kW':
        return value * 1.34102
    elif unit == 'HP':
        return value
    return None

def estimate_thrust_from_hp(power_hp):
    """Estimates thrust in Newtons from power in HP."""
    # A rough approximation: 1 HP is about 746 Watts. Thrust depends on propeller efficiency.
    # Assuming a typical efficiency for RC engines. This is a simplification.
    # A common rule of thumb for model aircraft: 1 HP can generate roughly 20-30 N of thrust
    # Using an average of 25 N/HP for estimation.
    if pd.isna(power_hp):
        return None
    return power_hp * 25

# Convert Weight to kilograms
def convert_weight_to_kg(weight_str):
    if isinstance(weight_str, str):
        weight_str = weight_str.strip()
        if weight_str == '-' or weight_str == 'Not Available':
            return None
        elif 'lbs' in weight_str:
            return float(weight_str.replace(' lbs', '')) * 0.453592
        elif 'kg' in weight_str:
            return float(weight_str.replace(' kg', ''))
        elif 'g' in weight_str:
            return float(weight_str.replace(' g', '')) / 1000.0
        else: # Assume grams if no unit is specified
            try:
                return float(weight_str) / 1000.0
            except ValueError:
                return None
    return None

# Convert Capacity to milliliters
def convert_capacity_to_ml(capacity_str):
    if isinstance(capacity_str, str):
        capacity_str = capacity_str.strip()
        if capacity_str == '-' or capacity_str == 'N/A':
            return None
        elif 'ml' in capacity_str:
            return float(capacity_str.replace(' ml', ''))
        elif 'oz' in capacity_str: # Assuming fluid ounces
            return float(capacity_str.replace(' oz', '')) * 29.5735 # 1 fluid oz = 29.5735 ml
        else:
            try:
                return float(capacity_str) # Assume ml if no unit
            except ValueError:
                return None
    return None

def calculate_power_hp_simplified(row):
    """
    Calculates or estimates power in HP for a given row of the dataframe,
    without intermediate columns and without debugging prints.
    """
    power_value, power_unit = parse_power(row['Power'])
    displacement_cc = row.get('Displacement (cc)')

    if not pd.isna(power_value):
        return convert_to_hp(power_value, power_unit)
    else:
        return estimate_hp_from_displacement(displacement_cc)


def init():
    """
    Initializes and processes all UAV data from CSV files.

    Returns:
        dict: A dictionary of processed pandas DataFrames.
    """
    # Define the folder path containing the CSV files
    folder_path = 'uavData'
    csv_files = []

    # Walk through the directory and find all CSV files
    for root, dirs, files in os.walk(folder_path):
      for file in files:
        if file.endswith('.csv'):
          csv_files.append(os.path.join(root, file))

    print("CSV files found:")
    for csv_file in csv_files:
      print(csv_file)

    # Load CSV files into pandas DataFrames
    dataframes = {}

    for csv_file in csv_files:
        df_name = os.path.splitext(os.path.basename(csv_file))[0]
        try:
            dataframes[df_name] = pd.read_csv(csv_file)
        except Exception as e:
            print(f"Error reading CSV file {csv_file}: {e}")

    print(f"Loaded {len(dataframes)} dataframes.")

    # --- Clean Powerplant Data ---

    # Access the rc_gasoline_engines dataframe from the dataframes dictionary
    if 'rc_gasoline_engines' in dataframes:
        rc_gasoline_engines_df = dataframes['rc_gasoline_engines'].copy()
        # Default engine type for estimation, as it's not in the source data
        rc_gasoline_engines_df['Engine Type'] = '2-stroke'
        print("Processing powerplant data.")

        # Calculate or estimate power in HP
        rc_gasoline_engines_df['Power (HP)'] = rc_gasoline_engines_df.apply(
            lambda row: convert_to_hp(*parse_power(row['Power']))
            if not pd.isna(parse_power(row['Power'])[0])
            else estimate_hp_from_displacement(row.get('Displacement (cc)')),
            axis=1
        )

        # Apply the parse_rpm function and substitute 9999 if the result is None
        rc_gasoline_engines_df['Speed (RPM)'] = rc_gasoline_engines_df['Speed (RPM)'].apply(parse_rpm).fillna(9999)

        # Convert Weight to kilograms
        rc_gasoline_engines_df['Weight_kg'] = rc_gasoline_engines_df['Weight'].apply(convert_weight_to_kg)

        # Estimate Range, Useful Load, and Cruise Speed
        # Apply the estimation function to each row
        estimation_results = rc_gasoline_engines_df.apply(
            lambda row: estimate_performance_from_hp(row['Power (HP)'], row.get('Engine Type', '2-stroke')),
            axis=1
        )

        # Add the results as new columns
        rc_gasoline_engines_df[['Estimated Range (km)', 'Estimated Useful Load (kg)', 'Estimated Cruise Speed (knots)', 'Estimated Max Fuel (kg)', 'Estimated MTOW (kg)', 'Estimated Thrust (N)']] = pd.DataFrame(estimation_results.tolist(), index=rc_gasoline_engines_df.index)

        # Create a summary dataframe including the new columns
        dataframes['rc_gasoline_engines'] = rc_gasoline_engines_df[['ModelID', 'Power (HP)', 'Estimated Thrust (N)', 'Weight_kg', 'Price', 'Estimated Range (km)', 'Estimated Useful Load (kg)', 'Estimated Cruise Speed (knots)', 'Estimated Max Fuel (kg)', 'Estimated MTOW (kg)', 'Speed (RPM)']].copy()

        print("Processed powerplant data.")
    else:
        print("Powerplant dataframe 'rc_gasoline_engines' not found.")

    # --- Clean EDF Data ---

    # Access the edf dataframe from the dataframes dictionary
    if 'edf' in dataframes:
        edf_df = dataframes['edf'].copy()
        print("Processing EDF data.")

        # Convert Thrust from grams to Newtons
        if 'Thrust (g)' in edf_df.columns:
            edf_df['Thrust (N)'] = pd.to_numeric(edf_df['Thrust (g)'], errors='coerce') * 0.00980665

        # Process Power (W)
        if 'Power (W)' in edf_df.columns:
            edf_df['Power (W)'] = pd.to_numeric(edf_df['Power (W)'], errors='coerce')

        # Estimate Weight and Price
        edf_df['Weight_g'] = edf_df['Power (W)'] * 0.1  # Placeholder
        edf_df['Price'] = edf_df['Power (W)'] * 0.5  # Placeholder

        # Apply the electric performance estimation
        estimation_results = edf_df.apply(
            lambda row: estimate_electric_performance(row['Thrust (N)'], row['Power (W)']),
            axis=1
        )

        # Convert the list of dictionaries to a DataFrame
        estimation_df = pd.DataFrame(estimation_results.tolist(), index=edf_df.index)

        # Add the results as new columns
        for col in estimation_df.columns:
            edf_df[col] = estimation_df[col]
        
        # Create a summary dataframe for plotting
        edf_summary = edf_df.dropna(subset=['total_range_km', 'mtow_kg'])
        
        # Create a summary dataframe
        dataframes['edf'] = edf_df[[
            'Model ID', 'Power (W)', 'Thrust (N)', 'Weight_g', 'Price',
            'total_range_km', 'useful_load_kg', 'estimated_knots',
            'battery_weight_kg', 'mtow_kg', 'payload_kg'
        ]].copy()
        
        print("Processed EDF data.")

        # Display the head and info of the new dataframe (These will print to the console when the script is run)
        # print("\nEDF Summary Head:")
        # print(dataframes['edf'].head())
        # print("\nEDF Summary Info:")
        # dataframes['edf'].info()

        # Create a scatter plot of Thrust vs. Estimated Weight
        # if 'Estimated Weight (g)' in dataframes['edf'].columns and 'Thrust (N)' in dataframes['edf'].columns:
        #     plt.figure(figsize=(10, 6))
        #     sns.scatterplot(data=dataframes['edf'], x='Estimated Weight (g)', y='Thrust (N)')
        #     plt.title('Estimated Thrust vs. Estimated Weight for EDFs')
        #     plt.xlabel('Estimated Weight (g)')
        #     plt.ylabel('Thrust (N)')
        #     plt.grid(True)
            # plt.show() # Commenting out plt.show() as it might block execution in some environments
            # print("Generated EDF Thrust vs. Estimated Weight scatter plot.")
    else:
        print("EDF dataframe 'edf' not found.")

    # --- Clean Battery Data ---

    # Access the battery dataframe
    if 'battery' in dataframes:
        battery_df = dataframes['battery'].copy()
        print("Processing battery data.")

        # Standardize weight column
        if 'weight' in battery_df.columns:
            battery_df['weight_g'] = pd.to_numeric(battery_df['weight'], errors='coerce')

        # Standardize capacity column
        if 'capacity-mAh' in battery_df.columns:
            battery_df['capacity_Ah'] = pd.to_numeric(battery_df['capacity-mAh'], errors='coerce') / 1000

        # Standardize voltage column ('nominalV')
        if 'voltage' in battery_df.columns and 'nominalV' not in battery_df.columns:
            battery_df['nominalV'] = pd.to_numeric(battery_df['voltage'], errors='coerce')
        elif 'config' in battery_df.columns and 'nominalV' not in battery_df.columns:
            battery_df['cell_count'] = battery_df['config'].str.extract(r'(\d+)S').astype(float)
            battery_df['nominalV'] = battery_df['cell_count'] * 3.7

        # Calculate energy if possible
        if 'capacity_Ah' in battery_df.columns and 'nominalV' in battery_df.columns:
            battery_df['energy_Wh'] = battery_df['capacity_Ah'] * battery_df['nominalV']

        # Now, filter the dataframe
        required_cols = ['weight_g', 'capacity_Ah', 'energy_Wh', 'nominalV']
        
        # Check if all required columns exist before dropping NA
        if all(col in battery_df.columns for col in required_cols):
            processed_battery_df = battery_df.dropna(subset=required_cols).copy()
            # Ensure energy and voltage are greater than zero
            dataframes['battery'] = processed_battery_df[
                (processed_battery_df['energy_Wh'] > 0) & (processed_battery_df['nominalV'] > 0)
            ].copy()
        else:
            print("Warning: Could not process battery data completely due to missing columns.")
            # Fallback to a simpler dataframe if essential columns are missing
            fallback_cols = [col for col in ['weight_g', 'capacity_Ah'] if col in battery_df.columns]
            if fallback_cols:
                dataframes['battery'] = battery_df.dropna(subset=fallback_cols).copy()
            else:
                dataframes['battery'] = pd.DataFrame() # Empty dataframe

        print("Processed battery data.")

        # Display the head and info of the new dataframe (These will print to the console when the script is run)
        # print("\nCleaned Battery DataFrame Head:")
        # # display(dataframes['battery'].head()) # Commenting out display as it requires a specific environment
        # print(dataframes['battery'].head())

        # print("\nCleaned Battery DataFrame Info:")
        # dataframes['battery'].info()
    else:
        print("Battery dataframe 'battery' not found.")

    # --- Clean Fuel Tank Data ---

    # Access the fuel tank dataframe
    if 'fuel tank' in dataframes:
        fuel_tank_df = dataframes['fuel tank'].copy()
        print("Processing fuel tank data.")

        # Convert 'Weight' to kilograms
        if 'Weight' in fuel_tank_df.columns:
            fuel_tank_df['Weight_kg'] = fuel_tank_df['Weight'].apply(convert_weight_to_kg)
            print("Converted 'Weight' to 'Weight_kg' in fuel tank data.")

        # Convert 'Capacity' to milliliters
        if 'Capacity' in fuel_tank_df.columns:
            fuel_tank_df['Capacity_ml'] = fuel_tank_df['Capacity'].apply(convert_capacity_to_ml)
            print("Converted 'Capacity' to 'Capacity_ml' in fuel tank data.")

        # Drop rows with NaN in processed columns if necessary for later use
        dataframes['fuel tank'] = fuel_tank_df.dropna(subset=['Weight_kg', 'Capacity_ml']).copy()
        print("Processed fuel tank data.")

    else:
        print("Fuel tank dataframe 'fuel tank' not found.")


    return dataframes




if __name__ == "__main__":
    my_dict = init()

    # Create a single figure with 4 subplots
    fig, axs = plt.subplots(2, 2, figsize=(24, 18))
    plt.style.use('seaborn-v0_8-whitegrid')

    # --- Plot 1: RC Gasoline Engines Flight Profiles ---
    if 'rc_gasoline_engines' in my_dict and not my_dict['rc_gasoline_engines'].empty:
        engines_df = my_dict['rc_gasoline_engines'].dropna(subset=['Power (HP)']).copy()
        sample_engines = engines_df.sample(n=min(15, len(engines_df)), random_state=42)
        
        colors = plt.cm.viridis(np.linspace(0, 1, len(sample_engines)))
        ax1 = axs[0, 0]

        for i, (index, row) in enumerate(sample_engines.iterrows()):
            x_path, y_path, _ = calculate_flight_path(row['Power (HP)'], row.get('Engine Type', '2-stroke'))
            label = f"{row['ModelID']} ({row['Power (HP)']:.1f} HP)"
            if x_path and y_path:
                ax1.plot(x_path, y_path, marker='o', linestyle='-', color=colors[i], label=label, lw=2)

        ax1.set_title("Gasoline Engine Flight Profiles", fontsize=16)
        ax1.set_xlabel("Range (Nautical Miles)", fontsize=12)
        ax1.set_ylabel("Altitude (Feet)", fontsize=12)
        ax1.legend(fontsize=10)
        ax1.grid(True)

    # --- Plot 2: EDF Performance Metrics ---
    if 'edf' in my_dict and not my_dict['edf'].empty:
        edf_summary = my_dict['edf'].dropna(subset=['total_range_km', 'mtow_kg'])
        ax2 = axs[0, 1]
        
        sc = ax2.scatter(edf_summary['Power (W)'], edf_summary['total_range_km'], 
                         alpha=0.7, s=50, c=edf_summary['Thrust (N)'], cmap='viridis')
        ax2.set_title('EDF: Range vs Power', fontsize=16)
        ax2.set_xlabel('Power (W)', fontsize=12)
        ax2.set_ylabel('Estimated Range (km)', fontsize=12)
        ax2.grid(True)
        fig.colorbar(sc, ax=ax2, label='Thrust (N)')

    # --- Plot 3: EDF Flight Profiles ---
    if 'edf' in my_dict and not my_dict['edf'].empty:
        edf_summary = my_dict['edf'].dropna(subset=['total_range_km', 'mtow_kg'])
        sample_edf = edf_summary.sample(n=min(10, len(edf_summary)), random_state=42)
        ax3 = axs[1, 0]
        colors = plt.cm.plasma(np.linspace(0, 1, len(sample_edf)))

        for i, (idx, row) in enumerate(sample_edf.iterrows()):
            performance_data = estimate_electric_performance(row['Thrust (N)'], row['Power (W)'])
            x_path, y_path, _ = calculate_electric_flight_path(performance_data, row['Thrust (N)'], row['Power (W)'])
            label = f"{row['Model ID']} ({row['Thrust (N)']:.1f}N, {row['Power (W)']:.1f}W)"
            if x_path and y_path:
                ax3.plot(x_path, y_path, marker='o', linestyle='-', color=colors[i], label=label, lw=2)
        
        ax3.set_title("EDF Flight Profiles", fontsize=16)
        ax3.set_xlabel("Range (Nautical Miles)", fontsize=12)
        ax3.set_ylabel("Altitude (Feet)", fontsize=12)
        ax3.legend(fontsize=10)
        ax3.grid(True)

    # --- Plot 4: Another EDF Metric ---
    if 'edf' in my_dict and not my_dict['edf'].empty:
        edf_summary = my_dict['edf'].dropna(subset=['total_range_km', 'mtow_kg'])
        ax4 = axs[1, 1]
        
        sc = ax4.scatter(edf_summary['Power (W)'], edf_summary['mtow_kg'], 
                         alpha=0.7, s=50, c=edf_summary['Thrust (N)'], cmap='plasma')
        ax4.set_title('EDF: MTOW vs Power', fontsize=16)
        ax4.set_xlabel('Power (W)', fontsize=12)
        ax4.set_ylabel('Estimated MTOW (kg)', fontsize=12)
        ax4.grid(True)
        fig.colorbar(sc, ax=ax4, label='Thrust (N)')

    # Finalize and show the single figure
    plt.tight_layout(pad=3.0)
    plt.suptitle("UAV Performance Analysis", fontsize=24)
    fig.subplots_adjust(top=0.92)
    plt.show()
