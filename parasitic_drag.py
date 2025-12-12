def calculate_parasitic_drag_power(
    velocity_ms,
    wing_area_m2,
    zero_lift_drag_coefficient,
    density_air_kgm3=1.225
):
    """
    Estimates the power required to overcome parasitic drag for an airframe.

    Parasitic drag is composed of form drag, skin friction, and interference drag.
    This formula calculates the power (Force x Velocity) needed to counteract it.

    Args:
        velocity_ms (float): The true airspeed of the aircraft in meters per second (m/s).
        wing_area_m2 (float): The reference area (typically wing area) of the aircraft in square meters (m^2).
        zero_lift_drag_coefficient (float): A dimensionless number representing the airframe's
                                             drag at zero lift. A lower number means a more
                                             aerodynamically "clean" design.
        density_air_kgm3 (float, optional): The density of air in kg/m^3. Defaults to 1.225 (sea level).

    Returns:
        float: The power required to overcome parasitic drag, in Watts (W).
    """
    # Parasitic Drag Force (Dp) = 0.5 * rho * V^2 * A * Cd,0
    drag_force_N = 0.5 * density_air_kgm3 * (velocity_ms ** 2) * wing_area_m2 * zero_lift_drag_coefficient

    # Power (P) = Drag Force * Velocity
    power_W = drag_force_N * velocity_ms

    return power_W