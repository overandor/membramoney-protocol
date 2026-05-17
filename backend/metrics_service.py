"""Metrics Service — Prometheus-style metrics."""
from typing import Dict, Any, List

class MetricsService:
    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, Any] = {}

    def inc(self, name: str, value: int = 1) -> None:
        self._counters[name] = self._counters.get(name, 0) + value

    def gauge(self, name: str, value: float) -> None:
        self._gauges[name] = value

    def observe(self, name: str, value: float) -> None:
        if name not in self._histograms:
            self._histograms[name] = {"count": 0, "sum": 0.0, "buckets": {}}
        h = self._histograms[name]
        h["count"] += 1
        h["sum"] += value
        for b in [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]:
            if value <= b:
                key = str(b)
                h["buckets"][key] = h["buckets"].get(key, 0) + 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": dict(self._histograms),
        }
