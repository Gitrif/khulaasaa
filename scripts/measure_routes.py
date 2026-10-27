"""
Route Response Time Diagnostic Script.
Measures latency distribution across key endpoints:
- Configurable warm-ups and sample repetitions
- Reports HTTP status code, failure count, response bytes
- Measures min, median (p50), p95, and max latency per route
Strictly under 500 lines. Zero emojis.
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from main import app

ROUTES = [
    "/",
    "/bids",
    "/jobs",
    "/rentals",
    "/obituaries",
    "/about",
    "/jobs/cv",
    "/rentals/contract",
    "/api/auth/me",
    "/static/css/style.css",
    "/static/js/app_shell.js",
    "/static/js/app.js",
]


def percentile(data: list[float], pct: float) -> float:
    """Calculate percentile from sorted list."""
    if not data:
        return 0.0
    k = (len(data) - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return data[int(k)]
    d0 = data[int(f)] * (c - k)
    d1 = data[int(c)] * (k - f)
    return d0 + d1


def measure_routes(warmups: int = 3, samples: int = 15) -> None:
    client = TestClient(app)

    print("=" * 95)
    print(f"KHULAASAA ROUTE PERFORMANCE BENCHMARK (Warmups: {warmups}, Samples: {samples})")
    print("=" * 95)
    header = f"{'Route':<25} | {'Status':<6} | {'Fail':<4} | {'Min (ms)':<8} | {'p50 (ms)':<8} | {'p95 (ms)':<8} | {'Max (ms)':<8} | {'Size':<8}"
    print(header)
    print("-" * 95)

    for route in ROUTES:
        # Warm-ups
        for _ in range(warmups):
            try:
                client.get(route)
            except Exception:
                pass

        # Measurement samples
        latencies: list[float] = []
        status_code = 0
        failures = 0
        resp_size = 0

        for _ in range(samples):
            t0 = time.perf_counter()
            try:
                resp = client.get(route)
                dur = (time.perf_counter() - t0) * 1000.0
                status_code = resp.status_code
                resp_size = len(resp.content)
                if status_code >= 400:
                    failures += 1
                latencies.append(dur)
            except Exception:
                dur = (time.perf_counter() - t0) * 1000.0
                failures += 1
                latencies.append(dur)

        latencies.sort()
        min_lat = latencies[0] if latencies else 0.0
        p50_lat = percentile(latencies, 50)
        p95_lat = percentile(latencies, 95)
        max_lat = latencies[-1] if latencies else 0.0

        size_str = f"{resp_size/1024:.1f} KB" if resp_size >= 1024 else f"{resp_size} B"
        print(f"{route:<25} | {status_code:<6} | {failures:<4} | {min_lat:<8.2f} | {p50_lat:<8.2f} | {p95_lat:<8.2f} | {max_lat:<8.2f} | {size_str:<8}")

    print("=" * 95)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark route latency.")
    parser.add_argument("--warmups", type=int, default=3, help="Number of warm-up requests")
    parser.add_argument("--samples", type=int, default=15, help="Number of measured sample requests")
    args = parser.parse_args()
    measure_routes(warmups=args.warmups, samples=args.samples)
