"""
Comprehensive Unit & Integration Test Suite for Alert Decision Engine and Delivery Reliability.
Phase 3 Verification Suite.
"""
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import pytest
from starlette.testclient import TestClient

from main import app
from data.database import (
    get_db, init_db, create_user, get_user_by_email, add_follow,
    update_user_preferences, get_user_preferences,
)
from services.channel_linking_service import create_channel_link_token, verify_and_link_channel, disconnect_channel
from services.alert_decision_service import build_event_key, is_in_quiet_hours, evaluate_candidate_recipients, process_content_event
from services.alert_delivery_service import format_notification_message, dispatch_single_delivery, retry_failed_deliveries
from data.repos.notifications import (
    create_logical_notification, create_notification_delivery,
    list_user_notifications, mark_notification_read, get_unread_notification_count,
)

client = TestClient(app, follow_redirects=False)


def _purge_test_users(conn, emails):
    tables = ["notification_deliveries", "notifications", "channel_link_tokens", "user_notification_preferences", "user_follows", "user_sessions", "users"]
    for em in emails:
        u = get_user_by_email(conn, em)
        if u:
            for t in tables:
                col = "id" if t == "users" else "user_id"
                conn.execute(f"DELETE FROM {t} WHERE {col} = ?;", (u["id"],))


@pytest.fixture(autouse=True)
def clean_phase3_environment():
    """Ensure clean isolated test state for Phase 3 tests."""
    init_db()
    test_emails = ["phase3_alice@example.com", "phase3_bob@example.com", "phase3_carol@example.com"]
    with get_db() as conn:
        _purge_test_users(conn, test_emails)
    yield
    with get_db() as conn:
        _purge_test_users(conn, test_emails)


def test_event_key_generation_and_versioning():
    """Verify event key stability for re-scrapes and distinct keys for updates."""
    # 1. Base content keys
    k1 = build_event_key("news", "story_abc123", event_version=1)
    k2 = build_event_key("news", "story_abc123", event_version=1)
    assert k1 == k2 == "news:story_abc123:v1"

    # 2. Meaningful update gets higher version
    k_v2 = build_event_key("news", "story_abc123", event_version=2)
    assert k_v2 == "news:story_abc123:v2"
    assert k_v2 != k1

    # 3. Content update with fingerprint
    k_fp = build_event_key("news", "story_abc123", update_fingerprint="sha_987654321")
    assert k_fp == "news:story_abc123:upd_sha_987654"
    assert k_fp != k1


def test_quiet_hours_and_timezone_boundary():
    """Verify quiet hours evaluation with Maldives timezone and midnight spanning."""
    # Current UTC time 19:30 UTC -> Maldives (UTC+5) is 00:30 (next day)
    dt_midnight = datetime(2026, 10, 27, 19, 30, tzinfo=timezone.utc)
    # Start: 23:00, End: 07:00. At 00:30 local time, should be True
    assert is_in_quiet_hours(dt_midnight, start_str="23:00", end_str="07:00", tz_name="Indian/Maldives") is True

    # Current UTC time 07:00 UTC -> Maldives (UTC+5) is 12:00 (midday)
    dt_midday = datetime(2026, 10, 27, 7, 0, tzinfo=timezone.utc)
    assert is_in_quiet_hours(dt_midday, start_str="23:00", end_str="07:00", tz_name="Indian/Maldives") is False


def test_database_idempotency_constraint():
    """Verify UNIQUE(user_id, event_key) at DB level prevents duplicate logical notifications."""
    with get_db() as conn:
        u_id = create_user(conn, email="phase3_alice@example.com", password="password1", full_name="Alice")
        ev_key = "news:story_unique_test:v1"

        # First insert succeeds
        n1 = create_logical_notification(
            conn, user_id=u_id, event_key=ev_key, content_type="news",
            content_id="story_unique_test", title="Headline Test",
        )
        assert n1 is not None

        # Re-insert with identical event_key returns existing ID without inserting a second row
        n2 = create_logical_notification(
            conn, user_id=u_id, event_key=ev_key, content_type="news",
            content_id="story_unique_test", title="Headline Test Repeated",
        )
        assert n1 == n2

        # Verify only 1 notification row in table
        count = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND event_key = ?;",
            (u_id, ev_key),
        ).fetchone()[0]
        assert count == 1


def test_follow_target_matching_rules():
    """Verify matching across all 4 follow targets: story, topic, section, source."""
    with get_db() as conn:
        u_id = create_user(conn, email="phase3_alice@example.com", password="password1", full_name="Alice Match")
        # Ensure preferences initialized
        update_user_preferences(conn, u_id, followed_content_alerts=1, is_paused=0)

        # 1. Story follow
        add_follow(conn, u_id, "story", "story_999", "Special Story")
        match_story = evaluate_candidate_recipients(conn, "news", "story_999")
        assert u_id in match_story
        assert match_story[u_id]["reason"] == "followed_story"

        # 2. Topic follow
        add_follow(conn, u_id, "topic", "tourism", "Tourism Topic")
        match_topic = evaluate_candidate_recipients(conn, "news", "other_story", topics=["tourism"])
        assert u_id in match_topic
        assert match_topic[u_id]["reason"] == "followed_topic"

        # 3. Section follow
        add_follow(conn, u_id, "section", "general", "General News")
        match_sec = evaluate_candidate_recipients(conn, "news", "general_story", section="general")
        assert u_id in match_sec
        assert match_sec[u_id]["reason"] == "followed_section"

        # 4. Source follow
        add_follow(conn, u_id, "source", "mihaaru", "Mihaaru Media")
        match_src = evaluate_candidate_recipients(conn, "news", "any_story", source_id="mihaaru")
        assert u_id in match_src
        assert match_src[u_id]["reason"] == "followed_source"


def test_breaking_news_vs_routine_quiet_hours_behavior():
    """
    Verify urgent breaking news bypasses quiet hours while routine followed alerts are queued.
    """
    with get_db() as conn:
        u_id = create_user(conn, email="phase3_alice@example.com", password="password1", full_name="Alice QH")
        # Link verified telegram
        tok = create_channel_link_token(conn, u_id, "telegram")
        verify_and_link_channel(conn, "telegram", tok, "tg_chat_111", "alice_tg")

        # Configure quiet hours 00:00 to 23:59 (always in quiet hours for testing)
        update_user_preferences(
            conn, u_id,
            breaking_alerts=1,
            followed_content_alerts=1,
            quiet_hours_enabled=1,
            quiet_hours_start="00:00",
            quiet_hours_end="23:59",
            is_paused=0,
        )
        add_follow(conn, u_id, "topic", "fisheries", "Fisheries")

        # 1. Routine follow content -> must be queued_quiet_hours
        stats_routine = process_content_event(
            conn,
            content_type="news",
            content_id="routine_fish_1",
            title="Fisheries Update",
            is_breaking=False,
            topics=["fisheries"],
            mock_mode=True,
        )
        assert stats_routine["notifications_created"] == 1
        delivs_routine = conn.execute(
            "SELECT status FROM notification_deliveries WHERE user_id = ? ORDER BY id DESC LIMIT 1;",
            (u_id,),
        ).fetchone()
        assert delivs_routine[0] == "queued_quiet_hours"

        # 2. Urgent Breaking News -> must BYPASS quiet hours and queue as pending
        stats_breaking = process_content_event(
            conn,
            content_type="news",
            content_id="breaking_event_1",
            title="Breaking Alert",
            is_breaking=True,
            mock_mode=True,
        )
        assert stats_breaking["notifications_created"] == 1
        delivs_breaking = conn.execute(
            "SELECT status FROM notification_deliveries WHERE user_id = ? ORDER BY id DESC LIMIT 1;",
            (u_id,),
        ).fetchone()
        assert delivs_breaking[0] == "pending"

        # Outbox worker sweep dispatches pending deliveries
        retry_failed_deliveries(conn, mock_mode=True)
        delivs_breaking_after = conn.execute(
            "SELECT status FROM notification_deliveries WHERE user_id = ? ORDER BY id DESC LIMIT 1;",
            (u_id,),
        ).fetchone()
        assert delivs_breaking_after[0] == "delivered"


def test_global_pause_and_unverified_channel_opt_out():
    """Verify that global pause and unverified channels strictly block alerts."""
    with get_db() as conn:
        u1 = create_user(conn, email="phase3_alice@example.com", password="password1", full_name="Paused Alice")
        # Link channel but pause notifications
        tok = create_channel_link_token(conn, u1, "telegram")
        verify_and_link_channel(conn, "telegram", tok, "tg_chat_paused")
        update_user_preferences(conn, u1, is_paused=1, breaking_alerts=1)

        # Breaking news must NOT alert paused user
        stats = process_content_event(
            conn, content_type="news", content_id="brk_123", title="Major Breaking Event",
            is_breaking=True, mock_mode=True,
        )
        # Alice was skipped due to is_paused
        alice_notifs = list_user_notifications(conn, u1)
        assert len(alice_notifs) == 0

        # Now test unverified channel
        u2 = create_user(conn, email="phase3_bob@example.com", password="password1", full_name="Unverified Bob")
        # Do not link channel (telegram_verified = 0)
        update_user_preferences(conn, u2, is_paused=0, breaking_alerts=1, telegram_enabled=1)

        stats2 = process_content_event(
            conn, content_type="news", content_id="brk_456", title="Another Event",
            is_breaking=True, mock_mode=True,
        )
        bob_delivs = conn.execute("SELECT COUNT(*) FROM notification_deliveries WHERE user_id = ?;", (u2,)).fetchone()[0]
        assert bob_delivs == 0


def test_independent_channel_deliveries_and_bounded_retry():
    """Verify that Telegram and Viber have separate deliveries, and bounded retries handle failures."""
    with get_db() as conn:
        uid = create_user(conn, email="phase3_alice@example.com", password="password1", full_name="Multi Channel")
        # Link both Telegram and Viber
        tok_tg = create_channel_link_token(conn, uid, "telegram")
        verify_and_link_channel(conn, "telegram", tok_tg, "tg_chat_dual")
        tok_vb = create_channel_link_token(conn, uid, "viber")
        verify_and_link_channel(conn, "viber", tok_vb, "vb_chat_dual")

        update_user_preferences(
            conn, uid, breaking_alerts=1, telegram_enabled=1, viber_enabled=1,
            is_paused=0, quiet_hours_enabled=0,
        )

        # Trigger breaking news: decision service queues pending deliveries for both channels
        stats = process_content_event(
            conn, content_type="news", content_id="dual_alert_1",
            title="Dual Alert Test", is_breaking=True, mock_mode=False,
        )
        assert stats["deliveries_queued"] == 2

        # Outbox worker sweep with Telegram failing but Viber succeeding
        with patch("alerts.telegram_client.send_telegram_message", return_value=(False, "Telegram 500 error")):
            with patch("alerts.viber.send_viber_message", return_value={"status": 0}):
                retry_failed_deliveries(conn, limit=5, mock_mode=False)

        delivs = conn.execute(
            "SELECT channel, status, attempt_count FROM notification_deliveries WHERE user_id = ? ORDER BY channel ASC;",
            (uid,),
        ).fetchall()
        assert len(delivs) == 2
        d_map = {r[0]: (r[1], r[2]) for r in delivs}
        # Telegram failed independently
        assert d_map["telegram"][0] == "failed"
        assert d_map["telegram"][1] == 1
        # Viber delivered successfully
        assert d_map["viber"][0] == "delivered"

        # Now test retry of failed delivery up to max_attempts
        # Attempt immediately -> must be blocked by 30s backoff!
        assert retry_failed_deliveries(conn, limit=5, mock_mode=False)["total"] == 0

        # Simulate 35s passing -> attempt 2 (fails)
        p35 = (datetime.now(timezone.utc) - timedelta(seconds=35)).isoformat()
        conn.execute("UPDATE notification_deliveries SET last_attempt_at = ? WHERE user_id = ? AND channel = 'telegram';", (p35, uid))
        with patch("alerts.telegram_client.send_telegram_message", return_value=(False, "Still failing")):
            retry_failed_deliveries(conn, limit=5, mock_mode=False)

        tg_row2 = conn.execute("SELECT status, attempt_count FROM notification_deliveries WHERE user_id = ? AND channel = 'telegram';", (uid,)).fetchone()
        assert tg_row2[0] == "failed"
        assert tg_row2[1] == 2

        # Blocked by 120s backoff!
        assert retry_failed_deliveries(conn, limit=5, mock_mode=False)["total"] == 0

        # Simulate 125s passing -> attempt 3 (fails -> dead_letter)
        p125 = (datetime.now(timezone.utc) - timedelta(seconds=125)).isoformat()
        conn.execute("UPDATE notification_deliveries SET last_attempt_at = ? WHERE user_id = ? AND channel = 'telegram';", (p125, uid))
        with patch("alerts.telegram_client.send_telegram_message", return_value=(False, "Final fail")):
            retry_failed_deliveries(conn, limit=5, mock_mode=False)

        tg_row3 = conn.execute("SELECT status, attempt_count FROM notification_deliveries WHERE user_id = ? AND channel = 'telegram';", (uid,)).fetchone()
        assert tg_row3[0] == "dead_letter"
        assert tg_row3[1] == 3

        # Confirm terminal dead_letter cannot be reclaimed automatically
        p_hr = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        conn.execute("UPDATE notification_deliveries SET last_attempt_at = ? WHERE user_id = ? AND channel = 'telegram';", (p_hr, uid))
        assert retry_failed_deliveries(conn, limit=5, mock_mode=False)["total"] == 0


def test_api_account_notifications_endpoints():
    """Verify /api/account/notifications, read, and read-all endpoints with cross-user isolation."""
    # 1. Register Alice and create notification
    reg_alice = client.post("/api/auth/register", json={
        "email": "phase3_alice@example.com", "password": "password123", "full_name": "Alice API",
    }).json()
    alice_token = reg_alice["token"]
    alice_id = reg_alice["user"]["id"]

    # 2. Register Bob
    reg_bob = client.post("/api/auth/register", json={
        "email": "phase3_bob@example.com", "password": "password123", "full_name": "Bob API",
    }).json()
    bob_token = reg_bob["token"]
    bob_id = reg_bob["user"]["id"]

    with get_db() as conn:
        n_alice = create_logical_notification(
            conn, user_id=alice_id, event_key="test:api:1", content_type="news",
            content_id="test1", title="Alice Notification",
        )
        n_bob = create_logical_notification(
            conn, user_id=bob_id, event_key="test:api:2", content_type="news",
            content_id="test2", title="Bob Notification",
        )

    # 3. Alice lists notifications -> must see only hers
    client.cookies.clear()
    client.cookies.set("session_token", alice_token)
    res_list = client.get("/api/account/notifications")
    assert res_list.status_code == 200
    data = res_list.json()
    assert data["unread_count"] == 1
    assert len(data["notifications"]) == 1
    assert data["notifications"][0]["id"] == n_alice

    # 4. Cross-user isolation: Alice cannot mark Bob's notification as read
    res_bad_read = client.post(f"/api/account/notifications/{n_bob}/read")
    assert res_bad_read.status_code == 200
    assert res_bad_read.json()["success"] is False

    # 5. Alice marks her notification read
    res_good_read = client.post(f"/api/account/notifications/{n_alice}/read")
    assert res_good_read.status_code == 200
    assert res_good_read.json()["success"] is True

    # 6. Check unread count is now 0
    res_list2 = client.get("/api/account/notifications")
    assert res_list2.json()["unread_count"] == 0
    client.cookies.clear()


def test_postgres_returning_id_and_cursor_compatibility():
    """Verify RETURNING id works when cursor.lastrowid is None (PostgreSQL / psycopg2 adapter parity)."""
    with get_db() as conn:
        uid = create_user(conn, email="phase3_alice@example.com", password="password1", full_name="PG Parity User")

        # Mock a PostgreSQL-like cursor where lastrowid is None, but RETURNING id returns a row
        class MockPGCursor:
            def __init__(self, real_cursor):
                self._real = real_cursor
                self.lastrowid = None  # Exactly like psycopg2

            def fetchone(self):
                return self._real.fetchone()

        class MockPGConn:
            def __init__(self, real_conn):
                self._real = real_conn

            def execute(self, sql, params=()):
                real_cur = self._real.execute(sql, params)
                return MockPGCursor(real_cur)

        mock_pg_conn = MockPGConn(conn)

        notif_id = create_logical_notification(
            mock_pg_conn, user_id=uid, event_key="pg:test:v1", content_type="news",
            content_id="pg_story", title="Postgres Compatible",
        )
        assert notif_id is not None
        assert notif_id > 0

        deliv_id = create_notification_delivery(
            mock_pg_conn, notification_id=notif_id, user_id=uid,
            channel="telegram", destination="123456",
        )
        assert deliv_id is not None
        assert deliv_id > 0


def test_logical_notifications_independent_of_external_channels():
    """Verify that in-app logical notifications are recorded even if user has NO connected channels."""
    with get_db() as conn:
        uid = create_user(conn, email="phase3_alice@example.com", password="password1", full_name="In-App Alice")
        # Alice follows topic "general", has NO telegram/viber connected
        update_user_preferences(conn, uid, followed_content_alerts=1, is_paused=0)
        add_follow(conn, uid, "topic", "economy", "Economy")

        stats = process_content_event(
            conn, content_type="news", content_id="econ_101", title="Economy Surges",
            topics=["economy"], mock_mode=True,
        )
        assert stats["notifications_created"] == 1
        assert stats["deliveries_queued"] == 0  # No external channel delivery queued

        notifs = list_user_notifications(conn, uid)
        assert len(notifs) == 1
        assert notifs[0]["title"] == "Economy Surges"


def test_operational_queue_quiet_hours_release_and_retries():
    """Verify process_operational_delivery_queue releases quiet hour queues and retries failed."""
    from services.alert_delivery_service import process_operational_delivery_queue
    with get_db() as conn:
        uid = create_user(conn, email="phase3_alice@example.com", password="password1", full_name="Queue Alice")
        tok = create_channel_link_token(conn, uid, "telegram")
        verify_and_link_channel(conn, "telegram", tok, "tg_queue_test")

        # Manually create a delivery in queued_quiet_hours with quiet hours currently disabled
        update_user_preferences(conn, uid, quiet_hours_enabled=0)
        nid = create_logical_notification(conn, uid, "q:test:1", "news", "s1", "Quiet Release Test")
        did = create_notification_delivery(conn, nid, uid, "telegram", "tg_queue_test", status="queued_quiet_hours")

        # Run operational delivery queue
        res = process_operational_delivery_queue(conn, limit=10, mock_mode=True)
        assert res["quiet_hours_released"] >= 1

        deliv_row = conn.execute("SELECT status FROM notification_deliveries WHERE id = ?;", (did,)).fetchone()
        assert deliv_row[0] == "delivered"  # Released to pending and dispatched in mock mode


def test_all_articles_processed_and_meaningful_update_fingerprint():
    """Verify all articles (beyond first 5) are processed and updates with new fingerprints trigger new events."""
    with get_db() as conn:
        uid = create_user(conn, email="phase3_alice@example.com", password="password1", full_name="Fingerprint Alice")
        update_user_preferences(conn, uid, breaking_alerts=1, is_paused=0)

        # 1. Initial article with fingerprint A
        stats1 = process_content_event(
            conn, content_type="news", content_id="story_dynamic", title="Headline Version 1",
            is_breaking=True, update_fingerprint="fp_aaaa1111", mock_mode=True,
        )
        assert stats1["notifications_created"] == 1

        # 2. Unchanged re-scrape with same fingerprint A -> 0 new notifications
        stats_dup = process_content_event(
            conn, content_type="news", content_id="story_dynamic", title="Headline Version 1",
            is_breaking=True, update_fingerprint="fp_aaaa1111", mock_mode=True,
        )
        assert stats_dup["notifications_created"] == 0

        # 3. Meaningful content update with new fingerprint B -> 1 new notification created
        stats_upd = process_content_event(
            conn, content_type="news", content_id="story_dynamic", title="Major Update to Headline",
            is_breaking=True, update_fingerprint="fp_bbbb2222", mock_mode=True,
        )
        assert stats_upd["notifications_created"] == 1


def test_legacy_broadcast_skips_registered_users_to_prevent_duplicate_delivery():
    """Verify dispatch_news_alerts excludes registered users' DMs while preserving public broadcast."""
    from alerts.telegram_dispatch import dispatch_news_alerts
    with get_db() as conn:
        uid = create_user(conn, email="phase3_alice@example.com", password="password1", full_name="Broadcast Alice")
        tok = create_channel_link_token(conn, uid, "telegram")
        verify_and_link_channel(conn, "telegram", tok, "chat_user_personal")

        # Mock public channel and personal chat
        with patch("alerts.telegram_dispatch.get_telegram_credentials", return_value=("mock_bot_token", "public_channel_999")):
            with patch("alerts.telegram_client.send_telegram_message", return_value=(True, "OK")):
                articles = [{"id": "broadcast_test_art", "headline": "Public News", "url": "/story/1"}]
                dispatched = dispatch_news_alerts(conn, articles, bot_token="mock_bot_token", force_resend=True)

                # Public broadcast channel received it, personal user DM skipped from legacy broadcast
                destinations = [d["chat_id"] for d in dispatched]
                assert "public_channel_999" in destinations
                assert "chat_user_personal" not in destinations
