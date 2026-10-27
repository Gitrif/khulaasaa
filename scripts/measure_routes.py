"""
Route Response Time Diagnostic Script.
Measures latency, database time, HTTP status, and response size for key routes.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

ROUTES = [
    "/",
    "/bids",
    "/jobs",
    "/rentals",
    "/obituaries",
    "/about",
    "/api/auth/me",
    "/static/css/style.css",
    "/static/js/app.js",
]

print(f"{'Route':<25} | {'Status':<6} | {'Time (ms)':<10} | {'Size (bytes)':<12}")
print("-" * 60)

for route in ROUTES:
    # Run once to warm up
    t0 = time.perf_counter()
    resp = client.get(route)
    t1 = time.perf_counter()
    dur_ms = (t1 - t0) * 1000.0
    print(f"{route:<25} | {resp.status_code:<6} | {dur_ms:<10.2f} | {len(resp.content):<12}")
