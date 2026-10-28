"""Provider authentication verification helpers."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, Optional
from urllib.parse import parse_qsl


def validate_telegram_webapp_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = 86400,
) -> Optional[dict[str, Any]]:
    """Validate Telegram Mini App initData using Telegram's documented HMAC scheme."""
    if not init_data or not bot_token:
        return None

    fields = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = fields.pop("hash", "")
    if not received_hash:
        return None

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(fields.items())
    )
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        return None

    try:
        auth_date = int(fields.get("auth_date", "0"))
    except (TypeError, ValueError):
        return None

    now = int(time.time())
    if auth_date <= 0 or now - auth_date > max_age_seconds or auth_date > now + 60:
        return None

    try:
        user_data = json.loads(fields.get("user") or "{}")
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(user_data, dict) or not user_data.get("id"):
        return None
    return user_data
