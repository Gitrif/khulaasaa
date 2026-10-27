"""
Jobs Background Ingestion Lock and Recovery Tests.
Verifies that background jobs synchronization cannot become stuck or deadlocked.
Strictly under 500 lines. Zero emojis.
"""
from __future__ import annotations

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
    with patch("scrapers.jobs.sync_jobs", return_value=mock_result):
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
    with patch("scrapers.jobs.sync_jobs", side_effect=RuntimeError("Gazette portal down")):
        res = run_jobs_sync(pages=1, trigger_alerts=False)

    assert res.get("status") == "failed"
    assert "Gazette portal down" in res.get("error", "")
    assert js._LIVE_JOBS_IS_SYNCING is False
    status = get_jobs_sync_status()
    assert status["status"] == "failed"
    assert "Gazette portal down" in status["last_error"]


def test_trigger_jobs_background_sync_does_not_abort_prematurely():
    """Verify trigger_jobs_background_sync successfully spawns worker without immediate already_running abort."""
    sync_called = False

    def mock_sync(conn, pages=1, trigger_alerts=True):
        nonlocal sync_called
        sync_called = True
        return {"fetched": 3, "new": 1, "updated": 0, "alerts_sent": 0}

    with patch("scrapers.jobs.sync_jobs", side_effect=mock_sync):
        triggered = trigger_jobs_background_sync(force=True, pages=1)
        assert triggered is True

        # Wait for thread execution
        deadline = time.time() + 3.0
        while time.time() < deadline and not sync_called:
            time.sleep(0.05)

        assert sync_called is True

        # Wait for thread lock release
        while time.time() < deadline and js._LIVE_JOBS_IS_SYNCING:
            time.sleep(0.05)

        assert js._LIVE_JOBS_IS_SYNCING is False


def test_trigger_jobs_background_sync_subsequent_runs_not_blocked():
    """Verify that after a sync completes, subsequent triggered syncs can run freely (never stuck)."""
    with patch("scrapers.jobs.sync_jobs", return_value={"fetched": 1, "new": 0, "updated": 0, "alerts_sent": 0}):
        # First sync
        res1 = run_jobs_sync(pages=1, trigger_alerts=False)
        assert res1["fetched"] == 1
        assert js._LIVE_JOBS_IS_SYNCING is False

        # Second sync immediately forced
        res2 = run_jobs_sync(pages=1, trigger_alerts=False)
        assert res2["fetched"] == 1
        assert js._LIVE_JOBS_IS_SYNCING is False
