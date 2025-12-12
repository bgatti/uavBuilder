import math

# 1. Log Scaled Values Class
class LogScaledParameter:
    """
    Manages a parameter with a defined range, providing a value
    that can be set on a logarithmic scale using a percentage (0-100).

    The `value` property represents the actual physical value (e.g., 150 kg).
    The `percent` property (0-100) represents the position on a logarithmic
    scale between the minimum and maximum values.

    Attributes:
        name (str): The name of the parameter (e.g., "Takeoff Weight").
        unit (str): The unit of measurement (e.g., "kg").
        min_val (float): The minimum value of the range.
        max_val (float): The maximum value of the range.
    """
    def __init__(self, name: str, unit: str, min_val: float, max_val: float):
        if not (isinstance(min_val, (int, float)) and isinstance(max_val, (int, float))):
             raise TypeError("Minimum and maximum values must be numbers.")
        if min_val <= 0 or max_val <= 0:
            raise ValueError("Minimum and maximum values must be positive for log scaling.")
        if min_val > max_val:
            raise ValueError("Minimum value must not be greater than maximum value.")
            
        self.name = name
        self.unit = unit
        self.min_val = float(min_val)
        self.max_val = float(max_val)
        
        # Internal storage for the percentage
        self._percent: float = 0.0
        
        # Set default value to the logarithmic midpoint (50%)
        self.percent = 50.0

    @property
    def value(self) -> float:
        """Calculates the physical value based on the current percentage using a log scale."""
        log_min = math.log(self.min_val)
        log_max = math.log(self.max_val)
        # Linear interpolation in log space
        log_val = log_min + (self._percent / 100.0) * (log_max - log_min)
        return math.exp(log_val)

    @value.setter
    def value(self, new_val: float):
        """Sets the internal percentage based on a given physical value."""
        if not (self.min_val <= new_val <= self.max_val):
            raise ValueError(
                f"Value {new_val} for '{self.name}' is outside the allowed range "
                f"[{self.min_val}, {self.max_val}] {self.unit}."
            )
        
        log_min = math.log(self.min_val)
        log_max = math.log(self.max_val)
        log_new_val = math.log(new_val)
        
        # Inverse interpolation to find the percentage
        self._percent = 100.0 * (log_new_val - log_min) / (log_max - log_min)

    @property
    def percent(self) -> float:
        """The percentage (0-100) representing the position on the logarithmic scale."""
        return self._percent

    @percent.setter
    def percent(self, new_percent: float):
        """Sets the internal percentage, ensuring it is within the 0-100 range."""
        if not (0 <= new_percent <= 100):
            raise ValueError("Percentage must be between 0 and 100.")
        self._percent = float(new_percent)

    def __repr__(self) -> str:
        """Provides a developer-friendly representation of the object."""
        return (f"LogScaledParameter(name='{self.name}', unit='{self.unit}', "
                f"min={self.min_val}, max={self.max_val}, "
                f"percent={self.percent:.1f}, value={self.value:.2f})")

    def __str__(self) -> str:
        """Provides a user-friendly string representation."""
        return (f"{self.name}: {self.value:.2f} {self.unit} "
                f"({self.percent:.1f}% of log range [{self.min_val}, {self.max_val}])")

    def score(self, actual_value: float) -> float:
        """
        Scores how well an actual value fits within the target range [min_val, max_val].
        A score of 1.0 is achieved at the center of the range.
        The score decreases towards the edges of the range and is penalized if outside.
        """
        target_min = self.min_val
        target_max = self.max_val

        # Handle the case where the range is a single point (scalar target)
        if target_min == target_max:
            if actual_value <= 0 or target_min <= 0:
                return 0.0
            # Score based on simple ratio for scalar targets
            return min(actual_value, target_min) / max(actual_value, target_min)

        # Penalize values outside the specified range
        if actual_value < target_min:
            return actual_value / target_min  # Score is < 1.0
        if actual_value > target_max:
            return target_max / actual_value  # Score is < 1.0

        # If inside the range, score based on proximity to the center
        center_value = (target_min + target_max) / 2.0
        max_distance_from_center = (target_max - target_min) / 2.0
        
        if max_distance_from_center <= 0:
            return 1.0 # Should not happen due to min==max check, but for safety

        distance_from_center = abs(actual_value - center_value)
        
        # Score is 1.0 at the center, decreasing linearly to 0.0 at the edges
        score = 1.0 - (distance_from_center / max_distance_from_center)
        
        return max(0.0, score)


# 2. Fixed Wing Parameters Class (Replaces the Dictionary)
class FixedWingParameters:
    """
    A container for all configurable parameters of a fixed-wing UAV.
    
    Each attribute is an instance of LogScaledParameter, providing a structured
    and explicit way to access and modify UAV specifications.
    """
    def __init__(self):
        self.name = "Default"
        self.takeoff_weight = LogScaledParameter(
            name="Takeoff Weight", 
            unit="kg", 
            min_val=5, 
            max_val=250
        )
        self.cruise_speed = LogScaledParameter(
            name="Cruise Speed", 
            unit="km/h", 
            min_val=30, 
            max_val=600
        )
        self.endurance = LogScaledParameter(
            name="Endurance", 
            unit="hours", 
            min_val=(5 / 60),  # 5 minutes
            max_val=10
        )
        self.wingspan = LogScaledParameter(
            name="Wingspan", 
            unit="m", 
            min_val=0.3, 
            max_val=3
        )
        self.payload_capacity = LogScaledParameter(
            name="Payload Capacity", 
            unit="kg", 
            min_val=0.2, 
            max_val=30
        )

    def __str__(self) -> str:
        """Provides a user-friendly summary of all parameters."""
        param_list = [
            f"  - {self.takeoff_weight}",
            f"  - {self.cruise_speed}",
            f"  - {self.endurance}",
            f"  - {self.wingspan}",
            f"  - {self.payload_capacity}"
        ]
        return "\n".join(param_list)

# Instantiate the parameters object
fixed_wing_parameters = FixedWingParameters()


# 3. Main execution block (if __name__ == "__main__") for testing
if __name__ == "__main__":
    print("--- UAV Parameterization Tool ---")
    print("\n[INFO] This script demonstrates the LogScaledParameter class within a dedicated container object.")
    
    print("\n--- Default UAV Specs (Initialized to 50% on Log Scale) ---")
    print(fixed_wing_parameters)
        
    print("\n--- Example 1: Adjusting Endurance via Percentage ---")
    print("Setting Endurance to 0% (minimum).")
    # Access via attribute instead of dictionary key
    fixed_wing_parameters.endurance.percent = 0
    print(f"  - {fixed_wing_parameters.endurance}")
    
    print("\nSetting Endurance to 100% (maximum).")
    fixed_wing_parameters.endurance.percent = 100
    print(f"  - {fixed_wing_parameters.endurance}")

    print("\n--- Example 2: Adjusting Takeoff Weight via Value ---")
    new_weight = 50.0
    print(f"Setting Takeoff Weight to a specific value: {new_weight} kg.")
    # Access via attribute
    fixed_wing_parameters.takeoff_weight.value = new_weight
    print(f"  - {fixed_wing_parameters.takeoff_weight}")
    
    print("\n--- Example 3: Handling Invalid Input ---")
    try:
        print("Attempting to set cruise speed beyond its maximum limit...")
        # Access via attribute
        fixed_wing_parameters.cruise_speed.value = 700
    except ValueError as e:
        print(f"  [SUCCESS] Caught expected error: {e}")

    try:
        print("\nAttempting to set payload percentage to an invalid value...")
        # Access via attribute
        fixed_wing_parameters.payload_capacity.percent = -10
    except ValueError as e:
        print(f"  [SUCCESS] Caught expected error: {e}")
