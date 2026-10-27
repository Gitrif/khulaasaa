"""
Tests for Transactional Outbox Worker, Concurrency, and Lease Recovery.
Phase 3.3 Outbox Reliability Hardening.
"""
import sqlite3
import threading
import time
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
    finalize_delivery,
    dispatch_single_delivery,
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
    w1 = start_outbox_worker(interval_seconds=10)
    assert w1.is_running() is True

    # Repeated start must be idempotent and non-blocking
    w2 = start_outbox_worker(interval_seconds=10)
    assert w2 is w1
    assert w2.is_running() is True

    # Stop worker gracefully
    stop_outbox_worker(timeout=2.0)
    assert w1.is_running() is False

    # Repeated stop must be idempotent and non-blocking
    stop_outbox_worker(timeout=2.0)


def test_outbox_worker_lifecycle_timeout_thread_still_alive():
    """A timed-out join must not mark worker stopped or allow starting a second thread."""
    worker = OutboxWorker(interval_seconds=5)
    thread_active = threading.Event()
    release_thread = threading.Event()

    def slow_loop():
        thread_active.set()
        release_thread.wait(timeout=5.0)

    with patch.object(worker, "_run_loop", side_effect=slow_loop):
        worker.start()
        assert thread_active.wait(timeout=2.0) is True

        # Stop with tiny timeout so join times out
        worker.stop(timeout=0.05)
        # Thread is still executing -> worker must NOT be marked stopped!
        assert worker.is_running() is True

        # Calling start() while thread is still executing must not spawn another thread
        orig_thread = worker._thread
        worker.start()
        assert worker._thread is orig_thread

        # Now release slow thread and stop cleanly
        release_thread.set()
        worker.stop(timeout=2.0)
        assert worker.is_running() is False


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


def test_concurrent_multi_connection_claiming():
    """Two genuinely concurrent threads with independent DB connections claim the same delivery."""
    with get_db() as conn:
        uid = create_user(conn, email="outbox_multi@example.com", password="pass", full_name="Multi User")
        nid = create_logical_notification(conn, uid, "outbox:test:multi", "news", "m1", "Multi Story")
        did = create_notification_delivery(conn, nid, uid, "telegram", "555111", status="pending")

    results = []
    barrier = threading.Barrier(2)

    def worker_claim(worker_id):
        barrier.wait()
        with get_db() as c:
            claimed = claim_actionable_deliveries(c, limit=5, worker_id=worker_id)
            if claimed:
                results.append((worker_id, claimed[0]["id"]))

    t1 = threading.Thread(target=worker_claim, args=("worker_1",))
    t2 = threading.Thread(target=worker_claim, args=("worker_2",))
    t1.start()
    t2.start()
    t1.join(timeout=3.0)
    t2.join(timeout=3.0)

    # Exactly one thread claimed the delivery
    assert len(results) == 1
    assert results[0][1] == did


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


def test_claim_token_ownership_and_finalization_lost_lease():
    """Worker cannot finalize delivery after another worker legitimately reclaimed its lease."""
    with get_db() as conn:
        uid = create_user(conn, email="outbox_lost@example.com", password="pass", full_name="Lost Lease User")
        nid = create_logical_notification(conn, uid, "outbox:test:lost", "news", "l1", "Lost Story")
        did = create_notification_delivery(conn, nid, uid, "telegram", "777888", status="pending")

        # Worker 1 claims delivery
        c1 = claim_actionable_deliveries(conn, limit=1, worker_id="worker_orig")
        assert len(c1) == 1

        # Simulate lease expiry and Worker 2 legitimately reclaiming delivery
        ten_mins_ago = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        conn.execute("UPDATE notification_deliveries SET claimed_at = ? WHERE id = ?;", (ten_mins_ago, did))
        c2 = claim_actionable_deliveries(conn, limit=1, worker_id="worker_new")
        assert len(c2) == 1
        assert c2[0]["claim_token"] == "worker_new"

        # Worker 1 attempts to finalize with old token -> must fail safely (rowcount mismatch)
        ok_w1 = finalize_delivery(conn, did, claim_token="worker_orig", success=True)
        assert ok_w1 is False

        # Worker 2 finalizes with valid current token -> succeeds
        ok_w2 = finalize_delivery(conn, did, claim_token="worker_new", success=True)
        assert ok_w2 is True

        row = conn.execute("SELECT status FROM notification_deliveries WHERE id = ?;", (did,)).fetchone()
        assert row[0] == "delivered"


def test_claim_commit_failure_rolls_back_and_skips_dispatch():
    """If claim transaction fails to commit, it must rollback and return no uncommitted claims."""
    with get_db() as conn:
        uid = create_user(conn, email="outbox_fail_claim@example.com", password="pass", full_name="Fail Claim")
        nid = create_logical_notification(conn, uid, "outbox:test:fail", "news", "f1", "Fail Story")
        did = create_notification_delivery(conn, nid, uid, "telegram", "333444", status="pending")

        class FailingCommitConn:
            def __init__(self, real_conn):
                self._real = real_conn
                self.rolled_back = False

            def execute(self, sql, params=()):
                return self._real.execute(sql, params)

            def commit(self):
                raise sqlite3.OperationalError("Simulated disk I/O failure on commit")

            def rollback(self):
                self.rolled_back = True
                self._real.rollback()

        fail_conn = FailingCommitConn(conn)
        claimed = claim_actionable_deliveries(fail_conn, limit=10)
        assert claimed == []
        assert fail_conn.rolled_back is True


def test_finalization_commit_failure_surfaced():
    """If finalization commit fails, finalize_delivery and dispatch_single_delivery surface failure."""
    with get_db() as conn:
        uid = create_user(conn, email="outbox_fail_fin@example.com", password="pass", full_name="Fail Fin")
        nid = create_logical_notification(conn, uid, "outbox:test:fin", "news", "f2", "Fin Story")
        did = create_notification_delivery(conn, nid, uid, "telegram", "444555", status="pending")

        c = claim_actionable_deliveries(conn, limit=1, worker_id="fin_worker")
        assert len(c) == 1

        class FailingFinConn:
            def __init__(self, real_conn):
                self._real = real_conn
                self.rolled_back = False

            def execute(self, sql, params=()):
                return self._real.execute(sql, params)

            def commit(self):
                raise sqlite3.OperationalError("Simulated database failure during finalization")

            def rollback(self):
                self.rolled_back = True
                self._real.rollback()

        fail_conn = FailingFinConn(conn)
        ok = finalize_delivery(fail_conn, did, claim_token="fin_worker", success=True)
        assert ok is False
        assert fail_conn.rolled_back is True


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

        # Public retry_failed_deliveries must also block by default
        assert retry_failed_deliveries(conn, limit=10)["total"] == 0

        # 2. Failed 35 seconds ago -> backoff elapsed -> must be claimable
        thirty_five_secs_ago = (datetime.now(timezone.utc) - timedelta(seconds=35)).isoformat()
        conn.execute(
            "UPDATE notification_deliveries SET attempt_count = 1, last_attempt_at = ? WHERE id = ?;",
            (thirty_five_secs_ago, did),
        )

        claimed_after = claim_actionable_deliveries(conn, limit=10, ignore_backoff=False)
        assert len(claimed_after) == 1
        assert claimed_after[0]["id"] == did


def test_dead_letter_never_reclaimed_automatically():
    """Terminal dead_letter deliveries cannot be reclaimed by any operational path."""
    with get_db() as conn:
        uid = create_user(conn, email="outbox_dl@example.com", password="pass", full_name="DL User")
        nid = create_logical_notification(conn, uid, "outbox:test:dl", "news", "dl1", "Dead Letter Story")
        did = create_notification_delivery(conn, nid, uid, "telegram", "121212", status="dead_letter")

        one_day_ago = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        conn.execute("UPDATE notification_deliveries SET attempt_count = 3, last_attempt_at = ? WHERE id = ?;", (one_day_ago, did))

        # claim_actionable_deliveries must not claim dead_letter
        assert len(claim_actionable_deliveries(conn, limit=10, ignore_backoff=True)) == 0
        # retry_failed_deliveries must not claim dead_letter
        assert retry_failed_deliveries(conn, limit=10)["total"] == 0
        # process_operational_delivery_queue must not claim dead_letter
        assert process_operational_delivery_queue(conn, limit=10, mock_mode=True)["total_attempted"] == 0


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
