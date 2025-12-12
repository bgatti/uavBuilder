import abc
from typing import Dict, Any, Tuple, Optional

class FlightProfileCalculator(abc.ABC):
    """
    Abstract base class for calculating flight profiles for fixed-wing UAVs.
    Subclasses should implement the calculate_profile method for specific powerplant types.
    """

    @abc.abstractmethod
    def calculate_profile(
        self,
        mtow: float,  # Maximum Takeoff Weight in kg
        powerplant_details: Dict[str, Any], # Details specific to the powerplant type
        cruise_speed: float, # Cruise speed in knots
        cruise_altitude: float, # Cruise altitude in feet
        wing_profile: Dict[str, Any] # Wing profile details from naca_reader
    ) -> Tuple[float, float, float, str]:
        """
        Calculates the flight endurance, distance, rotation speed, and termination reason.

        Args:
            mtow: Maximum Takeoff Weight in kg.
            powerplant_details: A dictionary containing details about the powerplant.
                                Expected keys and types depend on the powerplant type
                                (e.g., 'engine_hp': float, 'fuel_onboard_kg': float for fuel,
                                'battery_capacity_kwh': float for electric).
            cruise_speed: Cruise speed in knots.
            cruise_altitude: Cruise altitude in feet.
            wing_profile: A dictionary containing details about the wing profile,
                          likely obtained from a NACA reader.

        Returns:
            A tuple containing:
            - endurance_minutes: Flight endurance in minutes.
            - distance_nm: Flight distance in nautical miles.
            - rotation_speed_knots: Estimated rotation speed in knots.
            - how_terminated: Reason for flight termination (e.g., 'FUEL_EXHAUSTION',
                              'BATTERY_DEPLETION', 'FAIL_TAKEOFF', 'FAIL_CLIMB', 'MISSION_COMPLETE').
        """
        pass

    @staticmethod
    def get_air_density(altitude_feet: float) -> float:
        """
        Estimates air density at a given altitude using the International Standard Atmosphere (ISA) model.
        Simplified for altitudes up to 36,089 feet (11,000 meters).

        Args:
            altitude_feet: Altitude in feet.

        Returns:
            Air density in kg/m^3.
        """
        # ISA sea level conditions
        T0 = 288.15  # K
        P0 = 101325.0  # Pa
        rho0 = 1.225  # kg/m^3
        L = 0.0065  # K/m (temperature lapse rate)
        g = 9.80665  # m/s^2 (acceleration due to gravity)
        R = 287.058  # J/(kg·K) (specific gas constant for dry air)

        altitude_meters = altitude_feet * 0.3048

        if altitude_meters < 11000: # Troposphere
            T = T0 - L * altitude_meters
            P = P0 * (T / T0)**(g / (L * R))
            rho = P / (R * T)
            return rho
        else:
            # Simplified: assume constant temperature above 11km (stratosphere)
            # For a more accurate model, this would need to be expanded.
            print("Warning: Altitude above 11,000 meters. Using simplified density model.")
            T_11km = T0 - L * 11000
            P_11km = P0 * (T_11km / T0)**(g / (L * R))
            rho_11km = P_11km / (R * T_11km)
            # In the stratosphere (11km to 20km), temperature is constant at -56.5 C (216.65 K)
            # Density decreases exponentially with altitude
            # This simplified model just returns the density at 11km for altitudes >= 11km
            return rho_11km # Simplified

    @staticmethod
    def calculate_takeoff_airspeed(
        mtow_kg: float,
        wing_area_sq_m: float,
        cl_max_takeoff: float, # Maximum lift coefficient at takeoff configuration
        air_density_kg_m3: float # Air density at takeoff altitude
    ) -> float:
        """
        Calculates the estimated takeoff airspeed (stall speed) using the lift equation.

        Args:
            mtow_kg: Maximum Takeoff Weight in kg.
            wing_area_sq_m: Wing area in square meters.
            cl_max_takeoff: Maximum lift coefficient at takeoff configuration.
                            This should be obtained from wing profile data at rotation AoA.
            air_density_kg_m3: Air density at takeoff altitude in kg/m^3.

        Returns:
            Estimated takeoff airspeed in meters per second.
        """
        # Lift = 0.5 * rho * V^2 * A * Cl
        # At takeoff speed (stall speed), Lift = Weight = mtow_kg * g
        # V = sqrt((2 * Weight) / (rho * A * Cl_max))
        g = 9.80665 # m/s^2
        weight_n = mtow_kg * g

        if air_density_kg_m3 <= 0 or wing_area_sq_m <= 0 or cl_max_takeoff <= 0:
            print("Warning: Invalid input for takeoff airspeed calculation.")
            return float('inf') # Indicate inability to take off

        takeoff_airspeed_mps = (2 * weight_n / (air_density_kg_m3 * wing_area_sq_m * cl_max_takeoff))**0.5
        return takeoff_airspeed_mps

    @staticmethod
    def calculate_drag_at_cruise(
        cruise_speed_mps: float,
        air_density_kg_m3: float, # Air density at cruise altitude
        wing_area_sq_m: float,
        cd_cruise: float # Drag coefficient at cruise AoA
    ) -> float:
        """
        Calculates the estimated drag force at cruise using the drag equation.

        Args:
            cruise_speed_mps: Cruise speed in meters per second.
            air_density_kg_m3: Air density at cruise altitude in kg/m^3.
            wing_area_sq_m: Wing area in square meters.
            cd_cruise: Drag coefficient at cruise AoA.
                       This should be obtained from wing profile data at cruise AoA.

        Returns:
            Estimated drag force in Newtons.
        """
        # Drag = 0.5 * rho * V^2 * A * Cd
        if air_density_kg_m3 <= 0 or wing_area_sq_m <= 0 or cd_cruise < 0 or cruise_speed_mps < 0:
             print("Warning: Invalid input for drag calculation.")
             return float('nan') # Indicate invalid result

        drag_force_n = 0.5 * air_density_kg_m3 * (cruise_speed_mps**2) * wing_area_sq_m * cd_cruise
        return drag_force_n


# Example structure for specific powerplant implementations (to be added by user)

# class ElectricFlightProfileCalculator(FlightProfileCalculator):
#     def calculate_profile(
#         self,
#         mtow: float,
#         powerplant_details: Dict[str, Any], # Expected keys: 'battery_capacity_kwh': float, 'motor_efficiency': float
#         cruise_speed: float,
#         cruise_altitude: float,
#         wing_profile: Dict[str, Any]
#     ) -> Tuple[float, float, str]:
#         # Implement calculation logic for electric powerplant
#         pass


# class HybridFlightProfileCalculator(FlightProfileCalculator):
#     def calculate_profile(
#         self,
#         mtow: float,
#         powerplant_details: Dict[str, Any], # Expected keys: 'engine_hp': float, 'fuel_onboard_kg': float, 'fuel_consumption_kg_per_hr': float, 'battery_capacity_kwh': float, 'motor_efficiency': float
#         cruise_speed: float,
#         cruise_altitude: float,
#         wing_profile: Dict[str, Any]
#     ) -> Tuple[float, float, str]:
#         # Implement calculation logic for hybrid powerplant
#         pass
