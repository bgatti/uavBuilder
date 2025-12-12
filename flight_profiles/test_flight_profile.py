import os
import sys
from typing import Dict, Any, Tuple

# Add the parent directory to the sys.path to allow importing modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from flight_profiles.fuel_flight_profile import FuelFlightProfileCalculator
from naca_reader import init as read_naca_data # Use init function from naca_reader

def run_fuel_flight_profile_test():
    """
    Tests the FuelFlightProfileCalculator with provided parameters and NACA profiles.
    """
    # Provided parameters
    provided_params = {
        "wing_loading": "127.24 kg/m^2",
        "induced_drag_proportion_at_ld_max": "0.04 ",
        "thrust_to_weight_ratio": 0.3469710855760236,
        "lift_to_drag_ratio": "16.97 ",
        "engine_thrust": "623.88 N",
        "Takeoff_Weight": "183.29 kg",
        "Payload_Capacity": "13.11 kg",
        "Propulsion_Types": "fuel-powered",
        "Endurance": "322.55 minutes",
        "Range": "798.12 km",
        "Wingspan": "1.49 m",
        "power_budget": {
            "motor_kg": 4.99104,
            "battery_kg": 0,
            "fuel_kg": 16.7693745,
            "total_power_budget_kg": 21.760414500000003
        },
        "power_budget_total_kg": 21.760414500000003,
        "wing_area_sq_m": 2.510821917808219,
        "wing_loading_kg_per_sq_m": 73.0,
        "induced_drag_coefficient": 0.1124976688670135,
        "power_budget_to_mtow_ratio": 0.11872123138196303,
        "payload_to_mtow_ratio": 0.07152599705384909,
        "mtow_to_range_ratio": 0.22965218262917855
    }

    # Extract necessary parameters from provided data
    mtow = float(provided_params["Takeoff_Weight"].split()[0]) # Extract numerical value
    fuel_onboard_kg = provided_params["power_budget"]["fuel_kg"]
    expected_endurance_minutes = float(provided_params["Endurance"].split()[0]) # Extract numerical value
    wing_area_sq_m = provided_params["wing_area_sq_m"] # Extract wing area

    # Estimated fuel consumption rate (kg/hr) based on provided endurance and fuel onboard
    endurance_hours_expected = expected_endurance_minutes / 60.0
    fuel_consumption_kg_per_hr = fuel_onboard_kg / endurance_hours_expected if endurance_hours_expected > 0 else 0.0

    # Made-up parameters for testing
    engine_hp = 20.0 # Made-up value
    cruise_speed_knots = 80.0 # Made-up value
    cruise_altitude_feet = 5000.0 # Made-up value

    powerplant_details = {
        'engine_hp': engine_hp,
        'fuel_onboard_kg': fuel_onboard_kg,
        'fuel_consumption_kg_per_hr': fuel_consumption_kg_per_hr
    }

    print("Running Fuel Flight Profile Test:")
    print(f"MTOW: {mtow} kg")
    print(f"Powerplant Details: {powerplant_details}")
    print(f"Cruise Speed: {cruise_speed_knots} knots")
    print(f"Cruise Altitude: {cruise_altitude_feet} feet")
    print(f"Expected Endurance: {expected_endurance_minutes} minutes")
    print("-" * 30)

    # Read NACA wing data using the init function
    naca_data_list_of_dicts = read_naca_data()

    if not naca_data_list_of_dicts:
        print("No NACA data found using naca_reader.init(). Cannot run tests.")
        return

    calculator = FuelFlightProfileCalculator()

    for profile_dict in naca_data_list_of_dicts:
        # Extract profile name and relevant data using dictionary keys
        profile_name = profile_dict.get("NACA Profile", "Unknown Profile")

        # Safely extract Cl and Cd using dictionary keys, handling potential errors
        rotation_cl = 0.0
        cruise_cd = 0.0
        try:
            rotation_cl_str = profile_dict.get("High Lift - Max Cl (approx)")
            if rotation_cl_str is not None:
                rotation_cl = float(rotation_cl_str)

            cruise_cd_str = profile_dict.get("Cruise - Cd (approx)")
            if cruise_cd_str is not None:
                cruise_cd = float(cruise_cd_str)

        except ValueError as e:
            print(f"  Warning: Could not convert Cl or Cd to float for profile {profile_name}: {e}")
            # Keep Cl and Cd as 0.0

        print(f"Testing with Wing Profile: {profile_name}")

        wing_profile_details = {
            "name": profile_name,
            "data": profile_dict, # Keep original dictionary data for reference
            "High Lift - Max Cl (approx)": rotation_cl, # Extracted value
            "Cruise - Cd (approx)": cruise_cd # Extracted value
        }


        endurance_minutes, distance_nm, rotation_speed_knots, how_terminated = calculator.calculate_profile(
            mtow=mtow,
            powerplant_details=powerplant_details,
            cruise_speed=cruise_speed_knots,
            cruise_altitude=cruise_altitude_feet,
            wing_profile=wing_profile_details,
            wing_area_sq_m=wing_area_sq_m # Pass the wing area
        )

        print(f"  Calculated Endurance: {endurance_minutes:.2f} minutes")
        print(f"  Calculated Distance: {distance_nm:.2f} nautical miles")
        print(f"  Estimated Rotation Speed: {rotation_speed_knots:.2f} knots")
        print(f"  Termination Reason: {how_terminated}")

        # Compare calculated endurance to expected endurance
        # Allow for a small tolerance due to potential floating point inaccuracies
        tolerance = 0.1
        if abs(endurance_minutes - expected_endurance_minutes) <= tolerance:
            print(f"  Endurance comparison: Matches expected endurance ({expected_endurance_minutes:.2f} minutes)")
        else:
            print(f"  Endurance comparison: Does NOT match expected endurance (Expected: {expected_endurance_minutes:.2f} minutes)")

        print("-" * 30)


        endurance_minutes, distance_nm, rotation_speed_knots, how_terminated = calculator.calculate_profile(
            mtow=mtow,
            powerplant_details=powerplant_details,
            cruise_speed=cruise_speed_knots,
            cruise_altitude=cruise_altitude_feet,
            wing_profile=wing_profile_details,
            wing_area_sq_m=wing_area_sq_m # Pass the wing area
        )

        print(f"  Calculated Endurance: {endurance_minutes:.2f} minutes")
        print(f"  Calculated Distance: {distance_nm:.2f} nautical miles")
        print(f"  Estimated Rotation Speed: {rotation_speed_knots:.2f} knots")
        print(f"  Termination Reason: {how_terminated}")

        # Compare calculated endurance to expected endurance
        # Allow for a small tolerance due to potential floating point inaccuracies
        tolerance = 0.1
        if abs(endurance_minutes - expected_endurance_minutes) <= tolerance:
            print(f"  Endurance comparison: Matches expected endurance ({expected_endurance_minutes:.2f} minutes)")
        else:
            print(f"  Endurance comparison: Does NOT match expected endurance (Expected: {expected_endurance_minutes:.2f} minutes)")

        print("-" * 30)

if __name__ == "__main__":
    run_fuel_flight_profile_test()
