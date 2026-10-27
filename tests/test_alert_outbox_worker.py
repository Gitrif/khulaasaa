"""
Tests for Transactional Outbox Worker, Concurrency, and Lease Recovery.
Phase 3.2 Outbox Verification.
"""
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest

from data.database import get_db, init_db, create_user
from data.repos.notifications import (
    create_logical_notification,
    create_notification_delivery,
)
from services.alert_delivery_service import (
    claim_actionable_deliveries,
    process_operational_delivery_queue,
    retry_failed_deliveries,
)
from services.alert_delivery_worker import (
    OutboxWorker,
    start_outbox_worker,
    stop_outbox_worker,
)


@pytest.fixture(autouse=True)
def clean_outbox_test_state():
    """Ensure clean test state for outbox worker tests."""
    init_db()
    with get_db() as conn:
        conn.execute("DELETE FROM notification_deliveries;")
        conn.execute("DELETE FROM notifications;")
        conn.execute("DELETE FROM users WHERE email LIKE 'outbox_%';")
    yield
    stop_outbox_worker(timeout=2.0)
    with get_db() as conn:
        conn.execute("DELETE FROM notification_deliveries;")
        conn.execute("DELETE FROM notifications;")
        conn.execute("DELETE FROM users WHERE email LIKE 'outbox_%';")


def test_outbox_worker_lifecycle_no_deadlock():
    """Verify start_outbox_worker and stop_outbox_worker never deadlock even with repeated calls."""
    # Start worker
    w1 = start_outbox_worker(interval_seconds=10)
    assert w1._is_running is True

    # Repeated start must be idempotent and non-blocking
    w2 = start_outbox_worker(interval_seconds=10)
    assert w2 is w1
    assert w2._is_running is True

    # Stop worker gracefully
    stop_outbox_worker(timeout=2.0)
    assert w1._is_running is False

    # Repeated stop must be idempotent and non-blocking
    stop_outbox_worker(timeout=2.0)


def test_concurrent_worker_atomic_claiming():
    """Verify atomic database claim: only one worker claims a delivery, second worker gets 0."""
    with get_db() as conn:
        uid = create_user(conn, email="outbox_concur@example.com", password="pass", full_name="Concur User")
        nid = create_logical_notification(conn, uid, "outbox:test:1", "news", "1", "Breaking Story")
        did = create_notification_delivery(conn, nid, uid, "telegram", "123456", status="pending")

        # Worker 1 claims
        claimed_w1 = claim_actionable_deliveries(conn, limit=10, worker_id="worker_alpha")
        assert len(claimed_w1) == 1
        assert claimed_w1[0]["id"] == did
        assert claimed_w1[0]["claim_token"] == "worker_alpha"

        # Worker 2 attempts to claim concurrently -> must get 0
        claimed_w2 = claim_actionable_deliveries(conn, limit=10, worker_id="worker_beta")
        assert len(claimed_w2) == 0

        # Row in database is in 'claiming' status with token 'worker_alpha'
        row = conn.execute("SELECT status, claim_token FROM notification_deliveries WHERE id = ?;", (did,)).fetchone()
        assert row[0] == "claiming"
        assert row[1] == "worker_alpha"


def test_lease_expiry_and_crashed_worker_recovery():
    """Verify deliveries stuck in 'claiming' past lease time are reclaimed and recovered."""
    with get_db() as conn:
        uid = create_user(conn, email="outbox_lease@example.com", password="pass", full_name="Lease User")
        nid = create_logical_notification(conn, uid, "outbox:test:2", "news", "2", "Lease Test")
        did = create_notification_delivery(conn, nid, uid, "telegram", "654321", status="pending")

        # Simulate a worker that crashed 5 minutes ago while claiming
        five_mins_ago = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        conn.execute(
            "UPDATE notification_deliveries SET status = 'claiming', claim_token = 'crashed_token', claimed_at = ? WHERE id = ?;",
            (five_mins_ago, did),
        )

        # Active worker claims with standard 180s lease -> must reclaim crashed record
        reclaimed = claim_actionable_deliveries(conn, limit=10, lease_seconds=180, worker_id="active_worker")
        assert len(reclaimed) == 1
        assert reclaimed[0]["id"] == did
        assert reclaimed[0]["claim_token"] == "active_worker"


def test_retry_backoff_timing_enforcement():
    """Verify failed deliveries honor backoff schedule before becoming claimable."""
    with get_db() as conn:
        uid = create_user(conn, email="outbox_backoff@example.com", password="pass", full_name="Backoff User")
        nid = create_logical_notification(conn, uid, "outbox:test:3", "news", "3", "Backoff Story")
        did = create_notification_delivery(conn, nid, uid, "telegram", "999888", status="failed")

        # 1. Just failed 5 seconds ago (backoff for attempt 1 is 30s) -> should NOT be claimable
        five_secs_ago = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
        conn.execute(
            "UPDATE notification_deliveries SET attempt_count = 1, last_attempt_at = ? WHERE id = ?;",
            (five_secs_ago, did),
        )

        claimed = claim_actionable_deliveries(conn, limit=10, ignore_backoff=False)
        assert len(claimed) == 0

        # 2. Failed 35 seconds ago -> backoff elapsed -> must be claimable
        thirty_five_secs_ago = (datetime.now(timezone.utc) - timedelta(seconds=35)).isoformat()
        conn.execute(
            "UPDATE notification_deliveries SET attempt_count = 1, last_attempt_at = ? WHERE id = ?;",
            (thirty_five_secs_ago, did),
        )

        claimed_after = claim_actionable_deliveries(conn, limit=10, ignore_backoff=False)
        assert len(claimed_after) == 1
        assert claimed_after[0]["id"] == did


def test_queued_digest_excluded_from_operational_queue():
    """Verify queued_digest deliveries are explicitly preserved and never claimed by operational sweep."""
    with get_db() as conn:
        uid = create_user(conn, email="outbox_digest@example.com", password="pass", full_name="Digest User")
        nid = create_logical_notification(conn, uid, "outbox:test:4", "news", "4", "Digest Only Story")
        did = create_notification_delivery(conn, nid, uid, "telegram", "112233", status="queued_digest")

        res = process_operational_delivery_queue(conn, limit=10, mock_mode=True)
        assert res["dispatched"] == 0
        assert res["total_attempted"] == 0

        row = conn.execute("SELECT status FROM notification_deliveries WHERE id = ?;", (did,)).fetchone()
        assert row[0] == "queued_digest"
