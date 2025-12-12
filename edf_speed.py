# edf_speed.py

import numpy as np

def estimate_modified_cruise_speed(power_w: float, params) -> float:
    """
    Estimates cruise speed based on EDF power, modified by an endurance factor
    and a size-based scaling factor to make larger aircraft slightly slower.
    """
    EMPIRICAL_A = 0.19815
    EMPIRICAL_B = 0.6246
    clipped_power_w = np.clip(power_w, 200, 20000)
    base_speed_kts = EMPIRICAL_A * (clipped_power_w ** EMPIRICAL_B)

    # Introduce a size-based penalty. Larger aircraft (higher power) are made
    # slightly less aerodynamically efficient, reducing their top speed.
    # The log term ensures the penalty is larger for bigger power systems.
    size_penalty_factor = 1.0 - 0.10 * np.log10(max(1, clipped_power_w / 1000.0))
    
    MIN_SPEED_FACTOR = 0.35
    endurance_percent = params.endurance.percent
    speed_factor = 1.0 - (endurance_percent / 100.0) * (1.0 - MIN_SPEED_FACTOR)
    
    # Apply both the user-defined speed factor and the size penalty
    final_speed_kts = base_speed_kts * speed_factor * size_penalty_factor
    
    return final_speed_kts
