"""Security tests for provider-backed authentication payload validation."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from routers.api_auth import _validate_telegram_webapp_init_data


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
    assert _validate_telegram_webapp_init_data(payload, "test-bot-token") == user


def test_telegram_init_data_rejects_tampered_payload():
    payload = _signed_init_data("test-bot-token", {"id": 987654321})
    tampered = payload.replace("987654321", "987654322")
    assert _validate_telegram_webapp_init_data(tampered, "test-bot-token") is None


def test_telegram_init_data_rejects_stale_signature():
    stale_date = int(time.time()) - 86401
    payload = _signed_init_data("test-bot-token", {"id": 987654321}, stale_date)
    assert _validate_telegram_webapp_init_data(payload, "test-bot-token") is None
