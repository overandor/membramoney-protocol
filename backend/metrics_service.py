"""Metrics Service — Prometheus-style metrics for all production services."""
from typing import Dict, Any, List

class MetricsService:
    """Counter, gauge, histogram metrics."""

    def __init__(self):
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, Dict[str, Any]] = {}

    def inc(self, name: str, value: int = 1) -> None:
        self._counters[name] = self._counters.get(name, 0) + value

    def gauge(self, name: str, value: float) -> None:
        self._gauges[name] = value

    def observe(self, name: str, value: float, buckets: List[float] = None) -> None:
        if name not in self._histograms:
            self._histograms[name] = {"count": 0, "sum": 0.0, "buckets": {}}
        h = self._histograms[name]
        h["count"] += 1
        h["sum"] += value
        buckets = buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
        for b in buckets:
            if value <= b:
                h["buckets"][b] = h["buckets"].get(b, 0) + 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {k: dict(v) for k, v in self._histograms.items()},
        }

    def to_prometheus(self) -> str:
        lines = []
        for name, value in self._counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        for name, value in self._gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        for name, h in self._histograms.items():
            lines.append(f"# TYPE {name} histogram")
            for b, count in h["buckets"].items():
                lines.append(f{name}_bucket{{le={b}}}
{count})
            lines.append(f"{name}_count {h[count]}")
            lines.append(f"{name}_sum {h[sum]}")
        return "\n".join(lines)
