"""Object models for the thermal battery simulation.

This module intentionally demonstrates constructors, inheritance, abstract
classes and method overriding for the Python practical experiments.
"""

from abc import ABC, abstractmethod


class ThermalComponent(ABC):
    """Abstract component that contributes thermal power to a battery cell."""

    def __init__(self, component_name):
        self.component_name = str(component_name).strip()
        if not self.component_name:
            raise ValueError("Component name cannot be empty")

    @abstractmethod
    def thermal_power_w(self, current_a, temperature_c, ambient_c, cooling_level):
        """Return heat contribution in watts (positive heats, negative cools)."""
        raise NotImplementedError


class BatteryCell(ThermalComponent):
    """A simplified battery cell with resistive heat generation."""

    def __init__(self, cell_id, initial_temperature_c=25.0, resistance_ohm=0.012,
                 thermal_capacity_j_per_c=480.0):
        super().__init__(f"Battery cell {cell_id}")
        self.cell_id = str(cell_id)
        self.temperature_c = float(initial_temperature_c)
        self.resistance_ohm = float(resistance_ohm)
        self.thermal_capacity_j_per_c = float(thermal_capacity_j_per_c)

    def thermal_power_w(self, current_a, temperature_c, ambient_c, cooling_level):
        # Joule heating: P = I^2 R.
        return float(current_a) ** 2 * self.resistance_ohm

    def update_temperature(self, net_power_w, dt_seconds):
        self.temperature_c += float(net_power_w) * float(dt_seconds) / self.thermal_capacity_j_per_c

    @property
    def status(self):
        if self.temperature_c >= 55.0:
            return "CRITICAL"
        if self.temperature_c >= 45.0:
            return "WARNING"
        return "NORMAL"

    def reset(self, temperature_c=25.0):
        self.temperature_c = float(temperature_c)

    def to_record(self):
        return {
            "cell_id": self.cell_id,
            "temperature_c": round(self.temperature_c, 2),
            "status": self.status,
        }


class CoolingUnit(ThermalComponent):
    """A simplified micro-channel cooling plate with an adjustable coolant level."""

    def __init__(self, cooling_coefficient_w_per_c=0.52):
        super().__init__("Cooling unit")
        self.cooling_coefficient_w_per_c = float(cooling_coefficient_w_per_c)

    def thermal_power_w(self, current_a, temperature_c, ambient_c, cooling_level):
        level = max(0, min(3, int(cooling_level)))
        temperature_difference = max(0.0, float(temperature_c) - float(ambient_c))
        return -self.cooling_coefficient_w_per_c * level * temperature_difference
