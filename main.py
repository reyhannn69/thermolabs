"""Launch the ThermoLab desktop application."""

from pathlib import Path
import tkinter as tk
from tkinter import messagebox

from thermal_battery.exceptions import DatabaseError
from thermal_battery.gui import ThermalBatteryApp


def main():
    project_dir = Path(__file__).resolve().parent
    database_path = project_dir / "data" / "thermal_battery.db"
    root = tk.Tk()
    try:
        ThermalBatteryApp(root, database_path)
    except DatabaseError as exc:
        messagebox.showerror("ThermoLab startup error", str(exc), parent=root)
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
