
def calculate_parabolic_drag_polar(C_L: float, C_D0: float, k: float) -> tuple[float, float]:
    """
    Calculates the total drag coefficient (CD) and Lift-to-Drag ratio (L/D)
    using the parabolic drag polar model.

    CD = C_D0 + k * C_L^2
    L/D = C_L / CD

    Args:
        C_L (float): Lift Coefficient.
        C_D0 (float): Zero-Lift Drag Coefficient.
        k (float): Induced Drag Factor.

    Returns:
        tuple[float, float]: A tuple containing (C_D, L_D_ratio).

    Raises:
        ValueError: If k or C_D0 are non-positive, or if C_L is too low resulting in non-positive CD.
    """
    if C_D0 <= 0:
        raise ValueError("Zero-Lift Drag Coefficient (C_D0) must be positive.")
    if k <= 0:
        raise ValueError("Induced Drag Factor (k) must be positive.")

    # Calculate total drag coefficient
    C_D = C_D0 + k * C_L**2

    if C_D <= 0:
        # This can happen if C_L is very small (near zero) and C_D0 is very small,
        # or due to floating point inaccuracies for C_L=0.
        # Ensure C_D is effectively positive for meaningful L/D.
        if C_L == 0:
            return C_D0, 0.0 # L/D is 0 when C_L is 0 (no lift, only drag)
        else:
            raise ValueError(f"Calculated C_D ({C_D}) is not positive. Check inputs.")

    # Calculate Lift-to-Drag ratio
    L_D_ratio = C_L / C_D

    return C_D, L_D_ratio

