import pandas as pd
import numpy as np
import json
from sklearn.linear_model import LinearRegression

# --- Real battery data ---
battery_data = {
    "Model": ["Tattu R-Line 1.55Ah", "CNHL Black 1.3Ah", "Tattu Funfly 1.3Ah", "Tattu 5.0Ah",
              "DJI TB30 4.28Ah", "DJI TB65 5.88Ah", "Tattu Plus 16Ah", "Tattu Plus 22Ah"],
    "Capacity_Ah": [1.55, 1.3, 1.3, 5.0, 4.28, 5.88, 16.0, 22.0],
    "Voltage_V": [22.2, 22.2, 22.2, 22.2, 26.1, 44.76, 44.4, 44.4],
    "C_Rating": [150, 100, 100, 75, 20, 15, 25, 25],
    "Weight_g": [254, 230, 218, 732, 685, 1350, 4900, 5800],
    "Dimensions_mm": [(78, 38, 38), (75, 35, 35), (76, 39, 36), (142, 50, 44), (125, 51, 47), (180, 70, 57), (224, 91, 70), (235, 96, 76)]
}
df_real = pd.DataFrame(battery_data)

df_real['Energy_Wh'] = df_real['Capacity_Ah'] * df_real['Voltage_V']
df_real['Weight_kg'] = df_real['Weight_g'] / 1000
df_real['Energy_x_C'] = df_real['Energy_Wh'] * df_real['C_Rating']
df_real['Volume_L'] = df_real['Dimensions_mm'].apply(lambda d: (d[0] * d[1] * d[2]) / 1_000_000)
df_real['Volumetric_Density_Wh_L'] = df_real['Energy_Wh'] / df_real['Volume_L']
df_real['Gravimetric_Density_Wh_kg'] = df_real['Energy_Wh'] / df_real['Weight_kg']

# Train the weight model
X_weight = df_real[['Energy_Wh', 'Energy_x_C']]
y_weight = df_real['Weight_kg']
weight_model = LinearRegression().fit(X_weight, y_weight)

# Train the volumetric density model
X_density = df_real[['C_Rating', 'Capacity_Ah']]
y_density = df_real['Volumetric_Density_Wh_L']
density_model = LinearRegression().fit(X_density, y_density)

# Extract coefficients and intercepts
weights = {
    "weight_model": {
        "coef": weight_model.coef_.tolist(),
        "intercept": float(weight_model.intercept_)
    },
    "density_model": {
        "coef": density_model.coef_.tolist(),
        "intercept": float(density_model.intercept_)
    }
}

# Save to JSON file
with open("battery_model_weights.json", "w") as f:
    json.dump(weights, f, indent=2)

print("Weights saved to battery_model_weights.json")
