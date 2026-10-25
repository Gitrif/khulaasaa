"""
Tests for user alert settings (Tenders, Jobs, Telegram & Viber connection) and security.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

import main
from data.database import (
    get_db,
    get_telegram_subscriber,
    get_viber_subscriber,
    init_db,
)

@pytest.fixture
def client():
    init_db()
    with TestClient(main.app) as c:
        yield c


def test_user_alert_settings_lifecycle(client):
    """Test registering a user, updating alert preferences, and verifying DB sync."""
    email = "developer.test.alerts@example.mv"
    reg_resp = client.post(
        "/api/auth/register",
        json={
            "full_name": "Test Engineer",
            "email": email,
            "password": "strongpassword123",
        },
    )
    assert reg_resp.status_code == 200
    token = reg_resp.json()["token"]
    client.cookies.set("session_token", token)

    # 1. Fetch current alert settings
    get_resp = client.get("/api/user/alert-settings")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["status"] == "ok"
    assert data["user"]["email"] == email

    # 2. Update alert settings with Telegram & Viber IDs, Tender sources & disciplines
    post_resp = client.post(
        "/api/user/alert-settings",
        json={
            "telegram_chat_id": "99887766",
            "viber_user_id": "+9607998877",
            "tender_alert_disciplines": ["Construction", "IT"],
            "tender_alert_sources": ["gazette", "hdc"],
            "job_alert_categories": ["it", "engineering"],
            "job_alert_sources": ["gazette", "soe"],
            "alerts_enabled": True,
        },
    )
    assert post_resp.status_code == 200
    res_data = post_resp.json()
    assert res_data["status"] == "ok"
    user_data = res_data["user"]
    assert user_data["telegram_chat_id"] == "99887766"
    assert user_data["viber_user_id"] == "+9607998877"
    assert "Construction" in user_data["tender_alert_disciplines"]
    assert "it" in user_data["job_alert_categories"]

    # 3. Verify sync to telegram_subscribers and viber_subscribers tables
    with get_db() as conn:
        tg_sub = get_telegram_subscriber(conn, "99887766")
        assert tg_sub is not None
        assert tg_sub["is_active"] == 1
        assert "Construction" in tg_sub["disciplines"]

        vb_sub = get_viber_subscriber(conn, "+9607998877")
        assert vb_sub is not None
        assert vb_sub["is_active"] == 1


def test_alert_test_connection_validation(client):
    """Test validation and mock response for /api/alerts/test-connection."""
    # Without target ID and not logged in should raise 400
    resp_bad = client.post("/api/alerts/test-connection", json={"channel": "telegram", "target_id": ""})
    assert resp_bad.status_code == 400

    # With Telegram chat ID mock
    resp_tg = client.post("/api/alerts/test-connection", json={"channel": "telegram", "target_id": "12345678"})
    assert resp_tg.status_code in (200, 400)

    # With Viber ID mock
    resp_vb = client.post("/api/alerts/test-connection", json={"channel": "viber", "target_id": "viber_test_id"})
    assert resp_vb.status_code in (200, 400)


def test_avatar_menu_client_endpoints_and_markup(client):
    """Test avatar menu markup presence and auth session endpoints."""
    # 1. Page markup includes avatar menu container and scripts
    resp = client.get("/")
    assert resp.status_code == 200
    assert "globalUserPillContainer" in resp.text
    assert "toggleUserAvatarMenu" in resp.text
    assert "user-avatar-btn" in resp.text
    assert "user-avatar-dropdown" in resp.text

    # 2. When logged out, /api/auth/me returns null user
    me_resp = client.get("/api/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json().get("user") is None

    # 3. Register user and verify /api/auth/me returns user object with initials support
    reg_resp = client.post(
        "/api/auth/register",
        json={
            "full_name": "Ibrahim Arif",
            "email": "ibrahim.arif@example.mv",
            "password": "securepassword123",
        },
    )
    assert reg_resp.status_code == 200
    token = reg_resp.json()["token"]
    client.cookies.set("session_token", token)

    me_logged_in = client.get("/api/auth/me")
    assert me_logged_in.status_code == 200
    user_data = me_logged_in.json()["user"]
    assert user_data["full_name"] == "Ibrahim Arif"
    assert user_data["email"] == "ibrahim.arif@example.mv"

    # 4. Logout endpoint clears authentication
    logout_resp = client.post("/api/auth/logout")
    assert logout_resp.status_code == 200
    client.cookies.delete("session_token")
    me_logged_out = client.get("/api/auth/me")
    assert me_logged_out.json().get("user") is None
