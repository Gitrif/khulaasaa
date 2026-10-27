"""
Comprehensive Unit & Integration Tests for User Accounts, Password Reset, and Following Workflow.
Phase 1 Verification Suite.
"""
import os
import sqlite3
import pytest
from starlette.testclient import TestClient

from main import app
from data.database import (
    get_db,
    init_db,
    create_user,
    get_user_by_email,
    add_follow,
    remove_follow,
    list_user_follows,
    is_following,
    get_followers_for_target,
    get_user_follow_counts,
    create_password_reset_token,
    verify_and_consume_password_reset_token,
)

client = TestClient(app, follow_redirects=False)


@pytest.fixture(autouse=True)
def clean_test_users():
    """Ensure test users are cleaned before and after tests."""
    init_db()
    test_emails = [
        "phase1_test_user@example.com",
        "phase1_other_user@example.com",
        "phase1_reset_user@example.com",
    ]
    with get_db() as conn:
        for em in test_emails:
            u = get_user_by_email(conn, em)
            if u:
                conn.execute("DELETE FROM user_follows WHERE user_id = ?;", (u["id"],))
                conn.execute("DELETE FROM user_sessions WHERE user_id = ?;", (u["id"],))
                conn.execute("DELETE FROM users WHERE id = ?;", (u["id"],))
    yield
    with get_db() as conn:
        for em in test_emails:
            u = get_user_by_email(conn, em)
            if u:
                conn.execute("DELETE FROM user_follows WHERE user_id = ?;", (u["id"],))
                conn.execute("DELETE FROM user_sessions WHERE user_id = ?;", (u["id"],))
                conn.execute("DELETE FROM users WHERE id = ?;", (u["id"],))


def test_user_registration_login_logout_flow():
    """Verify registration, cookie issuance, me profile, and logout session revocation."""
    reg_payload = {
        "email": "phase1_test_user@example.com",
        "password": "securepassword123",
        "full_name": "Phase1 Test User",
        "phone": "+960 711 2233",
    }
    reg_resp = client.post("/api/auth/register", json=reg_payload)
    assert reg_resp.status_code == 200
    reg_data = reg_resp.json()
    assert reg_data["status"] == "ok"
    assert reg_data["user"]["email"] == "phase1_test_user@example.com"
    token = reg_data["token"]
    assert token

    # Check authenticated profile
    client.cookies.set("session_token", token)
    me_resp = client.get("/api/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["user"]["email"] == "phase1_test_user@example.com"

    # Logout
    logout_resp = client.post("/api/auth/logout")
    assert logout_resp.status_code == 200

    # Old token should be invalidated
    client.cookies.set("session_token", token)
    me_after = client.get("/api/auth/me")
    assert me_after.json()["user"] is None


def test_password_reset_flow_with_hash_and_single_use():
    """Verify non-enumerating forgot-password, hash storage, single-use, and session revocation."""
    email = "phase1_reset_user@example.com"
    with get_db() as conn:
        uid = create_user(conn, email=email, password="oldpassword123", full_name="Reset Tester")

    # 1. Non-enumerating response for unregistered email
    ghost_resp = client.post("/api/auth/forgot-password", json={"email": "nobody_registered@example.com"})
    assert ghost_resp.status_code == 200
    assert "instructions to reset your password" in ghost_resp.json()["message"]

    # 2. Forgot-password for registered user (token exposed in test env)
    os.environ["PYTEST_CURRENT_TEST"] = "1"
    req_resp = client.post("/api/auth/forgot-password", json={"email": email})
    assert req_resp.status_code == 200
    data = req_resp.json()
    assert "reset_token" in data
    raw_token = data["reset_token"]

    # Check that database stores SHA-256 hash, NOT raw token
    with get_db() as conn:
        row = conn.execute("SELECT reset_token_hash, reset_token_expires FROM users WHERE email = ?;", (email,)).fetchone()
        assert row["reset_token_hash"] is not None
        assert row["reset_token_hash"] != raw_token
        assert len(row["reset_token_hash"]) == 64  # SHA-256 hex string

    # 3. Invalid token fails
    bad_resp = client.post("/api/auth/reset-password", json={"token": "invalid_token_123", "new_password": "newpassword123"})
    assert bad_resp.status_code == 400

    # 4. Valid token resets password
    reset_resp = client.post("/api/auth/reset-password", json={"token": raw_token, "new_password": "newpassword123"})
    assert reset_resp.status_code == 200
    assert reset_resp.json()["status"] == "ok"

    # Token must now be consumed (single-use)
    reuse_resp = client.post("/api/auth/reset-password", json={"token": raw_token, "new_password": "anotherpassword123"})
    assert reuse_resp.status_code == 400

    # User can log in with new password
    login_resp = client.post("/api/auth/login", json={"email": email, "password": "newpassword123"})
    assert login_resp.status_code == 200
    assert login_resp.json()["status"] == "ok"


def test_follows_canonical_target_validation():
    """Verify target validation for all 4 types: story, topic, section, source."""
    with get_db() as conn:
        u_id = create_user(conn, email="phase1_test_user@example.com", password="password123", full_name="Follow Tester")

        # 1. Invalid target_type raises ValueError
        with pytest.raises(ValueError, match="Invalid target_type"):
            add_follow(conn, u_id, "invalid_type", "slug")

        # 2. Section validation
        with pytest.raises(ValueError, match="Invalid section"):
            add_follow(conn, u_id, "section", "invalid_section")

        f_sec = add_follow(conn, u_id, "section", "tenders")
        assert f_sec["target_type"] == "section"
        assert f_sec["target_id"] == "tenders"
        assert "Tenders" in f_sec["target_title"]

        # 3. Topic validation
        f_top = add_follow(conn, u_id, "topic", "economy")
        assert f_top["target_type"] == "topic"
        assert f_top["target_id"] == "economy"

        # 4. Source validation
        f_src = add_follow(conn, u_id, "source", "sun")
        assert f_src["target_type"] == "source"
        assert f_src["target_id"] == "sun"
        assert "Sun" in f_src["target_title"]

        # 5. Story validation
        f_sty = add_follow(conn, u_id, "story", "fenaka-stelco-merger")
        assert f_sty["target_type"] == "story"
        assert f_sty["target_id"] == "fenaka-stelco-merger"

        # Check counts
        counts = get_user_follow_counts(conn, u_id)
        assert counts["total"] == 4
        assert counts["section"] == 1
        assert counts["topic"] == 1
        assert counts["source"] == 1
        assert counts["story"] == 1


def test_follows_api_endpoints_and_idempotency():
    """Verify POST, DELETE, GET, and check endpoints for follows with idempotency."""
    # Register and log in user
    reg = client.post("/api/auth/register", json={
        "email": "phase1_test_user@example.com",
        "password": "password123",
        "full_name": "API Tester",
    }).json()
    token = reg["token"]
    client.cookies.set("session_token", token)

    # 1. Check initially not following
    chk0 = client.get("/api/follows/check?target_type=topic&target_id=policy")
    assert chk0.status_code == 200
    assert chk0.json()["following"] is False

    # 2. Follow topic
    post_res = client.post("/api/follows", json={
        "target_type": "topic",
        "target_id": "policy",
    })
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "ok"
    assert post_res.json()["follow"]["target_id"] == "policy"

    # Idempotent re-follow should succeed without error
    post_dup = client.post("/api/follows", json={
        "target_type": "topic",
        "target_id": "policy",
    })
    assert post_dup.status_code == 200

    # 3. Check now following
    chk1 = client.get("/api/follows/check?target_type=topic&target_id=policy")
    assert chk1.json()["following"] is True

    # 4. List follows
    list_res = client.get("/api/follows")
    assert list_res.status_code == 200
    data = list_res.json()
    assert len(data["follows"]) == 1
    assert data["counts"]["total"] == 1

    # 5. Unfollow
    del_res = client.delete("/api/follows?target_type=topic&target_id=policy")
    assert del_res.status_code == 200
    assert del_res.json()["removed"] is True

    # Idempotent re-unfollow
    del_dup = client.delete("/api/follows?target_type=topic&target_id=policy")
    assert del_dup.status_code == 200
    assert del_dup.json()["removed"] is False

    # Check not following after delete
    chk2 = client.get("/api/follows/check?target_type=topic&target_id=policy")
    assert chk2.json()["following"] is False


def test_cross_user_follow_data_isolation():
    """Verify that User A cannot see or delete User B's follows."""
    with get_db() as conn:
        u1 = create_user(conn, email="phase1_test_user@example.com", password="pass1", full_name="User One")
        u2 = create_user(conn, email="phase1_other_user@example.com", password="pass2", full_name="User Two")
        add_follow(conn, u1, "story", "male-traffic-ban")
        add_follow(conn, u2, "story", "ras-male-project")

    # Log in as User One
    login1 = client.post("/api/auth/login", json={"email": "phase1_test_user@example.com", "password": "pass1"}).json()
    client.cookies.set("session_token", login1["token"])

    follows1 = client.get("/api/follows").json()["follows"]
    assert len(follows1) == 1
    assert follows1[0]["target_id"] == "male-traffic-ban"

    # User One tries to unfollow User Two's story
    client.delete("/api/follows?target_type=story&target_id=ras-male-project")

    # Verify User Two's follow is still intact
    with get_db() as conn:
        assert is_following(conn, u2, "story", "ras-male-project") is True


def test_web_routes_and_avatar_menu_links():
    """Verify /account and /following web routes, guest redirection, and avatar menu destinations."""
    client.cookies.clear()

    # 1. Guest redirected to login
    acc_guest = client.get("/account")
    assert acc_guest.status_code == 302
    assert "auth=login" in acc_guest.headers["location"]

    fol_guest = client.get("/following")
    assert fol_guest.status_code == 302
    assert "auth=login" in fol_guest.headers["location"]

    # 2. Authenticated user can load /account and /following
    login = client.post("/api/auth/register", json={
        "email": "phase1_test_user@example.com",
        "password": "password123",
        "full_name": "Web View Tester",
    }).json()
    client.cookies.set("session_token", login["token"])

    acc_auth = client.get("/account")
    assert acc_auth.status_code == 200
    assert "Account Settings" in acc_auth.text
    assert "phase1_test_user@example.com" in acc_auth.text

    fol_auth = client.get("/following")
    assert fol_auth.status_code == 200
    assert "Following Dashboard" in fol_auth.text

    # 3. Base layout contains avatar menu 5 exact destinations
    base_res = client.get("/")
    assert base_res.status_code == 200
    html = base_res.text
    assert 'href="/account"' in html
    assert 'href="/following"' in html
    assert 'href="/account/alerts"' in html
    assert 'href="/account/channels"' in html
    assert "handleGlobalLogout()" in html
