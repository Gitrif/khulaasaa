"""
Jobs Background Ingestion Lock, Concurrency, and Atomic Scheduling Tests.
Verifies that background jobs synchronization:
1. Atomically schedules at most one worker under high thread concurrency.
2. Gracefully cleans up pending state if worker thread startup fails.
3. Automatically recovers and allows subsequent syncs after a failed background sync.
4. Provides thread-safe operational status observability.
Strictly under 500 lines. Zero emojis.
"""
from __future__ import annotations

import concurrent.futures
import threading
import time
from unittest.mock import MagicMock, patch
import pytest

from services.jobs_service import (
    _LIVE_JOBS_LOCK,
    get_jobs_sync_status,
    run_jobs_sync,
    trigger_jobs_background_sync,
)
import services.jobs_service as js


def setup_function():
    """Ensure clean lock state before each test."""
    with _LIVE_JOBS_LOCK:
        js._LIVE_JOBS_IS_SYNCING = False
        js._LIVE_JOBS_LAST_SYNC = 0.0


def teardown_function():
    """Reset lock state after each test."""
    with _LIVE_JOBS_LOCK:
        js._LIVE_JOBS_IS_SYNCING = False
        js._LIVE_JOBS_LAST_SYNC = 0.0


def test_run_jobs_sync_success_resets_lock():
    """Verify run_jobs_sync executes and releases the sync lock upon completion."""
    mock_result = {"fetched": 5, "new": 2, "updated": 1, "alerts_sent": 0}
    with patch("services.ingestion.jobs_ingestion.sync_jobs", return_value=mock_result):
        res = run_jobs_sync(pages=1, trigger_alerts=False)

    assert res == mock_result
    assert js._LIVE_JOBS_IS_SYNCING is False
    assert js._LIVE_JOBS_LAST_SYNC > 0
    status = get_jobs_sync_status()
    assert status["status"] == "success"
    assert status["fetched"] == 5
    assert status["new"] == 2


def test_run_jobs_sync_exception_safely_releases_lock():
    """Verify that an unhandled exception inside scrapers safely releases the sync lock in finally."""
    with patch("services.ingestion.jobs_ingestion.sync_jobs", side_effect=RuntimeError("Gazette portal down")):
        res = run_jobs_sync(pages=1, trigger_alerts=False)

    assert res.get("status") == "failed"
    assert "Gazette portal down" in res.get("error", "")
    assert js._LIVE_JOBS_IS_SYNCING is False
    status = get_jobs_sync_status()
    assert status["status"] == "failed"
    assert "Gazette portal down" in status["last_error"]


def test_concurrent_triggers_atomically_schedule_only_one_worker():
    """
    Launch 10 concurrent threads simultaneously requesting background sync.
    Proves that atomic reservation guarantees EXACTLY one caller schedules the worker.
    """
    barrier = threading.Barrier(10)
    results: list[bool] = []
    lock = threading.Lock()

    def worker_attempt():
        barrier.wait()  # Synchronize all threads to fire simultaneously
        triggered = trigger_jobs_background_sync(force=True, pages=1)
        with lock:
            results.append(triggered)

    # Use a mock that holds execution for a short period
    def slow_mock(conn, pages=1, trigger_alerts=True):
        time.sleep(0.1)
        return {"fetched": 2, "new": 1, "updated": 0, "alerts_sent": 0}

    with patch("services.ingestion.jobs_ingestion.sync_jobs", side_effect=slow_mock):
        threads = [threading.Thread(target=worker_attempt) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    # Exactly one thread must have succeeded in scheduling
    true_count = sum(1 for r in results if r is True)
    false_count = sum(1 for r in results if r is False)
    assert true_count == 1, f"Expected exactly 1 trigger, got {true_count}"
    assert false_count == 9

    # Wait for the single scheduled worker to conclude
    deadline = time.time() + 3.0
    while time.time() < deadline and js._LIVE_JOBS_IS_SYNCING:
        time.sleep(0.02)
    assert js._LIVE_JOBS_IS_SYNCING is False


def test_worker_start_failure_cleans_up_state():
    """Verify that if worker thread fails to start, the pending state is cleaned up immediately."""
    with patch("threading.Thread.start", side_effect=RuntimeError("Cannot allocate thread resources")):
        triggered = trigger_jobs_background_sync(force=True, pages=1)
        assert triggered is False
        assert js._LIVE_JOBS_IS_SYNCING is False

    # A subsequent trigger without the error must succeed immediately
    with patch("services.ingestion.jobs_ingestion.sync_jobs", return_value={"fetched": 1, "new": 0, "updated": 0, "alerts_sent": 0}):
        subsequent = trigger_jobs_background_sync(force=True, pages=1)
        assert subsequent is True

        deadline = time.time() + 3.0
        while time.time() < deadline and js._LIVE_JOBS_IS_SYNCING:
            time.sleep(0.02)
        assert js._LIVE_JOBS_IS_SYNCING is False


def test_subsequent_sync_runs_after_failed_background_sync():
    """Verify that after a background worker crashes, a later sync runs and is not locked out."""
    first_worker_ran = threading.Event()

    def failing_worker(conn, pages=1, trigger_alerts=True):
        first_worker_ran.set()
        raise ConnectionError("Upstream Gazette connection failed")

    with patch("services.ingestion.jobs_ingestion.sync_jobs", side_effect=failing_worker):
        triggered_1 = trigger_jobs_background_sync(force=True, pages=1)
        assert triggered_1 is True

        assert first_worker_ran.wait(timeout=3.0)

        deadline = time.time() + 3.0
        while time.time() < deadline and js._LIVE_JOBS_IS_SYNCING:
            time.sleep(0.02)
        assert js._LIVE_JOBS_IS_SYNCING is False

        status = get_jobs_sync_status()
        assert status["status"] == "failed"
        assert "Upstream Gazette connection failed" in str(status.get("last_error"))

    # Now verify second sync runs successfully without being blocked
    second_worker_ran = threading.Event()

    def successful_worker(conn, pages=1, trigger_alerts=True):
        second_worker_ran.set()
        return {"fetched": 4, "new": 2, "updated": 0, "alerts_sent": 0}

    with patch("services.ingestion.jobs_ingestion.sync_jobs", side_effect=successful_worker):
        triggered_2 = trigger_jobs_background_sync(force=True, pages=1)
        assert triggered_2 is True
        assert second_worker_ran.wait(timeout=3.0)

        deadline = time.time() + 3.0
        while time.time() < deadline and js._LIVE_JOBS_IS_SYNCING:
            time.sleep(0.02)
        assert js._LIVE_JOBS_IS_SYNCING is False

        status2 = get_jobs_sync_status()
        assert status2["status"] == "success"
        assert status2["fetched"] == 4


def test_concurrent_status_reads_safe_during_execution():
    """Verify concurrent reads of get_jobs_sync_status() do not conflict or throw errors."""
    stop_event = threading.Event()

    def mock_worker(conn, pages=1, trigger_alerts=True):
        stop_event.wait(timeout=0.5)
        return {"fetched": 3, "new": 1, "updated": 1, "alerts_sent": 0}

    with patch("services.ingestion.jobs_ingestion.sync_jobs", side_effect=mock_worker):
        trigger_jobs_background_sync(force=True, pages=1)

        def reader():
            for _ in range(50):
                st = get_jobs_sync_status()
                assert isinstance(st, dict)
                time.sleep(0.005)

        readers = [threading.Thread(target=reader) for _ in range(5)]
        for r in readers:
            r.start()
        for r in readers:
            r.join()

        stop_event.set()
        deadline = time.time() + 3.0
        while time.time() < deadline and js._LIVE_JOBS_IS_SYNCING:
            time.sleep(0.02)
        assert js._LIVE_JOBS_IS_SYNCING is False
