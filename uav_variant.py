import os
import json
import pandas as pd
import re # Import re as parse_power might be used here later

class UAVVariant:
  """Represents a single UAV variant with its characteristics and score."""

  def __init__(self, variant_data, score):
    self.score = score
    for key, value in variant_data.items():
      # Sanitize keys to be valid Python identifiers (replace spaces and special chars)
      sanitized_key = key.replace(" ", "_").replace("-", "_").replace("/", "_").replace("(", "").replace(")", "").replace("+", "").replace("&","").replace(".","")
      setattr(self, sanitized_key, value)

# Load the mock data from mock.json
optimized_variants = {}
mock_file_path = 'mock.json'
if os.path.exists(mock_file_path):
    try:
        with open(mock_file_path, 'r') as f:
            optimized_variants = json.load(f)
    except Exception as e:
        print(f"Error reading mock file {mock_file_path}: {e}")
else:
    print(f"Mock file '{mock_file_path}' not found.")

# Create a list to hold all UAVVariant objects
all_variants = []

# Iterate through the optimized_variants dictionary and create UAVVariant objects
for model, variants in optimized_variants.items():
  for item in variants:
    # Ensure 'variant' and 'score' keys exist before accessing
    if 'variant' in item and 'score' in item:
        all_variants.append(UAVVariant(item['variant'], item['score']))
    else:
        print(f"Skipping item due to missing 'variant' or 'score' key: {item}")

# Example of accessing the first variant (for testing within this file if needed)
# if all_variants:
#     print(all_variants[0].Takeoff_Weight)
#     print(all_variants[0].score)
