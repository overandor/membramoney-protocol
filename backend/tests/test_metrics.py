"""
Tests for metrics collector.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.metrics import MetricsCollector


def test_counter_increment():
    m = MetricsCollector()
    m.inc("requests", 5)
    assert m.to_dict()["counters"]["requests"] == 5


def test_counter_decrement():
    m = MetricsCollector()
    m.inc("requests", 10)
    m.dec("requests", 3)
    assert m.to_dict()["counters"]["requests"] == 7


def test_gauge_set():
    m = MetricsCollector()
    m.gauge("memory_mb", 256.5)
    assert m.to_dict()["gauges"]["memory_mb"] == 256.5


def test_histogram_observe():
    m = MetricsCollector()
    m.observe("latency", 0.1)
    m.observe("latency", 0.2)
    data = m.to_dict()["histograms"]["latency"]
    assert data["count"] == 2
    assert round(data["sum"], 3) == 0.3


def test_timer_context():
    m = MetricsCollector()
    import time
    with m.timer("operation"):
        time.sleep(0.01)
    data = m.to_dict()["histograms"]["operation_duration_seconds"]
    assert data["count"] == 1
    assert data["sum"] > 0


def test_render_prometheus_format():
    m = MetricsCollector()
    m.inc("requests", 1)
    output = m.render()
    assert "requests" in output
    assert "1" in output
