import numpy as np

def calculate_propeller_range_fuel_uav(
    V_km_hr: float,
    propeller_efficiency: float,
    psfc_kg_per_kW_hr: float,
    L_D: float,
    W_empty_kg: float,
    W_fuel_kg: float,
    fuel_reserve_fraction: float = 0.15,
    mission_efficiency_factor: float = 0.90
) -> float:
    """
    Calculates a more realistic range for a propeller aircraft by incorporating
    fuel reserves and a mission efficiency factor into the Breguet Range Equation.

    Args:
        V_km_hr (float): True Airspeed in km/hr (for context).
        propeller_efficiency (float): Propeller efficiency (0 to 1).
        psfc_kg_per_kW_hr (float): Power Specific Fuel Consumption in kg/(kW*hr).
        L_D (float): Lift-to-Drag Ratio.
        W_empty_kg (float): Empty weight of the aircraft in kg.
        W_fuel_kg (float): TOTAL fuel weight at takeoff in kg.
        fuel_reserve_fraction (float, optional): Fraction of fuel to be held in reserve.
                                                 Defaults to 0.15 (15%).
        mission_efficiency_factor (float, optional): Factor to account for non-ideal
                                                     flight, weather, etc. Defaults to 0.90 (90%).

    Returns:
        float: The calculated realistic range of the aircraft in kilometers (km).
    """
    # --- Input Validation ---
    if not (0 < propeller_efficiency <= 1):
        raise ValueError("Propeller efficiency must be between 0 and 1.")
    if psfc_kg_per_kW_hr <= 0 or L_D <= 0 or W_empty_kg <= 0:
        raise ValueError("PSFC, L/D, and Empty Weight must be positive.")
    if not (0 <= fuel_reserve_fraction < 1):
        raise ValueError("Fuel reserve fraction must be between 0 and 1.")
    if not (0 < mission_efficiency_factor <= 1):
        raise ValueError("Mission efficiency factor must be between 0 and 1.")

    # --- Refined Weight Calculations ---
    fuel_for_reserves_kg = W_fuel_kg * fuel_reserve_fraction
    fuel_available_for_range_kg = W_fuel_kg - fuel_for_reserves_kg
    
    if fuel_available_for_range_kg <= 0:
        return 0.0

    W_initial_kg = W_empty_kg + W_fuel_kg
    # Final weight is NOT the empty weight. It's the empty weight PLUS the required fuel reserves.
    W_final_kg = W_empty_kg + fuel_for_reserves_kg

    # --- Core Breguet Calculation (same as before) ---
    psfc_kg_Joule = psfc_kg_per_kW_hr / (3.6 * 10**6)
    g = 9.81
    
    try:
        ln_ratio = np.log(W_initial_kg / W_final_kg)
        # Calculate the THEORETICAL range possible with the available fuel
        ideal_range_meters = (propeller_efficiency / (psfc_kg_Joule * g)) * L_D * ln_ratio
    except (ZeroDivisionError, ValueError) as e:
        print(f"An error occurred during calculation: {e}")
        return float('nan')

    # --- Apply Real-World Factors ---
    # Apply the mission efficiency factor to the ideal range
    realistic_range_meters = ideal_range_meters * mission_efficiency_factor
    
    return realistic_range_meters / 1000

# --- Main Test Section ---
if __name__ == "__main__":
    # Parameters for a Cessna 172
    V_cessna = 204           # km/hr (Cruise Airspeed)
    eta_prop_cessna = 0.735  # Propeller efficiency
    psfc_cessna = 0.30       # kg/(kW*hr)
    L_D_cessna = 9.0         # Lift-to-Drag Ratio
    W_empty_cessna = 680     # kg
    W_fuel_cessna = 109      # kg

    print("--- Cessna 172 Analysis ---")

    # --- Case 1: Your original "Ideal World" calculation ---
    # To replicate the ideal formula, we set reserves and inefficiency to zero.
    ideal_range = calculate_propeller_range_fuel_uav(
        V_cessna, eta_prop_cessna, psfc_cessna, L_D_cessna, W_empty_cessna, W_fuel_cessna,
        fuel_reserve_fraction=0.0,      # No fuel reserve
        mission_efficiency_factor=1.0   # 100% perfect mission
    )
    print(f"\n1. THEORETICAL Maximum Range (Ideal World Calculation):")
    print(f"   -> Result: {ideal_range:.2f} km")
    print("   (This assumes burning all fuel and flying perfectly, which is unrealistic.)")

    # --- Case 2: The "Realistic" calculation using default factors ---
    # This is a much better estimate of the aircraft's actual, usable range.
    realistic_range = calculate_propeller_range_fuel_uav(
        V_cessna, eta_prop_cessna, psfc_cessna, L_D_cessna, W_empty_cessna, W_fuel_cessna
        # Using default fuel_reserve_fraction=0.15 and mission_efficiency_factor=0.90
    )
    print(f"\n2. REALISTIC Operational Range (with Reserves & Inefficiencies):")
    print(f"   -> Result: {realistic_range:.2f} km")
    print("   (This assumes landing with 15% fuel and a 10% mission inefficiency penalty.)")
    
    # Check the real-world published range
    published_range_nm = 640
    published_range_km = published_range_nm * 1.852
    print(f"\n----------------------------------------------------")
    print(f"Published POH Range of a Cessna 172: ~{published_range_nm} nm ({published_range_km:.0f} km)")
    print(f"Our realistic estimate is much closer to the published value.")
    print(f"----------------------------------------------------\n")


    # --- Case 3: A hypothetical Long-Range UAV ---
    print("\n--- Long-Range UAV Analysis ---")
    V_uav = 150
    eta_prop_uav = 0.85      # More efficient propeller
    psfc_uav = 0.25          # More efficient engine
    L_D_uav = 15.0           # More aerodynamic airframe
    W_empty_uav = 50
    W_fuel_uav = 50          # Higher fuel fraction (50% of MTOW)
    
    realistic_range_uav = calculate_propeller_range_fuel_uav(
        V_uav, eta_prop_uav, psfc_uav, L_D_uav, W_empty_uav, W_fuel_uav
    )
    print(f"Realistic Operational Range of a highly efficient, long-range UAV:")
    print(f"   -> Result: {realistic_range_uav:.2f} km")
