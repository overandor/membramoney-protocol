#!/usr/bin/env python3
"""
Load testing script for Membra Money Protocol backend.
Usage: python scripts/load_test.py [--concurrency 10] [--duration 60]
"""

import argparse
import asyncio
import time
import statistics
from typing import List

import aiohttp


BASE_URL = "http://localhost:8000"


async def make_request(session: aiohttp.ClientSession, endpoint: str) -> dict:
    """Make a single request and return timing data."""
    start = time.time()
    try:
        async with session.get(f"{BASE_URL}{endpoint}") as resp:
            await resp.text()
            return {
                "endpoint": endpoint,
                "status": resp.status,
                "duration": time.time() - start,
                "error": None,
            }
    except Exception as e:
        return {
            "endpoint": endpoint,
            "status": 0,
            "duration": time.time() - start,
            "error": str(e),
        }


async def run_load_test(concurrency: int, duration: int) -> List[dict]:
    """Run load test with given concurrency and duration."""
    endpoints = ["/health", "/ready", "/api/v1/risk-disclosure", "/api/v1/reserves", "/api/v1/stats"]
    results = []
    start_time = time.time()

    async with aiohttp.ClientSession() as session:
        tasks = []
        while time.time() - start_time < duration:
            for _ in range(concurrency):
                endpoint = endpoints[len(tasks) % len(endpoints)]
                task = asyncio.create_task(make_request(session, endpoint))
                tasks.append(task)

                if len(tasks) >= concurrency * 10:
                    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                    for t in done:
                        results.append(t.result())
                    tasks = list(pending)

            # Small delay to prevent overwhelming
            await asyncio.sleep(0.01)

        # Wait for remaining tasks
        if tasks:
            remaining = await asyncio.gather(*tasks, return_exceptions=True)
            for r in remaining:
                if isinstance(r, dict):
                    results.append(r)

    return results


def print_results(results: List[dict], duration: int):
    """Print load test results."""
    total = len(results)
    errors = [r for r in results if r["error"]]
    successes = [r for r in results if not r["error"]]
    durations = [r["duration"] for r in successes]

    print("=" * 60)
    print("Membra Money Protocol — Load Test Results")
    print("=" * 60)
    print(f"Duration: {duration}s")
    print(f"Total requests: {total}")
    print(f"Successful: {len(successes)}")
    print(f"Failed: {len(errors)}")
    print(f"Throughput: {total / duration:.1f} req/s")

    if durations:
        print(f"\nLatency (seconds):")
        print(f"  Min: {min(durations):.4f}")
        print(f"  Max: {max(durations):.4f}")
        print(f"  Mean: {statistics.mean(durations):.4f}")
        print(f"  Median: {statistics.median(durations):.4f}")
        if len(durations) > 1:
            print(f"  Stdev: {statistics.stdev(durations):.4f}")

    # Status code breakdown
    status_codes = {}
    for r in results:
        status_codes[r["status"]] = status_codes.get(r["status"], 0) + 1
    print(f"\nStatus codes:")
    for status, count in sorted(status_codes.items()):
        print(f"  {status}: {count}")

    if errors:
        print(f"\nErrors (first 5):")
        for r in errors[:5]:
            print(f"  {r['endpoint']}: {r['error']}")

    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load test Membra Money backend")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent requests")
    parser.add_argument("--duration", type=int, default=30, help="Test duration in seconds")
    args = parser.parse_args()

    print(f"Starting load test: {args.concurrency} concurrent, {args.duration}s duration...")
    results = asyncio.run(run_load_test(args.concurrency, args.duration))
    print_results(results, args.duration)
