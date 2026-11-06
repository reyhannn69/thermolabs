"""Tkinter dashboard for the thermal battery monitor."""

import queue
import tkinter as tk
from tkinter import messagebox, ttk
import time

from .analytics import summarize_cells
from .database import BatteryDatabase
from .exceptions import DatabaseError
from .geometry_pad import GeometryPad
from .simulator import BatteryPack
from .worker import SimulationWorker


class ThermalBatteryApp:
    BACKGROUND = "#101820"
    PANEL = "#1b2a35"
    TEXT = "#e8f0f4"
    MUTED = "#9db0bb"
    NORMAL = "#20a58a"
    WARNING = "#e6a23c"
    CRITICAL = "#e05252"

    def __init__(self, root, database_path):
        self.root = root
        self.root.title("ThermoLab | Battery Thermal Monitor")
        self.root.geometry("1040x760")
        self.root.minsize(900, 680)
        self.root.configure(bg=self.BACKGROUND)

        self.pack = BatteryPack(cell_count=12)
        self.worker = SimulationWorker(self.pack)
        self.database = BatteryDatabase(database_path)
        self.latest_snapshot = self.pack.snapshot()
        self.last_saved_at = 0.0
        self.selected_cell = None
        self._closing = False
        self._build_style()
        self._build_interface()
        self._draw_battery(self.latest_snapshot["cells"])
        self._refresh_stats(self.latest_snapshot)
        self._poll_worker()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _build_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=self.BACKGROUND)
        style.configure("Panel.TFrame", background=self.PANEL)
        style.configure("TLabel", background=self.BACKGROUND, foreground=self.TEXT, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=self.PANEL, foreground=self.TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=self.BACKGROUND, foreground=self.MUTED, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=self.BACKGROUND, foreground=self.TEXT,
                        font=("Segoe UI", 21, "bold"))
        style.configure("CardValue.TLabel", background=self.PANEL, foreground=self.TEXT,
                        font=("Segoe UI", 19, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=(10, 7))
        style.configure("TScale", background=self.PANEL)

    def _build_interface(self):
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="THERMOLAB", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="BATTERY THERMAL MONITOR & COOLING SIMULATOR",
                  style="Muted.TLabel").pack(side="left", padx=(14, 0), pady=(8, 0))

        cards = ttk.Frame(outer)
        cards.pack(fill="x", pady=(0, 12))
        self.stat_values = {}
        stat_definitions = [
            ("AVERAGE", "average", "-- °C"),
            ("MAXIMUM", "maximum", "-- °C"),
            ("HOTTEST CELL", "hottest", "--"),
            ("ALERTS", "alerts", "0"),
        ]
        for index, (caption, key, initial) in enumerate(stat_definitions):
            cards.columnconfigure(index, weight=1)
            card = tk.Frame(cards, bg=self.PANEL, padx=14, pady=11,
                            highlightthickness=1, highlightbackground="#2c414f")
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 7, 0))
            tk.Label(card, text=caption, bg=self.PANEL, fg=self.MUTED,
                     font=("Segoe UI", 8, "bold")).pack(anchor="w")
            value = tk.Label(card, text=initial, bg=self.PANEL, fg=self.TEXT,
                             font=("Segoe UI", 18, "bold"))
            value.pack(anchor="w", pady=(4, 0))
            self.stat_values[key] = value

        content = ttk.Frame(outer)
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        visual_panel = tk.Frame(content, bg=self.PANEL, padx=12, pady=12,
                                highlightthickness=1, highlightbackground="#2c414f")
        visual_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tk.Label(visual_panel, text="BATTERY PACK LAYOUT", bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(visual_panel, text="Select a cell to inspect its temperature and condition.",
                 bg=self.PANEL, fg=self.MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(3, 8))
        self.canvas = tk.Canvas(visual_panel, width=690, height=300, bg="#13232d",
                                highlightthickness=0, relief="flat")
        self.canvas.pack(fill="both", expand=True)
        self.cell_detail = tk.StringVar(value="Select a battery cell")
        tk.Label(visual_panel, textvariable=self.cell_detail, bg=self.PANEL, fg="#c9d8df",
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(9, 0))
        tk.Label(visual_panel,
                 text="Illustrative model only — not a real battery-management or safety system.",
                 bg=self.PANEL, fg="#d5a65b", font=("Segoe UI", 8)).pack(anchor="w", pady=(7, 0))

        controls = tk.Frame(content, bg=self.PANEL, padx=14, pady=12,
                            highlightthickness=1, highlightbackground="#2c414f")
        controls.grid(row=0, column=1, sticky="nsew")
        tk.Label(controls, text="SIMULATION CONTROLS", bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 13))

        self.run_button = ttk.Button(controls, text="▶  Start simulation", command=self.toggle_simulation)
        self.run_button.pack(fill="x", pady=(0, 7))
        ttk.Button(controls, text="↺  Reset temperatures", command=self.reset_simulation).pack(fill="x", pady=(0, 16))

        self.current_value = tk.DoubleVar(value=60.0)
        self.cooling_value = tk.IntVar(value=1)
        self.ambient_value = tk.DoubleVar(value=25.0)
        self._add_scale(controls, "Load current", self.current_value, 0, 120, "A", resolution=1)
        self._add_scale(controls, "Cooling level", self.cooling_value, 0, 3, "(0–3)", resolution=1)
        self._add_scale(controls, "Ambient temperature", self.ambient_value, -10, 50, "°C", resolution=1)

        ttk.Separator(controls).pack(fill="x", pady=12)
        ttk.Button(controls, text="Save snapshot to SQLite", command=self.save_snapshot).pack(fill="x", pady=4)
        ttk.Button(controls, text="View recent history", command=self.show_history).pack(fill="x", pady=4)
        ttk.Button(controls, text="Draw geometric shapes", command=self.open_geometry_pad).pack(fill="x", pady=4)
        self.db_count_label = tk.Label(controls, text="Saved cell readings: 0", bg=self.PANEL,
                                       fg=self.MUTED, font=("Segoe UI", 8))
        self.db_count_label.pack(anchor="w", pady=(10, 0))

        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(11, 0))
        self.status_text = tk.StringVar(value="Ready. Start the simulation to monitor the battery pack.")
        ttk.Label(footer, textvariable=self.status_text, style="Muted.TLabel").pack(side="left")
        self.clock_text = tk.StringVar(value="SIM TIME 00:00")
        ttk.Label(footer, textvariable=self.clock_text, style="Muted.TLabel").pack(side="right")
        self._update_database_count()

    def _add_scale(self, parent, caption, variable, minimum, maximum, unit, resolution=1):
        block = tk.Frame(parent, bg=self.PANEL)
        block.pack(fill="x", pady=(0, 11))
        title = tk.Frame(block, bg=self.PANEL)
        title.pack(fill="x")
        tk.Label(title, text=caption, bg=self.PANEL, fg=self.TEXT,
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        value_label = tk.Label(title, text=f"{variable.get():g} {unit}", bg=self.PANEL,
                               fg="#85c9dc", font=("Segoe UI", 9))
        value_label.pack(side="right")

        def changed(value):
            numeric = float(value)
            if isinstance(variable, tk.IntVar):
                variable.set(int(round(numeric)))
                shown = str(int(round(numeric)))
            else:
                variable.set(numeric)
                shown = f"{numeric:.0f}"
            value_label.configure(text=f"{shown} {unit}")
            self._send_conditions()

        scale = tk.Scale(block, from_=minimum, to=maximum, orient="horizontal", resolution=resolution,
                         variable=variable, command=changed, showvalue=False,
                         bg=self.PANEL, fg=self.TEXT, troughcolor="#344b59",
                         activebackground="#65b9ce", highlightthickness=0, bd=0,
                         sliderrelief="flat", length=190)
        scale.pack(fill="x", pady=(1, 0))

    def _send_conditions(self):
        self.worker.set_conditions(self.current_value.get(), self.cooling_value.get(), self.ambient_value.get())

    def toggle_simulation(self):
        if self.worker.is_running:
            self.worker.pause()
            self.run_button.configure(text="▶  Resume simulation")
            self.status_text.set("Simulation paused.")
        else:
            self._send_conditions()
            self.worker.start()
            self.run_button.configure(text="Ⅱ  Pause simulation")
            self.status_text.set("Simulation running — temperatures update in real time.")

    def reset_simulation(self):
        self.worker.pause()
        self.worker.reset_pack(self.ambient_value.get())
        self.latest_snapshot = self.pack.snapshot(
            self.current_value.get(), self.cooling_value.get(), self.ambient_value.get()
        )
        self._draw_battery(self.latest_snapshot["cells"])
        self._refresh_stats(self.latest_snapshot)
        self.run_button.configure(text="▶  Start simulation")
        self.status_text.set("Battery temperatures reset to ambient temperature.")
        self.clock_text.set("SIM TIME 00:00")

    def _temperature_color(self, temperature, status):
        if status == "CRITICAL":
            return self.CRITICAL
        if status == "WARNING":
            return self.WARNING
        return self.NORMAL

    def _draw_battery(self, cell_records):
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 690)
        self.canvas.create_text(18, 15, anchor="w", text="COOLANT INLET",
                                fill="#71bdd2", font=("Segoe UI", 8, "bold"))
        self.canvas.create_line(20, 34, width - 20, 34, fill="#4b9db2", width=4,
                                arrow="last", arrowshape=(8, 10, 4))
        self.canvas.create_text(18, 282, anchor="w", text="COOLANT RETURN",
                                fill="#71bdd2", font=("Segoe UI", 8, "bold"))
        self.canvas.create_line(20, 263, width - 20, 263, fill="#376b7c", width=4,
                                arrow="last", arrowshape=(8, 10, 4))

        for index, cell in enumerate(cell_records):
            row, column = divmod(index, 4)
            x = 34 + column * 163
            y = 57 + row * 67
            color = self._temperature_color(cell["temperature_c"], cell["status"])
            tag = f"cell_{cell['cell_id']}"
            self.canvas.create_line(x + 54, 34, x + 54, y, fill="#4b9db2", width=2)
            self.canvas.create_line(x + 54, y + 44, x + 54, 263, fill="#376b7c", width=2)
            self.canvas.create_rectangle(x, y, x + 108, y + 43, fill="#203743",
                                         outline=color, width=2, tags=(tag, "battery_cell"))
            self.canvas.create_rectangle(x + 7, y + 8, x + 15, y + 35, fill=color,
                                         outline="", tags=(tag, "battery_cell"))
            self.canvas.create_text(x + 60, y + 14, text=cell["cell_id"], fill=self.TEXT,
                                    font=("Segoe UI", 9, "bold"), tags=(tag, "battery_cell"))
            self.canvas.create_text(x + 60, y + 30, text=f"{cell['temperature_c']:.1f} °C",
                                    fill=color, font=("Segoe UI", 9, "bold"), tags=(tag, "battery_cell"))
            self.canvas.tag_bind(tag, "<Button-1>", lambda event, record=cell: self._select_cell(record))

        # Small circular indicators are also Canvas geometry (Experiment 7).
        self.canvas.create_oval(width - 85, 8, width - 73, 20, fill="#4b9db2", outline="")

    def _select_cell(self, cell):
        self.selected_cell = cell["cell_id"]
        self.cell_detail.set(
            f"{cell['cell_id']}  |  Temperature: {cell['temperature_c']:.2f} °C  |  Status: {cell['status']}"
        )

    def _refresh_stats(self, snapshot):
        self.stat_values["average"].configure(text=f"{snapshot['average_c']:.1f} °C")
        self.stat_values["maximum"].configure(text=f"{snapshot['maximum_c']:.1f} °C")
        self.stat_values["hottest"].configure(text=snapshot["hottest_cell"])
        alerts = snapshot["warning_count"] + snapshot["critical_count"]
        self.stat_values["alerts"].configure(
            text=str(alerts), fg=self.CRITICAL if snapshot["critical_count"] else
            (self.WARNING if alerts else self.NORMAL)
        )
        self.clock_text.set(f"SIM TIME {int(snapshot['elapsed_seconds'] // 60):02d}:"
                            f"{int(snapshot['elapsed_seconds'] % 60):02d}")
        analytics = summarize_cells(snapshot["cells"])
        if analytics["maximum_c"] >= 55:
            self.status_text.set("CRITICAL: at least one simulated cell exceeded 55 °C.")
        elif analytics["maximum_c"] >= 45:
            self.status_text.set("WARNING: a simulated cell is above 45 °C.")

    def _poll_worker(self):
        if self._closing:
            return
        latest = None
        while True:
            try:
                latest = self.worker.output_queue.get_nowait()
            except queue.Empty:
                break
        if latest:
            if "worker_error" in latest:
                self.status_text.set(f"Simulation stopped: {latest['worker_error']}")
                self.run_button.configure(text="▶  Start simulation")
            else:
                self.latest_snapshot = latest
                self._draw_battery(latest["cells"])
                self._refresh_stats(latest)
                if time.monotonic() - self.last_saved_at >= 5.0:
                    try:
                        self.database.save_snapshot(latest)
                        self.last_saved_at = time.monotonic()
                        self._update_database_count()
                    except DatabaseError as exc:
                        self.status_text.set(str(exc))
        self.root.after(200, self._poll_worker)

    def save_snapshot(self):
        try:
            saved = self.database.save_snapshot(self.latest_snapshot)
            self.last_saved_at = time.monotonic()
            self._update_database_count()
            self.status_text.set(f"Saved {saved} cell readings to SQLite.")
        except DatabaseError as exc:
            messagebox.showerror("Database error", str(exc), parent=self.root)

    def _update_database_count(self):
        try:
            count = self.database.reading_count()
            self.db_count_label.configure(text=f"Saved cell readings: {count}")
        except DatabaseError:
            self.db_count_label.configure(text="Saved cell readings: unavailable")

    def open_geometry_pad(self):
        GeometryPad(self.root)

    def show_history(self):
        try:
            rows = self.database.recent_readings(limit=36)
        except DatabaseError as exc:
            messagebox.showerror("Database error", str(exc), parent=self.root)
            return
        window = tk.Toplevel(self.root)
        window.title("Recent battery readings")
        window.geometry("760x430")
        window.configure(bg=self.BACKGROUND)
        tk.Label(window, text="RECENT CELL READINGS", bg=self.BACKGROUND, fg=self.TEXT,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=14, pady=12)
        text = tk.Text(window, bg="#13232d", fg=self.TEXT, insertbackground=self.TEXT,
                       font=("Consolas", 9), relief="flat", wrap="none")
        text.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        text.insert("end", "RECORDED AT                CELL    TEMP °C   CURRENT A   COOLING   STATUS\n")
        text.insert("end", "-" * 88 + "\n")
        for row in rows:
            text.insert("end", f"{row['recorded_at']:<27} {row['cell_id']:<7} "
                               f"{row['temperature_c']:>7.2f}   {row['current_a']:>8.1f}   "
                               f"{row['cooling_level']:>7}   {row['status']}\n")
        if not rows:
            text.insert("end", "No readings saved yet. Start the simulation or save a snapshot.\n")
        text.configure(state="disabled")

    def close(self):
        self._closing = True
        self.worker.close()
        self.root.destroy()
