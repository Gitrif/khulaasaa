"""
Genuine PostgreSQL Integration Tests for Outbox Claim Races, Rollback, and Lease Recovery.
Phase 3.3 PostgreSQL Verification.
"""
import os
import threading
from datetime import datetime, timedelta, timezone
import pytest

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAVE_PSYCOPG2 = True
except ImportError:
    HAVE_PSYCOPG2 = False

from data.postgres_adapter import PostgresConnectionWrapper
from services.alert_delivery_service import (
    claim_actionable_deliveries,
    finalize_delivery,
    retry_failed_deliveries,
)

PG_TEST_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/khulaasaa_test")


def get_pg_connection():
    if not HAVE_PSYCOPG2:
        pytest.skip("psycopg2 is not installed")
    try:
        conn = psycopg2.connect(PG_TEST_URL)
        conn.autocommit = False
        return conn
    except Exception as exc:
        pytest.skip(f"PostgreSQL test database not reachable at {PG_TEST_URL}: {exc}")


@pytest.fixture(scope="module", autouse=True)
def setup_pg_tables():
    """Ensure PostgreSQL test schema exists."""
    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL DEFAULT '',
                    is_active INTEGER NOT NULL DEFAULT 1,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    is_paid INTEGER NOT NULL DEFAULT 0,
                    telegram_chat_id TEXT,
                    telegram_verified INTEGER DEFAULT 0,
                    viber_user_id TEXT,
                    viber_verified INTEGER DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS notifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    event_key TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    content_id TEXT NOT NULL,
                    event_version INTEGER NOT NULL DEFAULT 1,
                    reason TEXT NOT NULL DEFAULT 'breaking',
                    reason_target TEXT,
                    title TEXT NOT NULL,
                    summary TEXT,
                    url TEXT,
                    is_urgent INTEGER NOT NULL DEFAULT 0,
                    frequency TEXT NOT NULL DEFAULT 'instant',
                    is_read INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_pg_user_event UNIQUE (user_id, event_key)
                );

                CREATE TABLE IF NOT EXISTS notification_deliveries (
                    id SERIAL PRIMARY KEY,
                    notification_id INTEGER NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    channel TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    claim_token TEXT,
                    claimed_at TIMESTAMPTZ,
                    error_message TEXT,
                    last_attempt_at TIMESTAMPTZ,
                    delivered_at TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT uq_pg_notification_channel UNIQUE (notification_id, channel)
                );
            """)
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def clean_pg_deliveries():
    """Clean test data before and after each test."""
    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM notification_deliveries;")
            cur.execute("DELETE FROM notifications;")
            cur.execute("DELETE FROM users WHERE email LIKE 'pg_test_%';")
        conn.commit()
    finally:
        conn.close()
    yield
    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM notification_deliveries;")
            cur.execute("DELETE FROM notifications;")
            cur.execute("DELETE FROM users WHERE email LIKE 'pg_test_%';")
        conn.commit()
    finally:
        conn.close()


def test_pg_schema_and_column_compatibility():
    """Verify claim_token and claimed_at columns exist and work under PostgreSQL."""
    conn = get_pg_connection()
    try:
        wrapper = PostgresConnectionWrapper(conn)
        cur = wrapper.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'notification_deliveries'
              AND column_name IN ('claim_token', 'claimed_at');
            """
        )
        cols = {row["column_name"]: row["data_type"] for row in cur.fetchall()}
        assert "claim_token" in cols
        assert "claimed_at" in cols
    finally:
        conn.close()


def test_pg_concurrent_claim_race(clean_pg_deliveries):
    """Two independent PostgreSQL connections race to claim the same pending delivery."""
    conn_setup = get_pg_connection()
    try:
        w_setup = PostgresConnectionWrapper(conn_setup)
        cur_u = w_setup.execute(
            "INSERT INTO users (email, password_hash, full_name) VALUES (?, ?, ?) RETURNING id;",
            ("pg_test_race@example.com", "h", "PG Race User"),
        )
        uid = cur_u.fetchone()["id"]

        cur_n = w_setup.execute(
            "INSERT INTO notifications (user_id, event_key, content_type, content_id, title) VALUES (?, ?, ?, ?, ?) RETURNING id;",
            (uid, "pg:event:race", "news", "1", "PG Race"),
        )
        nid = cur_n.fetchone()["id"]

        cur_d = w_setup.execute(
            "INSERT INTO notification_deliveries (notification_id, user_id, channel, destination, status) VALUES (?, ?, ?, ?, ?) RETURNING id;",
            (nid, uid, "telegram", "998877", "pending"),
        )
        did = cur_d.fetchone()["id"]
        conn_setup.commit()
    finally:
        conn_setup.close()

    results = []
    barrier = threading.Barrier(2)

    def pg_worker(worker_id):
        conn_w = get_pg_connection()
        try:
            wrapper = PostgresConnectionWrapper(conn_w)
            barrier.wait()
            claimed = claim_actionable_deliveries(wrapper, limit=5, worker_id=worker_id)
            if claimed:
                results.append((worker_id, claimed[0]["id"]))
        finally:
            conn_w.close()

    t1 = threading.Thread(target=pg_worker, args=("pg_worker_1",))
    t2 = threading.Thread(target=pg_worker, args=("pg_worker_2",))
    t1.start()
    t2.start()
    t1.join(timeout=5.0)
    t2.join(timeout=5.0)

    # In genuine PostgreSQL, exactly one worker won the atomic claim
    assert len(results) == 1
    assert results[0][1] == did


def test_pg_rollback_on_claim_failure(clean_pg_deliveries):
    """Verify rollback on PostgreSQL if claim transaction fails."""
    conn = get_pg_connection()
    try:
        wrapper = PostgresConnectionWrapper(conn)
        cur_u = wrapper.execute(
            "INSERT INTO users (email, password_hash, full_name) VALUES (?, ?, ?) RETURNING id;",
            ("pg_test_rb@example.com", "h", "PG Rollback User"),
        )
        uid = cur_u.fetchone()["id"]
        cur_n = wrapper.execute(
            "INSERT INTO notifications (user_id, event_key, content_type, content_id, title) VALUES (?, ?, ?, ?, ?) RETURNING id;",
            (uid, "pg:event:rb", "news", "2", "PG Rollback"),
        )
        nid = cur_n.fetchone()["id"]
        cur_d = wrapper.execute(
            "INSERT INTO notification_deliveries (notification_id, user_id, channel, destination, status) VALUES (?, ?, ?, ?, ?) RETURNING id;",
            (nid, uid, "telegram", "112244", "pending"),
        )
        did = cur_d.fetchone()["id"]
        conn.commit()

        # Mock connection where commit fails
        class FailingPGCommit(PostgresConnectionWrapper):
            def __init__(self, real_conn):
                super().__init__(real_conn)
                self.rolled_back = False

            def commit(self):
                raise psycopg2.OperationalError("Simulated PostgreSQL commit error")

            def rollback(self):
                self.rolled_back = True
                super().rollback()

        fail_w = FailingPGCommit(conn)
        claimed = claim_actionable_deliveries(fail_w, limit=10, worker_id="failing_worker")
        assert claimed == []
        assert fail_w.rolled_back is True

        # Refresh connection: delivery must still be pending in PostgreSQL!
        conn_check = get_pg_connection()
        try:
            w_check = PostgresConnectionWrapper(conn_check)
            row = w_check.execute("SELECT status, claim_token FROM notification_deliveries WHERE id = ?;", (did,)).fetchone()
            assert row["status"] == "pending"
            assert row["claim_token"] is None
        finally:
            conn_check.close()
    finally:
        conn.close()


def test_pg_finalization_lost_lease(clean_pg_deliveries):
    """Verify PostgreSQL finalization rowcount check on reclaimed lease."""
    conn = get_pg_connection()
    try:
        wrapper = PostgresConnectionWrapper(conn)
        cur_u = wrapper.execute(
            "INSERT INTO users (email, password_hash, full_name) VALUES (?, ?, ?) RETURNING id;",
            ("pg_test_fin@example.com", "h", "PG Fin User"),
        )
        uid = cur_u.fetchone()["id"]
        cur_n = wrapper.execute(
            "INSERT INTO notifications (user_id, event_key, content_type, content_id, title) VALUES (?, ?, ?, ?, ?) RETURNING id;",
            (uid, "pg:event:fin", "news", "3", "PG Fin"),
        )
        nid = cur_n.fetchone()["id"]
        cur_d = wrapper.execute(
            "INSERT INTO notification_deliveries (notification_id, user_id, channel, destination, status) VALUES (?, ?, ?, ?, ?) RETURNING id;",
            (nid, uid, "telegram", "334455", "pending"),
        )
        did = cur_d.fetchone()["id"]
        conn.commit()

        # Worker 1 claims
        c1 = claim_actionable_deliveries(wrapper, limit=1, worker_id="pg_worker_1")
        assert len(c1) == 1

        # Simulate lease expiry in PostgreSQL
        ten_mins_ago = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        wrapper.execute("UPDATE notification_deliveries SET claimed_at = ? WHERE id = ?;", (ten_mins_ago, did))
        conn.commit()

        # Worker 2 reclaims
        c2 = claim_actionable_deliveries(wrapper, limit=1, worker_id="pg_worker_2")
        assert len(c2) == 1
        assert c2[0]["claim_token"] == "pg_worker_2"

        # Worker 1 finalization must fail in PostgreSQL
        ok1 = finalize_delivery(wrapper, did, claim_token="pg_worker_1", success=True)
        assert ok1 is False

        # Worker 2 finalization succeeds
        ok2 = finalize_delivery(wrapper, did, claim_token="pg_worker_2", success=True)
        assert ok2 is True

        row = wrapper.execute("SELECT status, claim_token FROM notification_deliveries WHERE id = ?;", (did,)).fetchone()
        assert row["status"] == "delivered"
        assert row["claim_token"] is None
    finally:
        conn.close()
