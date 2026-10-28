"""
Channel Linking and Truthful Provider Verification Engine for Khulaasaa.
Handles secure, expiring, single-use linking tokens, deep linking, callback verification, and disconnects.
"""
from __future__ import annotations

import logging
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from alerts.telegram_client import get_telegram_credentials
from data.repos.subscribers import (
    register_or_update_telegram_subscriber,
    register_or_update_viber_subscriber,
)
from data.repos.users import get_user_by_id
from data.repos.identities import link_platform_identity, mark_platform_identity_inactive

logger = logging.getLogger(__name__)

VALID_CHANNELS = {"telegram", "viber"}


def create_channel_link_token(
    conn: sqlite3.Connection,
    user_id: int,
    channel: str,
    ttl_minutes: int = 15,
) -> str:
    """
    Generate a secure single-use linking token bound to the authenticated user.
    Invalidates any previous unconsumed token for (user_id, channel).
    """
    clean_channel = channel.strip().lower()
    if clean_channel not in VALID_CHANNELS:
        raise ValueError(f"Invalid channel '{channel}'. Must be one of: {', '.join(sorted(VALID_CHANNELS))}")

    # Clean expired tokens system-wide
    conn.execute("DELETE FROM channel_link_tokens WHERE expires_at < CURRENT_TIMESTAMP;")
    # Invalidate existing token for this user and channel
    conn.execute("DELETE FROM channel_link_tokens WHERE user_id = ? AND channel = ?;", (user_id, clean_channel))

    if clean_channel == "telegram":
        raw_token = secrets.token_urlsafe(16)
    else:
        # 6-digit numeric PIN for Viber so user can easily enter it in Viber chat
        raw_token = f"{secrets.randbelow(900000) + 100000}"

    expires = (datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)).isoformat()
    conn.execute(
        "INSERT INTO channel_link_tokens (token, user_id, channel, expires_at) VALUES (?, ?, ?, ?);",
        (raw_token, user_id, clean_channel, expires),
    )
    return raw_token


def get_telegram_deep_link(token: str) -> str:
    """Generate a Telegram deep link with the verification token payload."""
    bot_username = os.environ.get("TELEGRAM_BOT_USERNAME")
    if not bot_username:
        _, _, default_chat = get_telegram_credentials()
        bot_username = os.environ.get("TELEGRAM_BOT_NAME", "KhulaasaaBot").lstrip("@")
    return f"https://t.me/{bot_username}?start=link_{token}"


def verify_and_link_channel(
    conn: sqlite3.Connection,
    channel: str,
    token: str,
    provider_channel_id: str,
    provider_username: Optional[str] = None,
) -> tuple[bool, str, Optional[int]]:
    """
    Verify single-use token and bind the provider channel ID to the authenticating user.
    Enforces channel ownership, unbinds stale associations, and consumes token.
    Returns (success, message, user_id).
    """
    clean_channel = channel.strip().lower()
    clean_token = token.strip()
    clean_id = str(provider_channel_id).strip()

    if not clean_token or not clean_id:
        return False, "Token and provider identifier are required.", None

    row = conn.execute(
        "SELECT id, user_id, expires_at FROM channel_link_tokens WHERE channel = ? AND token = ?;",
        (clean_channel, clean_token),
    ).fetchone()

    if not row:
        return False, "Invalid or unrecognized verification token.", None

    user_id = row["user_id"] if hasattr(row, "keys") else row[1]
    expires_str = row["expires_at"] if hasattr(row, "keys") else row[2]

    # Check expiration
    if expires_str:
        try:
            exp_clean = expires_str.replace("Z", "+00:00")
            exp_dt = datetime.fromisoformat(exp_clean)
            if exp_dt.tzinfo is None:
                exp_dt = exp_dt.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp_dt:
                conn.execute("DELETE FROM channel_link_tokens WHERE token = ?;", (clean_token,))
                return False, "Verification token has expired. Please generate a new connection link.", None
        except Exception:
            return False, "Invalid expiration date on token.", None

    user = get_user_by_id(conn, user_id)
    if not user:
        conn.execute("DELETE FROM channel_link_tokens WHERE token = ?;", (clean_token,))
        return False, "User account no longer exists.", None

    # Provider identity ownership is exclusive. Never silently transfer an identity
    # already linked to a different Khulaasaa account.
    linked, link_message = link_platform_identity(
        conn,
        clean_channel,
        clean_id,
        user_id,
        provider_username=provider_username,
        display_name=provider_username or user.get("full_name"),
    )
    if not linked:
        conn.execute("DELETE FROM channel_link_tokens WHERE token = ?;", (clean_token,))
        return False, link_message, None

    if clean_channel == "telegram":
        conn.execute(
            "UPDATE users SET telegram_chat_id = ?, telegram_verified = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
            (clean_id, user_id),
        )
        register_or_update_telegram_subscriber(
            conn,
            chat_id=clean_id,
            name=provider_username or user.get("full_name") or f"User {user_id}",
            disciplines=["All"],
            keywords=["all_news", "breaking", "janaza"],
            is_active=1,
            is_paid=1 if user.get("is_paid") else 0,
        )

    elif clean_channel == "viber":
        conn.execute(
            "UPDATE users SET viber_user_id = ?, viber_verified = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
            (clean_id, user_id),
        )
        register_or_update_viber_subscriber(
            conn,
            viber_user_id=clean_id,
            name=provider_username or user.get("full_name") or f"User {user_id}",
            categories=["all", "news", "janaza", "bids", "jobs"],
            is_active=1,
            is_paid=1 if user.get("is_paid") else 0,
        )

    # Consume token to prevent replay
    conn.execute("DELETE FROM channel_link_tokens WHERE token = ?;", (clean_token,))
    return True, f"{clean_channel.capitalize()} successfully linked and verified.", user_id


def disconnect_channel(
    conn: sqlite3.Connection,
    user_id: int,
    channel: str,
) -> bool:
    """
    Disconnect and unverify a channel for a user.
    """
    clean_channel = channel.strip().lower()
    if clean_channel not in VALID_CHANNELS:
        raise ValueError(f"Invalid channel '{channel}'")

    user = get_user_by_id(conn, user_id)
    if not user:
        return False

    if clean_channel == "telegram":
        chat_id = user.get("telegram_chat_id")
        conn.execute(
            "UPDATE users SET telegram_chat_id = NULL, telegram_verified = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
            (user_id,),
        )
        if chat_id:
            conn.execute("UPDATE telegram_subscribers SET is_active = 0 WHERE chat_id = ?;", (chat_id,))
            mark_platform_identity_inactive(conn, "telegram", chat_id)
            conn.execute(
                "UPDATE user_identities SET user_id = NULL, verified_at = NULL, updated_at = CURRENT_TIMESTAMP WHERE provider = 'telegram' AND provider_user_id = ? AND user_id = ?;",
                (chat_id, user_id),
            )

    elif clean_channel == "viber":
        viber_id = user.get("viber_user_id")
        conn.execute(
            "UPDATE users SET viber_user_id = NULL, viber_verified = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
            (user_id,),
        )
        if viber_id:
            conn.execute("UPDATE viber_subscribers SET is_active = 0 WHERE viber_user_id = ?;", (viber_id,))
            mark_platform_identity_inactive(conn, "viber", viber_id)
            conn.execute(
                "UPDATE user_identities SET user_id = NULL, verified_at = NULL, updated_at = CURRENT_TIMESTAMP WHERE provider = 'viber' AND provider_user_id = ? AND user_id = ?;",
                (viber_id, user_id),
            )

    return True


def get_channel_connection_status(
    conn: sqlite3.Connection,
    user_id: int,
) -> dict[str, Any]:
    """
    Retrieve truthful channel connection status for the user.
    """
    row = conn.execute(
        "SELECT telegram_chat_id, telegram_verified, viber_user_id, viber_verified FROM users WHERE id = ?;",
        (user_id,),
    ).fetchone()

    if not row:
        return {
            "telegram": {"connected": False, "chat_id": None, "verified": False},
            "viber": {"connected": False, "user_id": None, "verified": False},
        }

    tg_id = row["telegram_chat_id"] if hasattr(row, "keys") else row[0]
    tg_ver = bool(row["telegram_verified"] if hasattr(row, "keys") else row[1])
    vb_id = row["viber_user_id"] if hasattr(row, "keys") else row[2]
    vb_ver = bool(row["viber_verified"] if hasattr(row, "keys") else row[3])

    return {
        "telegram": {
            "connected": bool(tg_id and tg_ver),
            "chat_id": tg_id,
            "verified": tg_ver,
        },
        "viber": {
            "connected": bool(vb_id and vb_ver),
            "user_id": vb_id,
            "verified": vb_ver,
        },
    }
