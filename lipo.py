# lipo.py (Corrected)

import os
import math

class Battery:
    """Represents a UAV battery pack with realistic trade-offs."""
    def __init__(self, weight_kg: float, c_rating: int, energy_wh: float, voltage: float, model_number: str = "Generic", num_batteries: int = 1):
        self.model_number = model_number
        self.num_batteries = num_batteries
        self.weight_kg = weight_kg * self.num_batteries
        self.c_rating = c_rating
        self.energy_wh = energy_wh * self.num_batteries
        self.voltage = voltage
        self.capacity_ah = self.energy_wh / self.voltage if self.voltage > 0 else 0
        self.max_power_w = self.energy_wh * self.c_rating
        self.total_energy_j = self.energy_wh * 3600

    @staticmethod
    def _calculate_energy_density(c_rating: int) -> float:
        """Calculates specific energy (Wh/kg) based on C-rating."""
        BASE_ENERGY_DENSITY_WH_KG = 210
        return BASE_ENERGY_DENSITY_WH_KG - 25 * math.log10(max(1, c_rating / 10))
    
    def check_power_output(self, required_power_w: float):
        """Checks if the battery can safely provide the required power."""
        if self.max_power_w < required_power_w * 1.2:
            raise ValueError(f"Battery cannot supply peak power. Needs {required_power_w * 1.2:.0f}W, but can only supply {self.max_power_w:.0f}W.")

    @classmethod
    def from_c_and_weight(cls, c_rating: int, max_weight_kg: float, cell_count: int = 6, num_batteries: int = 1) -> 'Battery':
        """Factory to create the best possible Battery within a weight budget."""
        if c_rating <= 0 or max_weight_kg <= 0: raise ValueError("C-rating and weight must be positive.")
        voltage = cell_count * 3.7
        energy_density = cls._calculate_energy_density(c_rating)
        energy_wh = (max_weight_kg / num_batteries) * energy_density
        return cls(weight_kg=max_weight_kg / num_batteries, c_rating=c_rating, energy_wh=energy_wh, voltage=voltage, num_batteries=num_batteries)

    @classmethod
    def from_df_row(cls, row, num_batteries: int = 1):
        """Creates a Battery instance from a DataFrame row."""
        return cls(
            weight_kg=row.get('weight_g', 0) / 1000,
            c_rating=row.get('c_rating', 40),  # Default C-rating if not specified
            energy_wh=row.get('energy_Wh', 0),
            voltage=row.get('nominalV', 0),
            model_number=row.get('Model Number', 'N/A'),
            num_batteries=num_batteries
        )

    def __repr__(self) -> str:
        density = self.energy_wh / self.weight_kg if self.weight_kg > 0 else 0
        return (f"Battery(Model: {self.model_number} x{self.num_batteries}, "
                f"Wt:{self.weight_kg:.2f}kg, C:{self.c_rating}, Ah:{self.capacity_ah:.1f}, "
                f"PMax:{self.max_power_w:,.0f}W, Dens:{density:.1f}Wh/kg)")
