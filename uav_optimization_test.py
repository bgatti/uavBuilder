import random
import math
from optimizer_utils import optimize_with_dual_annealing, optimize_with_differential_evolution

# --- Mock Data for UAV Components ---

motor_options = [
    {"name": "Motor Small", "takeoff_factor": 1.2, "range_factor": 0.8, "payload_potential": 1.0},
    {"name": "Motor Medium", "takeoff_factor": 1.0, "range_factor": 1.0, "payload_potential": 1.5},
    {"name": "Motor Large", "takeoff_factor": 0.8, "range_factor": 1.1, "payload_potential": 2.0},
]

wing_options = [
    {"name": "Wing Profile 1", "takeoff_factor": 1.1, "range_factor": 1.2, "payload_potential": 0.9},
    {"name": "Wing Profile 2", "takeoff_factor": 1.0, "range_factor": 1.0, "payload_potential": 1.0},
    {"name": "Wing Profile 3", "takeoff_factor": 0.9, "range_factor": 0.8, "payload_potential": 1.1},
]

battery_options = [
    {"name": "Battery Small", "takeoff_factor": 1.0, "range_factor": 0.9, "payload_potential": 0.8},
    {"name": "Battery Medium", "takeoff_factor": 1.0, "range_factor": 1.0, "payload_potential": 1.0},
    {"name": "Battery Large", "takeoff_factor": 1.0, "range_factor": 1.1, "payload_potential": 1.2},
]

# Combine categories
all_uav_components = [motor_options, wing_options, battery_options]

# --- UAV Fitness Function ---
# This function evaluates a combination of UAV components based on
# takeoff distance (minimize), range (maximize), and payload potential (maximize).

def uav_fitness_function(combination_indices):
    """
    Evaluates the fitness of a combination of UAV components.

    Args:
        combination_indices (list): A list of indices, where each index
                                    corresponds to the selected component in
                                    the respective category (motor, wing, battery).

    Returns:
        float: The calculated fitness score. Lower is better for minimization.
    """
    if len(combination_indices) != len(all_uav_components):
        raise ValueError("Combination indices must match the number of component categories")

    # Convert float indices from optimizer to integers
    integer_combination_indices = [int(round(index)) for index in combination_indices]

    selected_components = [all_uav_components[i][integer_combination_indices[i]] for i in range(len(all_uav_components))]

    # --- Fitness Calculation Logic ---
    # Combine objectives: minimize takeoff distance, maximize range, maximize payload.
    # We need a single scalar value to minimize.
    # A simple approach is to negate the values we want to maximize and sum them.
    # Lower fitness value is better.

    # Base values (can be arbitrary, factors will scale them)
    base_takeoff_distance = 100.0
    base_range = 500.0
    base_payload_potential = 10.0

    # Calculate combined factors for each objective
    combined_takeoff_factor = selected_components[0].get("takeoff_factor", 1.0) * \
                              selected_components[1].get("takeoff_factor", 1.0) * \
                              selected_components[2].get("takeoff_factor", 1.0)

    combined_range_factor = selected_components[0].get("range_factor", 1.0) * \
                            selected_components[1].get("range_factor", 1.0) * \
                            selected_components[2].get("range_factor", 1.0)

    combined_payload_potential = selected_components[0].get("payload_potential", 1.0) * \
                                 selected_components[1].get("payload_potential", 1.0) * \
                                 selected_components[2].get("payload_potential", 1.0)

    # Calculate objective values
    takeoff_distance = base_takeoff_distance * combined_takeoff_factor
    range_value = base_range * combined_range_factor
    payload_potential_value = base_payload_potential * combined_payload_potential

    # Combine objectives into a single fitness score to MINIMIZE
    # We want to minimize takeoff_distance, maximize range, maximize payload_potential.
    # So, fitness = takeoff_distance - range_value - payload_potential_value
    # A smaller (more negative) fitness value is better.

    fitness = takeoff_distance - range_value - payload_potential_value

    # Print selected components and calculated values for debugging/understanding
    print("\nEvaluating Combination:")
    for component in selected_components:
        print(f"- {component['name']}")
    print(f"  Calculated Takeoff Distance: {takeoff_distance:.2f}")
    print(f"  Calculated Range: {range_value:.2f}")
    print(f"  Calculated Payload Potential: {payload_potential_value:.2f}")
    print(f"  Fitness Score: {fitness:.2f}")


    return fitness

# --- Example Usage ---

if __name__ == "__main__":
    # Define the bounds for the optimization.
    # For each component category, the bounds are (0, number_of_options - 1)
    bounds = [(0, len(category) - 1) for category in all_uav_components]

    print("Starting UAV Optimization Test...")

    # Example using Dual Annealing
    print("\n--- Dual Annealing Optimization ---")
    best_indices_da, best_fitness_da = optimize_with_dual_annealing(uav_fitness_function, bounds)
    print("\n--- Dual Annealing Results ---")
    print(f"Best Combination Indices: {best_indices_da}")
    print(f"Best Fitness (to minimize): {best_fitness_da:.2f}")
    selected_components_da = [all_uav_components[i][best_indices_da[i]] for i in range(len(all_uav_components))]
    print("Selected Components:")
    for component in selected_components_da:
        print(f"- {component['name']}")

    # Example using Differential Evolution
    print("\n--- Differential Evolution Optimization ---")
    best_indices_de, best_fitness_de = optimize_with_differential_evolution(uav_fitness_function, bounds)
    print("\n--- Differential Evolution Results ---")
    print(f"Best Combination Indices: {best_indices_de}")
    print(f"Best Fitness (to minimize): {best_fitness_de:.2f}")
    selected_components_de = [all_uav_components[i][best_indices_de[i]] for i in range(len(all_uav_components))]
    print("Selected Components:")
    for component in selected_components_de:
        print(f"- {component['name']}")

    # Note: For a real-world scenario, the fitness function would be much more complex
    # and based on physics, aerodynamics, battery performance models, etc.
    # The mock data and fitness function here are simplified for demonstration.
