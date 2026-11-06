"""Small analytics helpers using Python collections and functional tools."""

from collections import Counter, defaultdict, deque
from functools import reduce


def summarize_cells(cell_records):
    """Summarize a collection of cell dictionaries.

    Demonstrates map, filter, reduce, lambda, Counter, defaultdict and deque.
    """
    records = list(cell_records)
    if not records:
        return {
            "average_c": 0.0,
            "minimum_c": 0.0,
            "maximum_c": 0.0,
            "status_counts": Counter(),
            "hot_cells": [],
            "status_groups": {},
            "recent_temperatures": (),
        }

    temperatures = list(map(lambda item: float(item["temperature_c"]), records))
    total = reduce(lambda running_total, value: running_total + value, temperatures, 0.0)
    hot_cells = list(filter(lambda item: float(item["temperature_c"]) >= 45.0, records))
    status_counts = Counter(map(lambda item: item["status"], records))

    grouped = defaultdict(list)
    for item in records:
        grouped[item["status"]].append(item["cell_id"])

    recent = deque(temperatures, maxlen=5)
    return {
        "average_c": round(total / len(temperatures), 2),
        "minimum_c": round(min(temperatures), 2),
        "maximum_c": round(max(temperatures), 2),
        "status_counts": status_counts,
        "hot_cells": hot_cells,
        "status_groups": dict(grouped),
        "recent_temperatures": tuple(recent),
    }
