"""
Tests for UI Alignment Phase: Sign-In, Truthful Channel Verification, Following, and In-App Notifications.
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from main import app
from data.database import (
    get_db,
    init_db,
    create_user,
    create_user_session,
    get_user_by_email,
)
from data.repos.notifications import (
    create_logical_notification,
    get_unread_notification_count,
)

client = TestClient(app, follow_redirects=False)


@pytest.fixture(autouse=True)
def clean_ui_test_users():
    """Ensure clean test environment for UI alignment test users."""
    init_db()
    test_emails = [
        "ui_test_user@example.com",
        "ui_test_user_verified@example.com",
    ]
    with get_db() as conn:
        for em in test_emails:
            u = get_user_by_email(conn, em)
            if u:
                conn.execute("DELETE FROM channel_link_tokens WHERE user_id = ?;", (u["id"],))
                conn.execute("DELETE FROM user_notification_preferences WHERE user_id = ?;", (u["id"],))
                conn.execute("DELETE FROM notifications WHERE user_id = ?;", (u["id"],))
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
                conn.execute("DELETE FROM notifications WHERE user_id = ?;", (u["id"],))
                conn.execute("DELETE FROM user_follows WHERE user_id = ?;", (u["id"],))
                conn.execute("DELETE FROM user_sessions WHERE user_id = ?;", (u["id"],))
                conn.execute("DELETE FROM users WHERE id = ?;", (u["id"],))


def test_auth_me_reflects_truthful_channel_verification():
    """Verify that /api/auth/me returns truthful telegram_verified and viber_verified fields."""
    with get_db() as conn:
        uid = create_user(
            conn,
            email="ui_test_user@example.com",
            password="testpassword123",
            full_name="UI Test User",
            telegram_chat_id="tg_12345",
            viber_user_id="vb_67890",
        )
        token = create_user_session(conn, uid)

    res = client.get("/api/auth/me", cookies={"session_token": token})
    assert res.status_code == 200
    data = res.json()
    assert data["user"] is not None
    assert data["user"]["email"] == "ui_test_user@example.com"
    # Even though IDs are entered, verification is false initially
    assert data["user"]["telegram_verified"] is False
    assert data["user"]["viber_verified"] is False

    # Now verify channels directly in database
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET telegram_verified = 1, viber_verified = 1 WHERE id = ?;",
            (uid,),
        )

    res_verified = client.get("/api/auth/me", cookies={"session_token": token})
    assert res_verified.status_code == 200
    data_verified = res_verified.json()
    assert data_verified["user"]["telegram_verified"] is True
    assert data_verified["user"]["viber_verified"] is True


def test_guest_protected_web_routes_redirect():
    """Verify unauthenticated requests to protected pages redirect to /?auth=login&next=..."""
    for path in ["/account", "/following", "/account/alerts", "/account/channels"]:
        res = client.get(path)
        assert res.status_code == 302, f"Expected 302 for unauthenticated {path}"
        location = res.headers.get("location")
        assert location is not None
        assert f"next={path}" in location


def test_authenticated_web_routes_render_ok():
    """Verify authenticated requests to user account pages render 200 with truthful UI."""
    with get_db() as conn:
        uid = create_user(
            conn,
            email="ui_test_user_verified@example.com",
            password="testpassword123",
            full_name="Verified UI User",
        )
        token = create_user_session(conn, uid)

    for path in ["/account", "/following", "/account/alerts", "/account/channels"]:
        res = client.get(path, cookies={"session_token": token})
        assert res.status_code == 200, f"Expected 200 for authenticated {path}"
        assert "Verified UI User" in res.text or "Khulaasaa" in res.text


def test_in_app_notification_endpoints():
    """Verify in-app notification center queries and mark-read actions."""
    # Guest cannot access notifications
    guest_res = client.get("/api/account/notifications")
    assert guest_res.status_code == 401

    with get_db() as conn:
        uid = create_user(
            conn,
            email="ui_test_user@example.com",
            password="testpassword123",
            full_name="UI Notif User",
        )
        token = create_user_session(conn, uid)

        # Initially 0 unread notifications
        assert get_unread_notification_count(conn, uid) == 0

        # Create two logical notifications
        n1 = create_logical_notification(
            conn,
            user_id=uid,
            event_key="evt_test_1",
            content_type="news",
            content_id="story_101",
            title="President Addresses Parliament",
            summary="Key legislative announcements made today.",
            url="/story/story_101",
        )
        n2 = create_logical_notification(
            conn,
            user_id=uid,
            event_key="evt_test_2",
            content_type="tender",
            content_id="tender_202",
            title="Major Port Development RFP Issued",
            summary="Submission deadline in 30 days.",
            url="/bids/tender_202",
        )

    # Fetch notifications via API
    res = client.get("/api/account/notifications", cookies={"session_token": token})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["unread_count"] == 2
    assert len(data["notifications"]) == 2

    # Mark first notification as read
    read_res = client.post(f"/api/account/notifications/{n1}/read", cookies={"session_token": token})
    assert read_res.status_code == 200
    assert read_res.json()["success"] is True

    # Verify unread count is now 1
    res2 = client.get("/api/account/notifications", cookies={"session_token": token})
    assert res2.json()["unread_count"] == 1

    # Mark all remaining notifications as read
    read_all_res = client.post("/api/account/notifications/read-all", cookies={"session_token": token})
    assert read_all_res.status_code == 200
    assert read_all_res.json()["marked_read"] == 1

    # Verify unread count is now 0
    res3 = client.get("/api/account/notifications", cookies={"session_token": token})
    assert res3.json()["unread_count"] == 0


def test_follow_unfollow_and_guest_interception():
    """Verify follow and unfollow API behaviors for stories and topics."""
    # Guest follow attempt fails with 401
    guest_res = client.post(
        "/api/follows",
        json={"target_type": "topic", "target_id": "economy", "target_title": "Economy"},
    )
    assert guest_res.status_code == 401

    with get_db() as conn:
        uid = create_user(
            conn,
            email="ui_test_user@example.com",
            password="testpassword123",
            full_name="UI Follow User",
        )
        token = create_user_session(conn, uid)

    # Authenticated user follows topic
    post_res = client.post(
        "/api/follows",
        json={"target_type": "topic", "target_id": "economy", "target_title": "Economy"},
        cookies={"session_token": token},
    )
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "ok"

    # Authenticated user follows story
    post_story_res = client.post(
        "/api/follows",
        json={"target_type": "story", "target_id": "cluster-1", "target_title": "Fisheries Development Policy"},
        cookies={"session_token": token},
    )
    assert post_story_res.status_code == 200

    # List follows
    list_res = client.get("/api/follows", cookies={"session_token": token})
    assert list_res.status_code == 200
    follows = list_res.json()["follows"]
    assert len(follows) == 2
    types = {f["target_type"] for f in follows}
    assert types == {"topic", "story"}

    # Unfollow topic
    del_res = client.delete(
        "/api/follows?target_type=topic&target_id=economy",
        cookies={"session_token": token},
    )
    assert del_res.status_code == 200

    # Remaining follows
    list_res2 = client.get("/api/follows", cookies={"session_token": token})
    assert len(list_res2.json()["follows"]) == 1
    assert list_res2.json()["follows"][0]["target_type"] == "story"
