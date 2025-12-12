import abc
from typing import Dict, Any, Tuple, Optional
from .flight_profile_calculator import FlightProfileCalculator

class FuelFlightProfileCalculator(FlightProfileCalculator):
    """
    Flight profile calculator for fixed-wing UAVs with liquid fuel engines.
    """
    def calculate_profile(
        self,
        mtow: float,
        powerplant_details: Dict[str, Any], # Expected keys: 'engine_hp': float, 'fuel_onboard_kg': float, 'fuel_consumption_kg_per_hr': float
        cruise_speed: float, # Cruise speed in knots
        cruise_altitude: float, # Cruise altitude in feet
        wing_profile: Dict[str, Any], # Wing profile details from naca_reader
        wing_area_sq_m: float # Wing area in square meters
    ) -> Tuple[float, float, float, str]:
        """
        Calculates the flight endurance, distance, rotation speed, and termination reason for a fuel-powered UAV.

        Args:
            mtow: Maximum Takeoff Weight in kg.
            powerplant_details: A dictionary containing details about the fuel powerplant.
                                Expected keys:
                                - 'engine_hp': Engine horsepower (float)
                                - 'fuel_onboard_kg': Initial fuel onboard in kg (float)
                                - 'fuel_consumption_kg_per_hr': Fuel consumption rate in kg per hour (float)
            cruise_speed: Cruise speed in knots.
            cruise_altitude: Cruise altitude in feet.
            wing_profile: A dictionary containing details about the wing profile.
                          Expected keys based on naca.csv:
                          - 'Rotation Cl': Maximum lift coefficient at takeoff configuration (float)
                          - 'Cruise Cd': Drag coefficient at cruise AoA (float)
            wing_area_sq_m: Wing area in square meters.

        Returns:
            A tuple containing:
            - endurance_minutes: Flight endurance in minutes.
            - distance_nm: Flight distance in nautical miles.
            - rotation_speed_knots: Estimated rotation speed in knots.
            - how_terminated: Reason for flight termination.
        """
        # Constants and conversions
        G = 9.80665 # m/s^2
        KNOTS_TO_MPS = 0.514444 # 1 knot = 0.514444 m/s
        HP_TO_WATTS = 745.7 # 1 horsepower = 745.7 Watts
        # Assume a propeller efficiency for converting engine power to thrust power
        PROPELLER_EFFICIENCY = 0.8 # Example value

        fuel_onboard_kg = powerplant_details.get('fuel_onboard_kg', 0.0)
        fuel_consumption_kg_per_hr_rate = powerplant_details.get('fuel_consumption_kg_per_hr', 0.0) # Use provided rate if available
        engine_hp = powerplant_details.get('engine_hp', 0.0)

        cruise_speed_knots = cruise_speed
        cruise_speed_mps = cruise_speed_knots * KNOTS_TO_MPS
        cruise_altitude_feet = cruise_altitude

        # Extract relevant data from wing profile
        # Need to handle potential missing keys or incorrect data types
        max_cl = float(wing_profile.get('High Lift - Max Cl (approx)', 0.0)) if wing_profile.get('High Lift - Max Cl (approx)') is not None else 0.0
        cruise_cd = float(wing_profile.get('Cruise Cd', 0.0)) if wing_profile.get('Cruise Cd') is not None else 0.0

        # --- Takeoff Speed Calculation ---
        # Assume takeoff at sea level for air density
        air_density_takeoff = self.get_air_density(0.0) # Sea level

        takeoff_airspeed_mps = self.calculate_takeoff_airspeed(
            mtow_kg=mtow,
            wing_area_sq_m=wing_area_sq_m,
            cl_max_takeoff=max_cl,
            air_density_kg_m3=air_density_takeoff
        )
        rotation_speed_knots = takeoff_airspeed_mps / KNOTS_TO_MPS # Use takeoff speed as estimate for rotation speed

        # Check for takeoff failure
        if max_cl <= 0 or wing_area_sq_m <= 0 or mtow <= 0:
             return 0.0, 0.0, 0.0, "FAIL_TAKEOFF" # Cannot calculate takeoff speed

        # --- Cruise Performance Calculation ---
        air_density_cruise = self.get_air_density(cruise_altitude_feet)

        drag_force_n = self.calculate_drag_at_cruise(
            cruise_speed_mps=cruise_speed_mps,
            air_density_kg_m3=air_density_cruise,
            wing_area_sq_m=wing_area_sq_m,
            cd_cruise=cruise_cd
        )

        # Power required for cruise (Watts)
        power_required_watts = drag_force_n * cruise_speed_mps

        # Available engine power (Watts) considering propeller efficiency
        available_engine_power_watts = engine_hp * HP_TO_WATTS * PROPELLER_EFFICIENCY

        # Check if enough power for cruise
        if available_engine_power_watts <= power_required_watts:
             return 0.0, 0.0, rotation_speed_knots, "FAIL_CLIMB" # Or insufficient power for cruise

        # Calculate fuel burn rate at cruise based on power required and engine efficiency
        # This is a simplified model. A more accurate model would use engine-specific fuel consumption maps.
        # Assuming fuel consumption is proportional to power output
        # Need a reference fuel consumption rate at a known power output.
        # If fuel_consumption_kg_per_hr_rate is provided, we can use that directly for a simpler model.
        # If not, we would need more engine data (e.g., specific fuel consumption).

        endurance_hours = 0.0
        how_terminated = "UNKNOWN"

        if fuel_consumption_kg_per_hr_rate > 0:
             # Use the provided fuel consumption rate for endurance calculation
             endurance_hours = fuel_onboard_kg / fuel_consumption_kg_per_hr_rate
             how_terminated = "FUEL_EXHAUSTION"
        else:
             # If fuel consumption rate is not provided, we cannot calculate endurance with this model
             return 0.0, 0.0, rotation_speed_knots, "UNKNOWN_FUEL_CONSUMPTION"


        endurance_minutes = endurance_hours * 60.0
        distance_nm = cruise_speed_knots * endurance_hours # Distance based on cruise speed and endurance

        # Final check for other potential failures (simplified)
        if endurance_minutes <= 0:
             how_terminated = "FAIL_CLIMB" # Indicate inability to sustain flight

        return endurance_minutes, distance_nm, rotation_speed_knots, how_terminated
