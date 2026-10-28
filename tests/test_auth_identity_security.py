"""Security tests for provider-backed authentication payload validation."""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode

from services.provider_auth_service import validate_telegram_webapp_init_data
from data.database import create_user, get_db, get_platform_identity, get_platform_identity_stats, init_db, link_platform_identity, upsert_platform_identity


def _signed_init_data(bot_token: str, user: dict, auth_date: int | None = None) -> str:
    fields = {
        "auth_date": str(auth_date or int(time.time())),
        "user": json.dumps(user, separators=(",", ":")),
        "query_id": "AAE-test-query",
    }
    check_string = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)


def test_telegram_init_data_accepts_valid_signature():
    user = {"id": 987654321, "first_name": "Test"}
    payload = _signed_init_data("test-bot-token", user)
    assert validate_telegram_webapp_init_data(payload, "test-bot-token") == user


def test_telegram_init_data_rejects_tampered_payload():
    payload = _signed_init_data("test-bot-token", {"id": 987654321})
    tampered = payload.replace("987654321", "987654322")
    assert _validate_telegram_webapp_init_data(tampered, "test-bot-token") is None


def test_telegram_init_data_rejects_stale_signature():
    stale_date = int(time.time()) - 86401
    payload = _signed_init_data("test-bot-token", {"id": 987654321}, stale_date)
    assert _validate_telegram_webapp_init_data(payload, "test-bot-token") is None


def test_platform_identity_upsert_is_idempotent_and_tracks_last_seen(tmp_path: Path):
    db_path = tmp_path / "identity-upsert.db"
    init_db(db_path)
    with get_db(db_path) as conn:
        first = upsert_platform_identity(conn, "telegram", "test-tg-identity-1", provider_username="reader_one", display_name="Reader One")
        second = upsert_platform_identity(conn, "telegram", "test-tg-identity-1", provider_username="reader_one", display_name="Reader One Updated")
        count = conn.execute("SELECT COUNT(*) FROM user_identities WHERE provider = ? AND provider_user_id = ?;", ("telegram", "test-tg-identity-1")).fetchone()[0]
        assert first["id"] == second["id"]
        assert second["display_name"] == "Reader One Updated"
        assert count == 1


def test_platform_identity_cannot_be_linked_to_two_people(tmp_path: Path):
    db_path = tmp_path / "identity-owner.db"
    init_db(db_path)
    with get_db(db_path) as conn:
        user_a = create_user(conn, "identity_a@example.test", "password123", "Identity A")
        user_b = create_user(conn, "identity_b@example.test", "password123", "Identity B")
        upsert_platform_identity(conn, "viber", "test-viber-identity-1", display_name="Viber Reader")
        ok_a, _ = link_platform_identity(conn, "viber", "test-viber-identity-1", user_a)
        ok_b, message = link_platform_identity(conn, "viber", "test-viber-identity-1", user_b)
        assert ok_a is True
        assert ok_b is False
        assert "already linked" in message.lower()
        identity = get_platform_identity(conn, "viber", "test-viber-identity-1")
        assert identity["user_id"] == user_a


def test_identity_stats_distinguish_linked_people_from_raw_channel_ids(tmp_path: Path):
    db_path = tmp_path / "identity-stats.db"
    init_db(db_path)
    with get_db(db_path) as conn:
        user = create_user(conn, "identity_stats@example.test", "password123", "Identity Stats")
        upsert_platform_identity(conn, "telegram", "test-stats-tg", user_id=user, verified=True)
        upsert_platform_identity(conn, "viber", "test-stats-viber", user_id=user, verified=True)
        upsert_platform_identity(conn, "telegram", "test-stats-unlinked")
        stats = get_platform_identity_stats(conn)
        assert stats["telegram_identities"] >= 2
        assert stats["viber_identities"] >= 1
        assert stats["people_with_multiple_linked_channels"] >= 1
        assert stats["unlinked_telegram_identities"] >= 1



def test_hooks85_transient_session_failure_is_briefly_cached(monkeypatch):
    from urllib.error import URLError
    from services import hooks85_service

    calls = []

    def offline_urlopen(request, timeout):
        calls.append(request.full_url)
        raise URLError("gateway offline")

    hooks85_service._SESSION_CACHE.clear()
    monkeypatch.setattr(hooks85_service.urllib.request, "urlopen", offline_urlopen)
    assert hooks85_service.verify_hooks85_session("offline-session-token") is None
    assert hooks85_service.verify_hooks85_session("offline-session-token") is None
    assert len(calls) == 1
    hooks85_service._SESSION_CACHE.clear()



def test_duplicate_registration_returns_conflict_not_existing_account_session(monkeypatch):
    from fastapi.testclient import TestClient
    from main import app
    from routers import api_auth as auth_module

    init_db()
    monkeypatch.setattr(auth_module, "register_via_hooks85", lambda *args: None)
    email = f"identity-register-{secrets.token_hex(6)}@example.test"
    client = TestClient(app)
    payload = {"email": email, "password": "password123", "full_name": "Registration Test"}

    first = client.post("/api/auth/register", json=payload)
    assert first.status_code == 200
    second = client.post("/api/auth/register", json=payload)
    assert second.status_code == 409
    assert "token" not in second.json()

    with get_db() as conn:
        user = conn.execute("SELECT id FROM users WHERE email = ?;", (email,)).fetchone()
        assert user is not None
        conn.execute("DELETE FROM user_sessions WHERE user_id = ?;", (user["id"],))
        conn.execute("DELETE FROM users WHERE id = ?;", (user["id"],))
