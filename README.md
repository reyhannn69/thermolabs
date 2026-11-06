# ThermoLab — Thermal Battery Monitoring & Cooling Simulator

A small educational Python desktop project that simulates temperature changes in a 12-cell battery pack. It provides a Tkinter dashboard, adjustable load current and micro-channel cooling level, cell-level status indicators, SQLite history, and a background simulation thread.

> **Important:** This is a simplified educational simulation. It is not a real battery-management system, does not model electrochemistry or micro-channel fluid dynamics, and must not be used to make real battery safety or engineering decisions.

## Run it

Requirements: Python 3.10 or newer with Tkinter enabled. No third-party Python packages are required.

**Windows:** extract the folder and double-click `run_windows.bat`, or run:

```bash
python main.py
```

**Linux:** install your distribution's Tkinter package if it is not already installed, then run:

```bash
./run_linux.sh
```

The database is created automatically at `data/thermal_battery.db`.

## Use the application

1. Adjust **Load current** (0–120 A), **Cooling level** (0–3), and **Ambient temperature** (-10–50 °C).
2. Press **Start simulation**. The 12 battery cells change temperature as the model calculates resistive heating and cooling.
3. Select a cell in the Canvas diagram to inspect its temperature and status.
4. Press **Pause** to freeze the model, **Reset temperatures** to reset all cells to ambient, or **Save snapshot to SQLite** to save the current reading.
5. **View recent history** shows readings stored in SQLite. While running, the program also saves a snapshot automatically every five seconds.
6. Press **Draw geometric shapes** to open the Experiment 7 Canvas drawing pad. Choose Rectangle, Oval or Line, then click and drag to draw.

Temperature bands used by this demo:

- NORMAL: below 45 °C
- WARNING: 45 °C to below 55 °C
- CRITICAL: 55 °C and above

The model uses Joule heating (`P = I²R`) and a simplified micro-channel coolant heat-removal term proportional to temperature difference and cooling level. The simulation advances approximately twice as fast as wall-clock time.

## How the project covers the Python practical experiments

| Experiment | Concept | Where it appears |
|---|---|---|
| 1 | Classes, objects, constructors | `BatteryCell`, `CoolingUnit`, `BatteryPack`, `BatteryDatabase`, `ThermalBatteryApp` |
| 2 | Constructors and lists | Battery pack constructor creates a list of 12 cell objects; cell records are held in lists |
| 3 | String handling and inheritance | Component names and cell IDs; `BatteryCell` and `CoolingUnit` inherit from `ThermalComponent` |
| 4 | Abstract class and method overriding | `ThermalComponent` declares abstract `thermal_power_w`; both concrete component classes override it |
| 5 | Exception handling, modules and multithreading | `exceptions.py`; separate Python modules; `SimulationWorker` uses `threading`, `Event`, `Lock` and `Queue` |
| 6 | Collections and functional programming | `Counter`, `defaultdict`, `deque`, `map`, `filter`, `reduce` and `lambda` in `analytics.py` |
| 7 | Tkinter Canvas geometric shapes | `geometry_pad.py` lets users draw rectangles, ovals and lines by dragging; the battery diagram also uses Canvas geometry |
| 8 | SQLite with Python | `database.py` creates the readings table and saves/queries cell temperatures |

## Project structure

```text
ThermoLab/
├── main.py
├── run_windows.bat
├── run_linux.sh
├── README.md
├── thermal_battery/
│   ├── __init__.py
│   ├── analytics.py
│   ├── database.py
│   ├── exceptions.py
│   ├── gui.py
│   ├── geometry_pad.py
│   ├── models.py
│   ├── simulator.py
│   └── worker.py
├── tests/
│   └── test_thermolab.py
└── data/
    └── thermal_battery.db  (created automatically)
```

## Run tests

```bash
python -m unittest discover -s tests -v
```

The tests cover heating/cooling behaviour, validation, status thresholds, analytics, and SQLite persistence.
