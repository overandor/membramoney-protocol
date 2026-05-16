"""
Prometheus-style metrics for Membra Money Protocol backend.
Devnet-only in-memory implementation. Production would use prometheus_client.
"""

import time
from collections import defaultdict
from typing import Dict, Any


class MetricsCollector:
    """Simple in-memory metrics collector for devnet."""

    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, list] = defaultdict(list)
        self._start_times: Dict[str, float] = {}

    def inc(self, name: str, value: int = 1, labels: Dict[str, str] = None):
        """Increment a counter."""
        key = self._key(name, labels)
        self._counters[key] += value

    def dec(self, name: str, value: int = 1, labels: Dict[str, str] = None):
        """Decrement a counter."""
        key = self._key(name, labels)
        self._counters[key] -= value

    def gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge value."""
        key = self._key(name, labels)
        self._gauges[key] = value

    def observe(self, name: str, value: float, labels: Dict[str, str] = None):
        """Observe a histogram value."""
        key = self._key(name, labels)
        self._histograms[key].append(value)

    def timer(self, name: str, labels: Dict[str, str] = None):
        """Context manager for timing operations."""
        return _MetricsTimer(self, name, labels)

    def start_timer(self, name: str, labels: Dict[str, str] = None):
        """Start a timer."""
        key = self._key(name, labels)
        self._start_times[key] = time.time()

    def stop_timer(self, name: str, labels: Dict[str, str] = None) -> float:
        """Stop a timer and return duration in seconds."""
        key = self._key(name, labels)
        start = self._start_times.pop(key, None)
        if start is None:
            return 0.0
        duration = time.time() - start
        self.observe(f"{name}_duration_seconds", duration, labels)
        return duration

    def _key(self, name: str, labels: Dict[str, str] = None) -> str:
        if labels:
            label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name

    def render(self) -> str:
        """Render metrics in Prometheus text format."""
        lines = []
        lines.append("# Membra Money Protocol Metrics")
        lines.append(f"# Generated at {time.time()}")
        lines.append("")

        # Counters
        for key, value in sorted(self._counters.items()):
            lines.append(f"{key} {value}")

        lines.append("")

        # Gauges
        for key, value in sorted(self._gauges.items()):
            lines.append(f"{key} {value}")

        lines.append("")

        # Histograms (render as sum and count)
        for key, values in sorted(self._histograms.items()):
            if values:
                lines.append(f"{key}_sum {sum(values)}")
                lines.append(f"{key}_count {len(values)}")
                lines.append(f"{key}_avg {sum(values) / len(values):.6f}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Export metrics as a dictionary."""
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                k: {"count": len(v), "sum": sum(v), "avg": sum(v) / len(v) if v else 0}
                for k, v in self._histograms.items()
            },
        }


class _MetricsTimer:
    def __init__(self, collector: MetricsCollector, name: str, labels: Dict[str, str] = None):
        self.collector = collector
        self.name = name
        self.labels = labels

    def __enter__(self):
        self.collector.start_timer(self.name, self.labels)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.collector.stop_timer(self.name, self.labels)
        return False


# Global metrics instance
metrics = MetricsCollector()
