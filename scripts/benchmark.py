#!/usr/bin/env python3
"""Performance benchmarking suite for Membra Money Protocol backend."""

import time
import statistics
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from core.metrics import MetricsCollector


class BenchmarkRunner:
    def __init__(self):
        self.results = []
        self.metrics = MetricsCollector()

    def run(self, name: str, fn, iterations: int = 100):
        """Run a benchmark and collect stats."""
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            fn()
            elapsed = time.perf_counter() - start
            times.append(elapsed)

        stats = {
            "name": name,
            "iterations": iterations,
            "mean_ms": statistics.mean(times) * 1000,
            "median_ms": statistics.median(times) * 1000,
            "min_ms": min(times) * 1000,
            "max_ms": max(times) * 1000,
            "p95_ms": sorted(times)[int(iterations * 0.95)] * 1000,
        }
        self.results.append(stats)
        return stats

    def report(self):
        print("\n" + "=" * 60)
        print("BENCHMARK RESULTS")
        print("=" * 60)
        for r in self.results:
            print(f"\n{r['name']}")
            print(f"  iterations: {r['iterations']}")
            print(f"  mean:   {r['mean_ms']:.3f} ms")
            print(f"  median: {r['median_ms']:.3f} ms")
            print(f"  min:    {r['min_ms']:.3f} ms")
            print(f"  max:    {r['max_ms']:.3f} ms")
            print(f"  p95:    {r['p95_ms']:.3f} ms")


def benchmark_hash_operations():
    import hashlib
    def _hash():
        hashlib.sha256(b"test" * 100).hexdigest()
    return _hash


def benchmark_pin_sanitize():
    import re
    def _sanitize():
        re.sub(r"[^\x20-\x7E]", "", "test123!")
    return _sanitize


def main():
    runner = BenchmarkRunner()
    runner.run("sha256_hash", benchmark_hash_operations(), 1000)
    runner.run("pin_sanitize", benchmark_pin_sanitize(), 10000)
    runner.report()


if __name__ == "__main__":
    main()
