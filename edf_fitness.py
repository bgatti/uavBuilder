import math
from edf_mission import run_mission_simulation
from edf_config import Aircraft, EDF
from uav_parameters import FixedWingParameters, LogScaledParameter

class Fitness:
    def __init__(self, fitness_score, parameter_scores):
        self.fitness_score = fitness_score
        self.parameter_scores = parameter_scores

    def __repr__(self):
        return f"Fitness(score={self.fitness_score:.2f}, params={self.parameter_scores})"

def fitness(params: FixedWingParameters, aircraft: Aircraft):
    """
    Calculates the fitness of an aircraft design by comparing its actual
    performance characteristics against the desired target parameters.
    The scoring for each parameter is now based on its proximity to the center of the defined range.
    """
    mission_path = run_mission_simulation(aircraft)

    # Score the aircraft's performance against the target parameter ranges
    scores = {
        'takeoff_weight': params.takeoff_weight.score(aircraft.mtow_kg),
        'cruise_speed': params.cruise_speed.score(aircraft.cruise_ias_kts * 1.852),  # km/h
        'endurance': params.endurance.score(mission_path.total_time_min / 60.0),  # hours
        'payload_capacity': params.payload_capacity.score(aircraft.payload_weight_kg),
        'wingspan': params.wingspan.score(aircraft.wing_area_m2 / params.wingspan.value) # Approximate wingspan score
    }

    # Calculate overall fitness score (geometric mean of individual scores)
    score_values = list(scores.values())
    overall_score = (math.prod(score_values)) ** (1.0 / len(score_values)) if score_values else 0.0

    return Fitness(overall_score, scores)

def set_range(param: LogScaledParameter, min_val: float, max_val: float):
    """Sets the min and max values for a UAVParameter."""
    param.min_val = min_val
    param.max_val = max_val

if __name__ == "__main__":
    print("--- EDF Fitness Demonstration (Center-Focused Scoring) ---")

    # Define a set of target parameters for a balanced design
    target_params = FixedWingParameters()
    target_params.name = "Balanced Target"
    # Set specific min/max for scoring demonstration
    set_range(target_params.takeoff_weight, 10, 20)
    set_range(target_params.cruise_speed, 100, 150)
    set_range(target_params.endurance, 1, 2)
    set_range(target_params.payload_capacity, 1, 3)

    print("\n--- Target Design Parameters ---")
    print(target_params)

    # Create a design to evaluate against the targets
    design_params = FixedWingParameters()
    design_params.name = "Initial Design"
    design_params.cruise_speed.percent = 60  # Aim for slightly faster cruise
    design_params.endurance.percent = 40    # Aim for slightly less endurance

    rules = {"c_rating": 50, "batt_motor_ratio": 2.5, "cruise_power_target": 70.0}
    
    # Design the aircraft based on the design parameters
    designed_aircraft = Aircraft.design_from_mission(design_params, rules, 15)

    print("\n--- Evaluating Designed Aircraft Against Targets ---")
    # The fitness function now uses the min/max from `target_params` for scoring
    final_fitness = fitness(target_params, designed_aircraft)
    
    print(f"\nDesigned Aircraft MTOW: {designed_aircraft.mtow_kg:.2f} kg")
    print(f"Designed Aircraft Cruise: {designed_aircraft.cruise_ias_kts * 1.852:.2f} km/h")
    mission_path = run_mission_simulation(designed_aircraft)
    print(f"Designed Aircraft Endurance: {mission_path.total_time_min / 60.0:.2f} hours")
    print(f"Designed Aircraft Payload: {designed_aircraft.payload_weight_kg:.2f} kg")
    
    print(f"\nFinal Fitness Score: {final_fitness.fitness_score:.3f}")
    print("Parameter Scores:")
    for name, score in final_fitness.parameter_scores.items():
        print(f"  - {name:<20}: {score:.3f}")
