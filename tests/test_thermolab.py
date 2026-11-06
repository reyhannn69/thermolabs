"""Automated tests for ThermoLab's simulation, analytics and persistence."""

import tempfile
import unittest
from pathlib import Path

from thermal_battery.analytics import summarize_cells
from thermal_battery.database import BatteryDatabase
from thermal_battery.exceptions import InvalidConditionError
from thermal_battery.models import BatteryCell, CoolingUnit, ThermalComponent
from thermal_battery.simulator import BatteryPack


class ThermalModelTests(unittest.TestCase):
    def test_battery_cell_and_cooling_unit_are_thermal_components(self):
        cell = BatteryCell("T01")
        cooler = CoolingUnit()
        self.assertIsInstance(cell, ThermalComponent)
        self.assertIsInstance(cooler, ThermalComponent)
        self.assertGreater(cell.thermal_power_w(10, 25, 25, 0), 0)
        self.assertLess(cooler.thermal_power_w(10, 40, 25, 2), 0)

    def test_current_generates_heat(self):
        pack = BatteryPack(cell_count=4, initial_temperature_c=25.0)
        before = pack.snapshot()["average_c"]
        after = pack.step(current_a=90, cooling_level=0, ambient_c=25)["average_c"]
        self.assertGreater(after, before)

    def test_cooling_reduces_temperature_rise(self):
        no_cooling = BatteryPack(cell_count=4, initial_temperature_c=40.0)
        with_cooling = BatteryPack(cell_count=4, initial_temperature_c=40.0)
        no_cooling.step(current_a=0, cooling_level=0, ambient_c=25)
        with_cooling.step(current_a=0, cooling_level=3, ambient_c=25)
        self.assertLess(with_cooling.snapshot()["average_c"], no_cooling.snapshot()["average_c"])

    def test_invalid_conditions_are_rejected(self):
        pack = BatteryPack()
        with self.assertRaises(InvalidConditionError):
            pack.step(current_a=140, cooling_level=1, ambient_c=25)
        with self.assertRaises(InvalidConditionError):
            pack.step(current_a=30, cooling_level=5, ambient_c=25)

    def test_warning_and_critical_status_thresholds(self):
        cell = BatteryCell("T02", initial_temperature_c=46)
        self.assertEqual(cell.status, "WARNING")
        cell.temperature_c = 55
        self.assertEqual(cell.status, "CRITICAL")


class AnalyticsTests(unittest.TestCase):
    def test_summary_uses_cell_records(self):
        records = [
            {"cell_id": "C01", "temperature_c": 30.0, "status": "NORMAL"},
            {"cell_id": "C02", "temperature_c": 48.0, "status": "WARNING"},
            {"cell_id": "C03", "temperature_c": 57.0, "status": "CRITICAL"},
        ]
        result = summarize_cells(records)
        self.assertEqual(result["average_c"], 45.0)
        self.assertEqual(result["maximum_c"], 57.0)
        self.assertEqual(len(result["hot_cells"]), 2)
        self.assertEqual(result["status_counts"]["NORMAL"], 1)


class DatabaseTests(unittest.TestCase):
    def test_snapshot_is_saved_and_read_back(self):
        with tempfile.TemporaryDirectory() as folder:
            database = BatteryDatabase(Path(folder) / "test.db")
            snapshot = BatteryPack(cell_count=3).snapshot(current_a=25, cooling_level=2, ambient_c=24)
            self.assertEqual(database.save_snapshot(snapshot), 3)
            self.assertEqual(database.reading_count(), 3)
            rows = database.recent_readings(2)
            self.assertEqual(len(rows), 2)
            self.assertIn("temperature_c", rows[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
