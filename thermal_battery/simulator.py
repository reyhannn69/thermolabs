"""Battery pack simulation and thermal calculations."""

from datetime import datetime
import random

from .exceptions import InvalidConditionError
from .models import BatteryCell, CoolingUnit


class BatteryPack:
    """A collection of battery cells and a cooling unit."""

    def __init__(self, cell_count=12, initial_temperature_c=25.0, seed=7):
        if not isinstance(cell_count, int) or cell_count < 1:
            raise ValueError("cell_count must be a positive integer")
        rng = random.Random(seed)
        self.cells = [
            BatteryCell(
                cell_id=f"C{i + 1:02d}",
                initial_temperature_c=initial_temperature_c + rng.uniform(-0.35, 0.35),
                resistance_ohm=0.0115 + rng.uniform(0.0, 0.0015),
                thermal_capacity_j_per_c=460.0 + rng.uniform(-18.0, 18.0),
            )
            for i in range(cell_count)
        ]
        self.cooling_unit = CoolingUnit()
        self.elapsed_seconds = 0.0

    def step(self, current_a, cooling_level, ambient_c, dt_seconds=1.0):
        """Advance the simulation and return a serializable snapshot."""
        current_a = float(current_a)
        ambient_c = float(ambient_c)
        cooling_level = int(cooling_level)
        dt_seconds = float(dt_seconds)
        if not 0.0 <= current_a <= 120.0:
            raise InvalidConditionError("Current must be between 0 and 120 A")
        if not 0 <= cooling_level <= 3:
            raise InvalidConditionError("Cooling level must be between 0 and 3")
        if not -10.0 <= ambient_c <= 50.0:
            raise InvalidConditionError("Ambient temperature must be between -10 and 50 °C")
        if not 0.0 < dt_seconds <= 10.0:
            raise InvalidConditionError("Time step must be greater than 0 and at most 10 seconds")

        for cell in self.cells:
            heat_generated = cell.thermal_power_w(current_a, cell.temperature_c, ambient_c, cooling_level)
            heat_removed = self.cooling_unit.thermal_power_w(
                current_a, cell.temperature_c, ambient_c, cooling_level
            )
            cell.update_temperature(heat_generated + heat_removed, dt_seconds)

        self.elapsed_seconds += dt_seconds
        return self.snapshot(current_a, cooling_level, ambient_c)

    def snapshot(self, current_a=0.0, cooling_level=0, ambient_c=25.0):
        records = [cell.to_record() for cell in self.cells]
        temperatures = [record["temperature_c"] for record in records]
        average = sum(temperatures) / len(temperatures)
        hottest = max(self.cells, key=lambda cell: cell.temperature_c)
        return {
            "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "elapsed_seconds": round(self.elapsed_seconds, 1),
            "current_a": float(current_a),
            "cooling_level": int(cooling_level),
            "ambient_c": float(ambient_c),
            "cells": records,
            "average_c": round(average, 2),
            "maximum_c": round(max(temperatures), 2),
            "minimum_c": round(min(temperatures), 2),
            "hottest_cell": hottest.cell_id,
            "warning_count": sum(1 for cell in self.cells if cell.status == "WARNING"),
            "critical_count": sum(1 for cell in self.cells if cell.status == "CRITICAL"),
        }

    def reset(self, temperature_c=25.0):
        for cell in self.cells:
            cell.reset(temperature_c)
        self.elapsed_seconds = 0.0
