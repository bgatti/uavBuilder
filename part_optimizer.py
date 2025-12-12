import os
import json
import pandas as pd
from uav_variant import UAVVariant, all_variants # Import UAVVariant class and all_variants list

# Define the folder path containing the processed dataframes
processed_folder_path = 'processed_uav_data'

# Load processed CSV files into a dictionary of pandas DataFrames (partsdict)
partsdict = {}
if os.path.exists(processed_folder_path):
    for file_name in os.listdir(processed_folder_path):
        if file_name.endswith('_processed.csv') or file_name.endswith('_cleaned_summary.csv') or file_name.endswith('_cleaned.csv'):
            df_name = file_name.replace('_processed.csv', '').replace('_cleaned_summary.csv', '').replace('_cleaned.csv', '')
            file_path = os.path.join(processed_folder_path, file_name)
            try:
                partsdict[df_name] = pd.read_csv(file_path)
            except Exception as e:
                print(f"Error reading processed CSV file {file_path}: {e}")
else:
    print(f"Processed data folder '{processed_folder_path}' not found.")

# Print names of tables in partsdict
print("Names of tables in partsdict:")
for table_name in partsdict.keys():
    print(table_name)

# Print the first variant in neat json format
print("\nFirst variant in optimized_variants:")
if all_variants:
    # Assuming all_variants is a list of UAVVariant objects
    # We need to convert the first UAVVariant object back to a dictionary for printing as JSON
    first_variant_dict = vars(all_variants[0])
    print(json.dumps(first_variant_dict, indent=4))
else:
    print("optimized_variants is empty or not in expected format (list or dict).")
