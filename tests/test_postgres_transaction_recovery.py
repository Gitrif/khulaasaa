"""
PostgreSQL Transaction Recovery & Savepoint Isolation Tests.
Verifies PostgreSQL aborted transaction recovery, column-safe query guards,
and per-record savepoint isolation in ingestion pipelines.
"""
import os
import pytest

from data.postgres_adapter import PostgresConnectionWrapper
from tests.test_postgres_outbox_integration import get_pg_connection, HAVE_PSYCOPG2, validate_pg_test_url

if HAVE_PSYCOPG2:
    import psycopg2
    from psycopg2 import errors


@pytest.fixture
def pg_wrapper():
    """Provides an isolated PostgresConnectionWrapper on the test database."""
    conn = get_pg_connection()
    try:
        wrapper = PostgresConnectionWrapper(conn)
        yield wrapper, conn
    finally:
        try:
            conn.rollback()
        except Exception:
            pass
        conn.close()


def test_missing_column_savepoint_recovery_on_pg(pg_wrapper):
    """
    Proves that executing an invalid query inside SAVEPOINT ... ROLLBACK TO SAVEPOINT
    prevents PostgreSQL from poisoning the transaction (SQLSTATE 25P02).
    """
    wrapper, raw_conn = pg_wrapper

    # 1. Clean slate inside transaction
    wrapper.execute("SELECT 1;")

    # 2. Simulate querying a missing column with SAVEPOINT protection
    caught = False
    try:
        wrapper.execute("SAVEPOINT test_col_check;")
        # Intentionally query a non-existent column
        wrapper.execute("SELECT non_existent_column_xyz FROM users LIMIT 1;")
        wrapper.execute("RELEASE SAVEPOINT test_col_check;")
    except Exception as exc:
        caught = True
        wrapper.execute("ROLLBACK TO SAVEPOINT test_col_check;")

    assert caught is True

    # 3. Subsequent query MUST succeed on the same transaction block without 25P02
    res = wrapper.execute("SELECT count(*) as cnt FROM users;").fetchone()
    assert res is not None
    assert "cnt" in res or 0 in res


def test_unprotected_failure_aborts_transaction_on_pg(pg_wrapper):
    """
    Contrast test: proves that WITHOUT savepoint rollback, PostgreSQL raises
    psycopg2.errors.InFailedSqlTransaction (25P02) on any subsequent query.
    """
    wrapper, raw_conn = pg_wrapper

    try:
        wrapper.execute("SELECT non_existent_column_xyz FROM users LIMIT 1;")
    except Exception:
        pass  # Caught in python but NOT rolled back in PG

    # The next query MUST fail with InFailedSqlTransaction
    with pytest.raises(Exception) as exc_info:
        wrapper.execute("SELECT 1;")

    err_str = str(exc_info.value)
    assert "current transaction is aborted" in err_str or "25P02" in err_str


def test_notification_creation_conflict_safety_pg(pg_wrapper):
    """
    Verifies that create_logical_notification and create_notification_delivery
    handle duplicates cleanly on PostgreSQL using SAVEPOINT and ON CONFLICT.
    """
    wrapper, raw_conn = pg_wrapper
    from data.repos.notifications import (
        create_logical_notification,
        create_notification_delivery,
    )

    # Insert a dummy user for foreign keys if not exists
    u_cur = wrapper.execute("""
        INSERT INTO users (email, password_hash, full_name, is_active)
        VALUES ('test_notif_user@example.mv', 'hash', 'Test User', 1)
        ON CONFLICT (email) DO UPDATE SET full_name = 'Test User'
        RETURNING id;
    """)
    u_row = u_cur.fetchone()
    user_id = u_row["id"] if hasattr(u_row, "keys") else u_row[0]

    # Create first logical notification
    nid1 = create_logical_notification(
        wrapper,
        user_id=user_id,
        event_key="evt_pg_test_dup_1",
        content_type="news",
        content_id="art-101",
        title="Test Notification 1",
        summary="Test Summary",
        url="https://khulaasaa.mv/test-1",
    )
    assert nid1 is not None

    # Create identical notification (duplicate event_key for same user)
    nid2 = create_logical_notification(
        wrapper,
        user_id=user_id,
        event_key="evt_pg_test_dup_1",
        content_type="news",
        content_id="art-101",
        title="Test Notification 1 (Dup)",
        summary="Test Summary Updated",
        url="https://khulaasaa.mv/test-1",
    )
    # Must return the same ID without aborting the transaction
    assert nid2 == nid1

    # Delivery idempotence check
    did1 = create_notification_delivery(
        wrapper,
        notification_id=nid1,
        user_id=user_id,
        channel="telegram",
        destination="12345678",
        status="pending",
    )
    assert did1 is not None

    did2 = create_notification_delivery(
        wrapper,
        notification_id=nid1,
        user_id=user_id,
        channel="telegram",
        destination="12345678",
        status="pending",
    )
    assert did2 == did1

    # Verify transaction is healthy
    check_row = wrapper.execute("SELECT count(*) as cnt FROM notification_deliveries WHERE id = ?;", (did1,)).fetchone()
    assert check_row["cnt"] == 1


def test_batch_ingestion_savepoint_isolation_pg(pg_wrapper):
    """
    Proves that a single failing item in a batch does not roll back preceding
    or succeeding items when guarded by per-record SAVEPOINTs.
    """
    wrapper, raw_conn = pg_wrapper

    # Create a test table for the batch isolation experiment
    wrapper.execute("""
        CREATE TEMP TABLE temp_batch_test (
            id SERIAL PRIMARY KEY,
            val TEXT UNIQUE NOT NULL
        );
    """)

    items_to_insert = ["valid_item_1", "valid_item_1", "valid_item_3"]  # item 2 duplicates item 1
    persisted_items = []

    for item in items_to_insert:
        try:
            wrapper.execute("SAVEPOINT item_batch_sp;")
            wrapper.execute("INSERT INTO temp_batch_test (val) VALUES (?);", (item,))
            wrapper.execute("RELEASE SAVEPOINT item_batch_sp;")
            persisted_items.append(item)
        except Exception:
            try:
                wrapper.execute("ROLLBACK TO SAVEPOINT item_batch_sp;")
            except Exception:
                pass

    # Items 1 and 3 should be persisted; item 2 was rejected
    assert persisted_items == ["valid_item_1", "valid_item_3"]

    rows = wrapper.execute("SELECT val FROM temp_batch_test ORDER BY id ASC;").fetchall()
    stored_vals = [r["val"] for r in rows]
    assert stored_vals == ["valid_item_1", "valid_item_3"]


def test_dispatch_news_alerts_tolerates_missing_telegram_verified_pg(pg_wrapper, monkeypatch):
    """
    Simulates production environment where telegram_verified column is temporarily absent.
    Proves dispatch_news_alerts rolls back to savepoint and executes subsequent queries
    (such as get_active_sponsored_ad) without raising InFailedSqlTransaction.
    """
    wrapper, raw_conn = pg_wrapper
    from alerts.telegram_dispatch import dispatch_news_alerts

    # Ensure required tables exist in test DB
    wrapper.execute("""
        CREATE TABLE IF NOT EXISTS telegram_subscribers (
            id SERIAL PRIMARY KEY,
            chat_id TEXT UNIQUE NOT NULL,
            name TEXT,
            keywords TEXT,
            is_paid INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS sponsored_ads (
            id SERIAL PRIMARY KEY,
            brand_name TEXT,
            campaign_name TEXT,
            sponsor_name TEXT,
            text_html TEXT,
            tagline TEXT,
            cta_text TEXT,
            cta_url TEXT,
            link_url TEXT,
            target_category TEXT DEFAULT 'all',
            is_active INTEGER DEFAULT 1,
            impressions INTEGER DEFAULT 0,
            max_impressions INTEGER DEFAULT NULL,
            expires_at TIMESTAMP DEFAULT NULL,
            pricing_tier TEXT DEFAULT 'custom'
        );
        CREATE TABLE IF NOT EXISTS sent_alerts (
            id SERIAL PRIMARY KEY,
            notice_id TEXT NOT NULL,
            chat_id TEXT NOT NULL,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Temporarily drop/rename telegram_verified column inside this transaction
    wrapper.execute("ALTER TABLE users DROP COLUMN IF EXISTS telegram_verified;")

    # Setup monkeypatch for Telegram credentials and message sender
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "mock_bot_token_123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100123456789")
    sent_calls = []
    monkeypatch.setattr(
        "alerts.telegram_dispatch.send_telegram_message",
        lambda *args, **kwargs: {"ok": True, "result": {"message_id": 999}},
    )

    test_articles = [{
        "id": "pg-test-art-1",
        "title": "Maldives Tech Update",
        "url": "https://khulaasaa.mv/pg-test-1",
        "source": "Sun Online",
        "published_at": "2026-10-27T10:00:00Z",
    }]

    # dispatch_news_alerts will query telegram_subscribers, try the missing telegram_verified,
    # safely catch and rollback to savepoint, then query get_active_sponsored_ad,
    # and finish without aborting PostgreSQL transaction.
    res = dispatch_news_alerts(wrapper, test_articles)
    assert isinstance(res, list)

    # Re-add column so other tests are unaffected if committed
    wrapper.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_verified INTEGER DEFAULT 0;")

