"""Background simulation worker; communicates with Tkinter using a Queue."""

import queue
import threading


class SimulationWorker:
    def __init__(self, battery_pack, interval_seconds=0.5):
        self.battery_pack = battery_pack
        self.interval_seconds = float(interval_seconds)
        self.output_queue = queue.Queue(maxsize=2)
        self._conditions = {"current_a": 60.0, "cooling_level": 1, "ambient_c": 25.0}
        self._conditions_lock = threading.Lock()
        self._simulation_lock = threading.Lock()
        self._running = threading.Event()
        self._shutdown = threading.Event()
        self._thread = threading.Thread(target=self._run, name="ThermoLabSimulation", daemon=True)
        self._thread.start()

    def set_conditions(self, current_a, cooling_level, ambient_c):
        with self._conditions_lock:
            self._conditions = {
                "current_a": float(current_a),
                "cooling_level": int(cooling_level),
                "ambient_c": float(ambient_c),
            }

    def start(self):
        self._running.set()

    def pause(self):
        self._running.clear()

    def reset_pack(self, temperature_c=25.0):
        """Reset the model safely while the worker is paused."""
        self.pause()
        with self._simulation_lock:
            self.battery_pack.reset(temperature_c)

    @property
    def is_running(self):
        return self._running.is_set()

    def _publish_latest(self, snapshot):
        try:
            self.output_queue.put_nowait(snapshot)
        except queue.Full:
            try:
                self.output_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self.output_queue.put_nowait(snapshot)
            except queue.Full:
                pass

    def _run(self):
        while not self._shutdown.is_set():
            if not self._running.wait(timeout=0.1):
                continue
            if self._shutdown.is_set():
                break
            with self._conditions_lock:
                conditions = dict(self._conditions)
            try:
                # Simulation time advances twice as fast as wall-clock time.
                with self._simulation_lock:
                    if not self._running.is_set():
                        continue
                    snapshot = self.battery_pack.step(**conditions, dt_seconds=1.0)
                self._publish_latest(snapshot)
            except Exception as exc:  # surfaced to the GUI instead of killing the worker
                self._publish_latest({"worker_error": str(exc)})
                self._running.clear()
            self._shutdown.wait(self.interval_seconds)

    def close(self):
        self._shutdown.set()
        self._running.set()
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)
