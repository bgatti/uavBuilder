from parasitic_drag import calculate_parasitic_drag_power

def calculate_flight_power_units(
    mass_plane_kg,
    wing_span_m,
    wing_area_m2,
    velocity_flight_ms,
    zero_lift_drag_coefficient,
    gravity_ms2=9.81,
    density_air_kgm3=1.225
):
    """
    Calculates the total power required for level, unaccelerated flight.

    This function integrates both induced drag (from lift) and parasitic drag 
    (from the airframe's shape and skin friction) to provide a more accurate 
    power estimate.

    Args:
        mass_plane_kg (float): Total mass of the aircraft (kg).
        wing_span_m (float): Wingspan of the aircraft (m).
        wing_area_m2 (float): Wing area of the aircraft (m^2).
        velocity_flight_ms (float): Forward velocity of the aircraft (m/s).
        zero_lift_drag_coefficient (float): Drag coefficient at zero lift.
        gravity_ms2 (float, optional): Acceleration due to gravity (m/s^2). Defaults to 9.81.
        density_air_kgm3 (float, optional): Density of air (kg/m^3). Defaults to 1.225.

    Returns:
        float: The total power required for flight in Watts (W).
    """
    # 1. Calculate Induced Drag Power (Power needed to overcome drag due to lift)
    lift_force_N = mass_plane_kg * gravity_ms2
    aspect_ratio = (wing_span_m ** 2) / wing_area_m2
    # Oswald efficiency factor (e) is assumed to be 1 for this simplified model
    induced_drag_coefficient = (lift_force_N / (0.5 * density_air_kgm3 * (velocity_flight_ms ** 2) * wing_area_m2)) ** 2 / (3.14159 * aspect_ratio)
    induced_drag_force_N = induced_drag_coefficient * 0.5 * density_air_kgm3 * (velocity_flight_ms ** 2) * wing_area_m2
    induced_power_W = induced_drag_force_N * velocity_flight_ms

    # 2. Calculate Parasitic Drag Power (Power needed to overcome airframe drag)
    parasitic_power_W = calculate_parasitic_drag_power(
        velocity_ms=velocity_flight_ms,
        wing_area_m2=wing_area_m2,
        zero_lift_drag_coefficient=zero_lift_drag_coefficient,
        density_air_kgm3=density_air_kgm3
    )

    # 3. Total Power is the sum of induced and parasitic power
    total_power_W = induced_power_W + parasitic_power_W
    
    return total_power_W

# --- Re-run the calculation for the Cessna 172S with the new function ---

# SI unit values for the Cessna 172S
cessna_mass_kg = 1111.0
cessna_wingspan_m = 11.0
cessna_wing_area_m2 = 16.2  # Approximate wing area for a Cessna 172
cessna_velocity_ms = 122 * 0.514444  # 122 knots to m/s
cessna_cd0 = 0.035  # Typical zero-lift drag coefficient for a light aircraft

# Call the updated function
power_required_W = calculate_flight_power_units(
    mass_plane_kg=cessna_mass_kg,
    wing_span_m=cessna_wingspan_m,
    wing_area_m2=cessna_wing_area_m2,
    velocity_flight_ms=cessna_velocity_ms,
    zero_lift_drag_coefficient=cessna_cd0
)

# Convert to horsepower for context
power_required_hp = power_required_W / 745.7

print("--- Using the updated function with a comprehensive drag model ---")
print(f"Calculated Power Required for Flight:")
print(f"  - In Watts: {power_required_W:,.2f} W")
print(f"  - In Horsepower: {power_required_hp:,.2f} hp")
