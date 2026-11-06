"""SQLite persistence for battery temperature readings."""

import sqlite3
from pathlib import Path

from .exceptions import DatabaseError


class BatteryDatabase:
    def __init__(self, database_path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(str(self.database_path), timeout=5.0)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        try:
            with self._connect() as connection:
                connection.execute(
                    """CREATE TABLE IF NOT EXISTS readings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        recorded_at TEXT NOT NULL,
                        cell_id TEXT NOT NULL,
                        temperature_c REAL NOT NULL,
                        current_a REAL NOT NULL,
                        cooling_level INTEGER NOT NULL,
                        ambient_c REAL NOT NULL,
                        status TEXT NOT NULL
                    )"""
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_readings_time ON readings(recorded_at)"
                )
        except sqlite3.Error as exc:
            raise DatabaseError(f"Could not initialize database: {exc}") from exc

    def save_snapshot(self, snapshot):
        """Save all cell readings from one simulation snapshot in one transaction."""
        try:
            rows = [
                (
                    snapshot["recorded_at"], cell["cell_id"], cell["temperature_c"],
                    snapshot["current_a"], snapshot["cooling_level"],
                    snapshot["ambient_c"], cell["status"],
                )
                for cell in snapshot["cells"]
            ]
            with self._connect() as connection:
                connection.executemany(
                    """INSERT INTO readings
                    (recorded_at, cell_id, temperature_c, current_a,
                     cooling_level, ambient_c, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    rows,
                )
            return len(rows)
        except (sqlite3.Error, KeyError, TypeError) as exc:
            raise DatabaseError(f"Could not save readings: {exc}") from exc

    def recent_readings(self, limit=24):
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    """SELECT recorded_at, cell_id, temperature_c, current_a,
                       cooling_level, ambient_c, status
                       FROM readings ORDER BY id DESC LIMIT ?""",
                    (max(1, min(int(limit), 500)),),
                ).fetchall()
            return [dict(row) for row in rows]
        except (sqlite3.Error, ValueError) as exc:
            raise DatabaseError(f"Could not read history: {exc}") from exc

    def reading_count(self):
        try:
            with self._connect() as connection:
                row = connection.execute("SELECT COUNT(*) AS total FROM readings").fetchone()
            return int(row["total"])
        except sqlite3.Error as exc:
            raise DatabaseError(f"Could not count readings: {exc}") from exc
