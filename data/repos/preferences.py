"""
User Notification Preferences Repository for Khulaasaa.
Handles delivery toggles, frequency, quiet hours, timezone, and global notification pausing.
"""
from __future__ import annotations

import re
import sqlite3
from typing import Any, Optional

DEFAULT_PREFERENCES: dict[str, Any] = {
    "breaking_alerts": 1,
    "followed_content_alerts": 1,
    "telegram_enabled": 1,
    "viber_enabled": 1,
    "frequency": "instant",
    "quiet_hours_enabled": 0,
    "quiet_hours_start": "23:00",
    "quiet_hours_end": "07:00",
    "timezone": "Indian/Maldives",
    "is_paused": 0,
}

_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def _parse_pref_row(row: Any) -> Optional[dict[str, Any]]:
    if not row:
        return None
    d = dict(row) if hasattr(row, "keys") else {
        "user_id": row[0],
        "breaking_alerts": row[1],
        "followed_content_alerts": row[2],
        "telegram_enabled": row[3],
        "viber_enabled": row[4],
        "frequency": row[5],
        "quiet_hours_enabled": row[6],
        "quiet_hours_start": row[7],
        "quiet_hours_end": row[8],
        "timezone": row[9],
        "is_paused": row[10],
        "created_at": row[11],
        "updated_at": row[12],
    }
    return {
        "user_id": d["user_id"],
        "breaking_alerts": bool(d.get("breaking_alerts", 1)),
        "followed_content_alerts": bool(d.get("followed_content_alerts", 1)),
        "telegram_enabled": bool(d.get("telegram_enabled", 1)),
        "viber_enabled": bool(d.get("viber_enabled", 1)),
        "frequency": str(d.get("frequency") or "instant").lower(),
        "quiet_hours_enabled": bool(d.get("quiet_hours_enabled", 0)),
        "quiet_hours_start": str(d.get("quiet_hours_start") or "23:00"),
        "quiet_hours_end": str(d.get("quiet_hours_end") or "07:00"),
        "timezone": str(d.get("timezone") or "Indian/Maldives"),
        "is_paused": bool(d.get("is_paused", 0)),
        "created_at": d.get("created_at"),
        "updated_at": d.get("updated_at"),
    }


def get_user_preferences(conn: sqlite3.Connection, user_id: int) -> dict[str, Any]:
    """
    Retrieve user notification preferences.
    If no record exists, lazily inserts default preferences and returns them.
    """
    row = conn.execute(
        """
        SELECT user_id, breaking_alerts, followed_content_alerts, telegram_enabled, viber_enabled,
               frequency, quiet_hours_enabled, quiet_hours_start, quiet_hours_end, timezone,
               is_paused, created_at, updated_at
        FROM user_notification_preferences
        WHERE user_id = ?;
        """,
        (user_id,),
    ).fetchone()

    if row:
        parsed = _parse_pref_row(row)
        if parsed:
            return parsed

    # Lazy insert default preferences
    conn.execute(
        """
        INSERT INTO user_notification_preferences (
            user_id, breaking_alerts, followed_content_alerts, telegram_enabled, viber_enabled,
            frequency, quiet_hours_enabled, quiet_hours_start, quiet_hours_end, timezone, is_paused
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO NOTHING;
        """,
        (
            user_id,
            DEFAULT_PREFERENCES["breaking_alerts"],
            DEFAULT_PREFERENCES["followed_content_alerts"],
            DEFAULT_PREFERENCES["telegram_enabled"],
            DEFAULT_PREFERENCES["viber_enabled"],
            DEFAULT_PREFERENCES["frequency"],
            DEFAULT_PREFERENCES["quiet_hours_enabled"],
            DEFAULT_PREFERENCES["quiet_hours_start"],
            DEFAULT_PREFERENCES["quiet_hours_end"],
            DEFAULT_PREFERENCES["timezone"],
            DEFAULT_PREFERENCES["is_paused"],
        ),
    )

    row = conn.execute(
        """
        SELECT user_id, breaking_alerts, followed_content_alerts, telegram_enabled, viber_enabled,
               frequency, quiet_hours_enabled, quiet_hours_start, quiet_hours_end, timezone,
               is_paused, created_at, updated_at
        FROM user_notification_preferences
        WHERE user_id = ?;
        """,
        (user_id,),
    ).fetchone()
    return _parse_pref_row(row) or dict(DEFAULT_PREFERENCES, user_id=user_id)


def update_user_preferences(conn: sqlite3.Connection, user_id: int, **kwargs: Any) -> dict[str, Any]:
    """
    Update user notification preferences with strict field validation.
    """
    # Ensure baseline row exists first
    get_user_preferences(conn, user_id)

    valid_keys = {
        "breaking_alerts",
        "followed_content_alerts",
        "telegram_enabled",
        "viber_enabled",
        "frequency",
        "quiet_hours_enabled",
        "quiet_hours_start",
        "quiet_hours_end",
        "timezone",
        "is_paused",
    }

    updates = ["updated_at = CURRENT_TIMESTAMP"]
    params: list[Any] = []

    for key, val in kwargs.items():
        if key not in valid_keys or val is None:
            continue

        if key in {"breaking_alerts", "followed_content_alerts", "telegram_enabled", "viber_enabled", "quiet_hours_enabled", "is_paused"}:
            updates.append(f"{key} = ?")
            params.append(1 if val else 0)

        elif key == "frequency":
            freq = str(val).strip().lower()
            if freq not in {"instant", "digest"}:
                raise ValueError("frequency must be 'instant' or 'digest'")
            updates.append("frequency = ?")
            params.append(freq)

        elif key in {"quiet_hours_start", "quiet_hours_end"}:
            t_str = str(val).strip()
            if not _TIME_RE.match(t_str):
                raise ValueError(f"{key} must be in 24-hour HH:MM format (00:00 to 23:59)")
            updates.append(f"{key} = ?")
            params.append(t_str)

        elif key == "timezone":
            tz_str = str(val).strip() or "Indian/Maldives"
            updates.append("timezone = ?")
            params.append(tz_str)

    if len(updates) > 1:
        params.append(user_id)
        sql = f"UPDATE user_notification_preferences SET {', '.join(updates)} WHERE user_id = ?;"
        conn.execute(sql, tuple(params))

    return get_user_preferences(conn, user_id)
