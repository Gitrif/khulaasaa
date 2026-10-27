"""
Comprehensive Unit & Integration Tests for Notification Preferences and Truthful Channel Linking.
Phase 2 Verification Suite.
"""
from datetime import datetime, timedelta, timezone
import pytest
from starlette.testclient import TestClient

from main import app
from data.database import (
    get_db,
    init_db,
    create_user,
    get_user_by_email,
    get_user_preferences,
    update_user_preferences,
)
from services.channel_linking_service import (
    create_channel_link_token,
    verify_and_link_channel,
    disconnect_channel,
    get_channel_connection_status,
)
from alerts.telegram_bot import handle_incoming_telegram_update
from alerts.viber import handle_viber_webhook_event

client = TestClient(app, follow_redirects=False)


@pytest.fixture(autouse=True)
def clean_test_users():
    """Ensure clean test environment."""
    init_db()
    test_emails = [
        "phase2_user_a@example.com",
        "phase2_user_b@example.com",
    ]
    with get_db() as conn:
        for em in test_emails:
            u = get_user_by_email(conn, em)
            if u:
                conn.execute("DELETE FROM channel_link_tokens WHERE user_id = ?;", (u["id"],))
                conn.execute("DELETE FROM user_notification_preferences WHERE user_id = ?;", (u["id"],))
                conn.execute("DELETE FROM user_follows WHERE user_id = ?;", (u["id"],))
                conn.execute("DELETE FROM user_sessions WHERE user_id = ?;", (u["id"],))
                conn.execute("DELETE FROM users WHERE id = ?;", (u["id"],))
    yield
    with get_db() as conn:
        for em in test_emails:
            u = get_user_by_email(conn, em)
            if u:
                conn.execute("DELETE FROM channel_link_tokens WHERE user_id = ?;", (u["id"],))
                conn.execute("DELETE FROM user_notification_preferences WHERE user_id = ?;", (u["id"],))
                conn.execute("DELETE FROM user_follows WHERE user_id = ?;", (u["id"],))
                conn.execute("DELETE FROM user_sessions WHERE user_id = ?;", (u["id"],))
                conn.execute("DELETE FROM users WHERE id = ?;", (u["id"],))


def test_notification_preferences_crud_and_validation():
    """Test preference lazy initialization, updates, and strict validation."""
    with get_db() as conn:
        u_id = create_user(conn, email="phase2_user_a@example.com", password="password123", full_name="Pref Tester")

        # 1. Lazy initialization creates defaults
        p0 = get_user_preferences(conn, u_id)
        assert p0["breaking_alerts"] is True
        assert p0["followed_content_alerts"] is True
        assert p0["frequency"] == "instant"
        assert p0["quiet_hours_enabled"] is False
        assert p0["is_paused"] is False

        # 2. Update valid fields
        p1 = update_user_preferences(
            conn,
            u_id,
            frequency="digest",
            quiet_hours_enabled=True,
            quiet_hours_start="22:30",
            quiet_hours_end="06:30",
            is_paused=True,
        )
        assert p1["frequency"] == "digest"
        assert p1["quiet_hours_enabled"] is True
        assert p1["quiet_hours_start"] == "22:30"
        assert p1["quiet_hours_end"] == "06:30"
        assert p1["is_paused"] is True

        # 3. Validation: invalid frequency raises ValueError
        with pytest.raises(ValueError, match="frequency"):
            update_user_preferences(conn, u_id, frequency="invalid_cadence")

        # 4. Validation: invalid time format raises ValueError
        with pytest.raises(ValueError, match="HH:MM"):
            update_user_preferences(conn, u_id, quiet_hours_start="25:00")
        with pytest.raises(ValueError, match="HH:MM"):
            update_user_preferences(conn, u_id, quiet_hours_end="bad_time")


def test_preferences_api_endpoints():
    """Test GET and PUT /api/account/preferences endpoints with auth enforcement."""
    # 1. Unauthenticated request rejected
    client.cookies.clear()
    res_unauth = client.get("/api/account/preferences")
    assert res_unauth.status_code == 401

    # 2. Authenticated user retrieves preferences
    reg = client.post("/api/auth/register", json={
        "email": "phase2_user_a@example.com",
        "password": "password123",
        "full_name": "API Pref User",
    }).json()
    token = reg["token"]
    client.cookies.set("session_token", token)

    res_get = client.get("/api/account/preferences")
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["status"] == "ok"
    assert "preferences" in data
    assert "channels" in data
    assert data["preferences"]["frequency"] == "instant"

    # 3. Update via PUT
    res_put = client.put("/api/account/preferences", json={
        "frequency": "digest",
        "telegram_enabled": 0,
        "quiet_hours_enabled": 1,
        "quiet_hours_start": "23:15",
        "quiet_hours_end": "07:45",
    })
    assert res_put.status_code == 200
    p_updated = res_put.json()["preferences"]
    assert p_updated["frequency"] == "digest"
    assert p_updated["telegram_enabled"] is False
    assert p_updated["quiet_hours_start"] == "23:15"


def test_channel_link_token_lifecycle_and_single_use():
    """Verify link token generation, deep link format, expiration, and replay prevention."""
    with get_db() as conn:
        u_id = create_user(conn, email="phase2_user_a@example.com", password="password123", full_name="Token Tester")

        # 1. Generate Telegram token
        tg_token = create_channel_link_token(conn, u_id, "telegram", ttl_minutes=15)
        assert tg_token
        # Verify in DB
        row = conn.execute("SELECT user_id, expires_at FROM channel_link_tokens WHERE token = ?;", (tg_token,)).fetchone()
        assert row is not None
        assert row["user_id"] == u_id

        # 2. Verify channel linking
        ok, msg, uid = verify_and_link_channel(conn, "telegram", tg_token, "tg_chat_998877", "tg_handle")
        assert ok is True
        assert uid == u_id

        # Channel connection status should now be truthful
        status = get_channel_connection_status(conn, u_id)
        assert status["telegram"]["connected"] is True
        assert status["telegram"]["chat_id"] == "tg_chat_998877"
        assert status["telegram"]["verified"] is True

        # 3. Single-use: Replay attempt with same token must fail
        ok_replay, msg_replay, _ = verify_and_link_channel(conn, "telegram", tg_token, "tg_chat_998877")
        assert ok_replay is False
        assert "Invalid or unrecognized" in msg_replay


def test_channel_token_expiration():
    """Verify that expired tokens fail verification."""
    with get_db() as conn:
        u_id = create_user(conn, email="phase2_user_a@example.com", password="password123", full_name="Exp Tester")
        tok = "expired_token_123"
        # Insert token already expired 5 minutes ago
        past_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        conn.execute(
            "INSERT INTO channel_link_tokens (token, user_id, channel, expires_at) VALUES (?, ?, ?, ?);",
            (tok, u_id, "telegram", past_time),
        )

        ok, msg, _ = verify_and_link_channel(conn, "telegram", tok, "tg_chat_000")
        assert ok is False
        assert "expired" in msg.lower()


def test_channel_ownership_and_conflict_transfer():
    """Verify that linking a channel already claimed by User A unlinks A and assigns to User B."""
    with get_db() as conn:
        u1 = create_user(conn, email="phase2_user_a@example.com", password="password1", full_name="User One")
        u2 = create_user(conn, email="phase2_user_b@example.com", password="password2", full_name="User Two")

        # User One claims chat_id 55555
        tok1 = create_channel_link_token(conn, u1, "telegram")
        verify_and_link_channel(conn, "telegram", tok1, "chat_55555")

        status1 = get_channel_connection_status(conn, u1)
        assert status1["telegram"]["connected"] is True
        assert status1["telegram"]["chat_id"] == "chat_55555"

        # Now User Two connects with the same chat_id 55555
        tok2 = create_channel_link_token(conn, u2, "telegram")
        ok, msg, _ = verify_and_link_channel(conn, "telegram", tok2, "chat_55555")
        assert ok is True

        # User Two now owns chat_55555
        status2 = get_channel_connection_status(conn, u2)
        assert status2["telegram"]["connected"] is True
        assert status2["telegram"]["chat_id"] == "chat_55555"

        # User One must be unlinked
        status1_after = get_channel_connection_status(conn, u1)
        assert status1_after["telegram"]["connected"] is False
        assert status1_after["telegram"]["chat_id"] is None


def test_channel_disconnection():
    """Verify clean channel disconnection."""
    with get_db() as conn:
        uid = create_user(conn, email="phase2_user_a@example.com", password="password1", full_name="Disc Tester")
        tok = create_channel_link_token(conn, uid, "viber")
        verify_and_link_channel(conn, "viber", tok, "viber_id_777")

        assert get_channel_connection_status(conn, uid)["viber"]["connected"] is True

        # Disconnect
        disc_ok = disconnect_channel(conn, uid, "viber")
        assert disc_ok is True

        status_after = get_channel_connection_status(conn, uid)
        assert status_after["viber"]["connected"] is False
        assert status_after["viber"]["user_id"] is None


def test_bot_webhook_deep_link_and_pin_handlers():
    """Test actual Telegram bot /start link_TOKEN update and Viber PIN message handling."""
    with get_db() as conn:
        uid = create_user(conn, email="phase2_user_a@example.com", password="password1", full_name="Bot Link Tester")
        tg_tok = create_channel_link_token(conn, uid, "telegram")
        vb_pin = create_channel_link_token(conn, uid, "viber")

    # 1. Telegram /start link_TOKEN update
    tg_update = {
        "update_id": 10001,
        "message": {
            "message_id": 501,
            "chat": {"id": 123456789},
            "from": {"first_name": "TestBotUser", "username": "test_bot_user"},
            "text": f"/start link_{tg_tok}",
        },
    }
    handle_incoming_telegram_update(tg_update)

    with get_db() as conn:
        status_tg = get_channel_connection_status(conn, uid)
        assert status_tg["telegram"]["connected"] is True
        assert status_tg["telegram"]["chat_id"] == "123456789"

    # 2. Viber link PIN message
    vb_event = {
        "event": "message",
        "sender": {"id": "viber_chat_9876", "name": "ViberTester"},
        "message": {"text": f"link {vb_pin}"},
    }
    vb_res = handle_viber_webhook_event(vb_event)
    assert vb_res.get("status") == 0

    with get_db() as conn:
        status_vb = get_channel_connection_status(conn, uid)
        assert status_vb["viber"]["connected"] is True
        assert status_vb["viber"]["user_id"] == "viber_chat_9876"


def test_web_routes_account_alerts_and_channels():
    """Verify web views for /account/alerts and /account/channels."""
    # Guest redirected
    client.cookies.clear()
    assert client.get("/account/alerts").status_code == 302
    assert client.get("/account/channels").status_code == 302

    # Authenticated user
    reg = client.post("/api/auth/register", json={
        "email": "phase2_user_a@example.com",
        "password": "password123",
        "full_name": "Web Channel User",
    }).json()
    client.cookies.set("session_token", reg["token"])

    # Load /account/alerts
    res_alerts = client.get("/account/alerts")
    assert res_alerts.status_code == 200
    assert "Notification Preferences" in res_alerts.text
    assert "Breaking News Alerts" in res_alerts.text
    assert "Delivery Cadence" in res_alerts.text
    assert "Quiet Hours" in res_alerts.text

    # Load /account/channels
    res_channels = client.get("/account/channels")
    assert res_channels.status_code == 200
    assert "Connected Alert Channels" in res_channels.text
    assert "Telegram Channel" in res_channels.text
    assert "Viber Channel" in res_channels.text
    assert "NOT CONNECTED" in res_channels.text
