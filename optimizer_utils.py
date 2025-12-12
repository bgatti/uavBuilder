import random
import math
from scipy.optimize import dual_annealing, differential_evolution
# You might need to install scikit-optimize: pip install scikit-optimize
# from skopt import gp_minimize
# from skopt.space import Integer # Needed for Bayesian Optimization

def optimize_with_dual_annealing(fitness_func, bounds):
    """
    Uses Dual Annealing for optimization.
    Suitable for global optimization of complex functions.
    Aims to minimize the fitness_func, so negate if maximizing.
    """
    result = dual_annealing(fitness_func, bounds)
    best_combination_indices = [int(round(x)) for x in result.x] # Indices are integers
    best_fitness = result.fun

    return best_combination_indices, best_fitness

def optimize_with_differential_evolution(fitness_func, bounds):
    """
    Uses Differential Evolution for optimization.
    Another global optimization algorithm.
    Aims to minimize the fitness_func, so negate if maximizing.
    """
    result = differential_evolution(fitness_func, bounds, strategy='best1bin', popsize=10, mutation=(0.5, 1), recombination=0.7, seed=None, disp=False, polish=True, init='latinhypercube')
    best_combination_indices = [int(round(x)) for x in result.x] # Indices are integers
    best_fitness = result.fun

    return best_combination_indices, best_fitness

def calculate_performance(engine_rpm, diameter_inches, pitch_inches, number_of_blades, speed_mps):
    """
    Calculates the performance of a propeller under given conditions.

    Args:
        engine_rpm (float): Engine speed in revolutions per minute.
        diameter_inches (float): Propeller diameter in inches.
        pitch_inches (float): Propeller pitch in inches.
        number_of_blades (int): Number of propeller blades.
        speed_mps (float): The aircraft's speed in meters per second (e.g., cruise speed or 0 for static).

    Returns:
        dict: A dictionary containing the calculated performance metrics.
    """
    if engine_rpm <= 0 or diameter_inches <= 0 or pitch_inches <= 0:
        raise ValueError("RPM, diameter, and pitch must be positive values.")

    # Physical constants
    AIR_DENSITY_KG_M3 = 1.225  # Sea level standard atmosphere
    SPEED_OF_SOUND_MPS = 343.0

    # Convert inputs to standard units (meters, seconds)
    prop_diameter_m = diameter_inches * 0.0254
    prop_pitch_m = pitch_inches * 0.0254
    rpm_sec = engine_rpm / 60.0

    # Advance Ratio (J)
    advance_ratio = (speed_mps) / (rpm_sec * prop_diameter_m) if rpm_sec > 0 else 0

    # Thrust Coefficient (Ct) - Simplified linear model
    CT_STATIC = 0.12
    J_ZERO_THRUST = 0.8
    thrust_coeff = max(0, CT_STATIC - (CT_STATIC / J_ZERO_THRUST) * advance_ratio)

    # Calculated Thrust (T) in Newtons
    blade_factor = 1 + (number_of_blades - 2) * 0.2
    calculated_thrust_N = thrust_coeff * AIR_DENSITY_KG_M3 * (rpm_sec**2) * (prop_diameter_m**4) * blade_factor

    # Tip Speed
    tip_speed_mps = math.pi * prop_diameter_m * rpm_sec
    mach_tip = tip_speed_mps / SPEED_OF_SOUND_MPS
    
    # Propeller air speed (theoretical)
    air_speed_mps = prop_pitch_m * rpm_sec

    return {
        'calculated_thrust_N': calculated_thrust_N,
        'advance_ratio_J': advance_ratio,
        'thrust_coefficient_Ct': thrust_coeff,
        'tip_speed_mps': tip_speed_mps,
        'tip_speed_mach': mach_tip,
        'air_speed_mps': air_speed_mps,
    }

def score_propeller(engine_rpm, diameter_inches, pitch_inches, number_of_blades, cruise_speed_mps, target_thrust_N, price_usd=0.0):
    """
    Scores a propeller based on its ability to meet a target thrust at cruise speed,
    its operational efficiency, and physical limitations like tip speed.

    The scoring system is based on penalties; a lower overall score is better.

    Args:
        engine_rpm (float): Engine speed in revolutions per minute.
        diameter_inches (float): Propeller diameter in inches.
        pitch_inches (float): Propeller pitch in inches.
        number_of_blades (int): Number of propeller blades.
        cruise_speed_mps (float): The aircraft's target cruise speed in meters per second.
        target_thrust_N (float): The required thrust in Newtons to maintain cruise speed.
        price_usd (float, optional): Propeller price in USD. Defaults to 0.0.

    Returns:
        dict: A dictionary containing the performance metrics and the final scores.
    """
    
    performance = calculate_performance(
        engine_rpm=engine_rpm,
        diameter_inches=diameter_inches,
        pitch_inches=pitch_inches,
        number_of_blades=number_of_blades,
        speed_mps=cruise_speed_mps
    )

    calculated_thrust_N = performance['calculated_thrust_N']
    mach_tip = performance['tip_speed_mach']
    air_speed_mps = performance['air_speed_mps']

    # Penalty 1: Thrust Performance
    thrust_penalty = 0.0
    if calculated_thrust_N < target_thrust_N:
        thrust_penalty = 5 * (target_thrust_N - calculated_thrust_N) / target_thrust_N if target_thrust_N > 0 else 1.0

    # Penalty 2: Efficiency Proxy
    efficiency_penalty = 0.0
    if air_speed_mps > cruise_speed_mps and cruise_speed_mps > 0:
        slip_ratio = (air_speed_mps - cruise_speed_mps) / cruise_speed_mps
        efficiency_penalty = slip_ratio * 0.25

    # Penalty 3: Tip Speed
    tip_speed_penalty = 0.0
    if mach_tip >= 0.9:
        tip_speed_penalty = 10.0 * (mach_tip - 0.9)

    # Overall score
    overall_score = (thrust_penalty * 1.0) + (efficiency_penalty * 0.5) + (tip_speed_penalty * 2.0)
    
    # Price component
    price_score_component = price_usd * 0.001
    overall_score += price_score_component

    score_details = {
        **performance,
        # Input Parameters
        'engine_rpm': engine_rpm,
        'diameter_inches': diameter_inches,
        'pitch_inches': pitch_inches,
        'number_of_blades': number_of_blades,
        'cruise_speed_mps': cruise_speed_mps,
        'target_thrust_N': target_thrust_N,
        'price_usd': price_usd,
        # Scores
        'thrust_penalty': thrust_penalty,
        'efficiency_penalty': efficiency_penalty,
        'tip_speed_penalty': tip_speed_penalty,
        'price_score_component': price_score_component,
        'overall_score': overall_score,
    }

    return score_details

# def optimize_with_bayesian_optimization(fitness_func, dimensions, n_calls=50):
#     """
#     Uses Bayesian Optimization (using scikit-optimize).
#     Effective for optimizing expensive black-box functions.
#     Aims to minimize the fitness_func, so negate if maximizing.
#     """
#     # Dimensions should be a list of tuples or skopt.space.Dimension objects
#     # For integer indices, use skopt.space.Integer
#     # skopt_dimensions = [Integer(0, len(category)-1) for category in all_categories] # Example dimension creation

#     result = gp_minimize(fitness_func, dimensions, n_calls=n_calls, random_state=0)
#     best_combination_indices = [int(round(x)) for x in result.x]
#     best_fitness = result.fun

#     return best_combination_indices, best_fitness
