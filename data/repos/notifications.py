"""
Notifications and Delivery Tracking Repository for Khulaasaa.
Handles logical notifications, per-channel delivery attempts, and user notification queries.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

VALID_CONTENT_TYPES = {"news", "tender", "job", "rental", "obituary"}
VALID_DELIVERY_CHANNELS = {"telegram", "viber"}
VALID_DELIVERY_STATUSES = {
    "pending",
    "delivered",
    "failed",
    "dead_letter",
    "queued_quiet_hours",
    "queued_digest",
}


def create_logical_notification(
    conn: sqlite3.Connection,
    user_id: int,
    event_key: str,
    content_type: str,
    content_id: str,
    title: str,
    summary: Optional[str] = None,
    url: Optional[str] = None,
    reason: str = "breaking",
    reason_target: Optional[str] = None,
    is_urgent: int = 0,
    frequency: str = "instant",
    event_version: int = 1,
) -> Optional[int]:
    """
    Idempotently creates a logical notification for a user and content event.
    Database-enforced UNIQUE(user_id, event_key) guarantees no duplicates.
    Returns notification_id if created or already existing, or None on error.
    """
    clean_event = event_key.strip()
    clean_title = title.strip()
    if not clean_event or not clean_title:
        return None

    # Check if already exists first (idempotent lookup)
    row = conn.execute(
        "SELECT id FROM notifications WHERE user_id = ? AND event_key = ?;",
        (user_id, clean_event),
    ).fetchone()
    if row:
        return row["id"] if hasattr(row, "keys") else row[0]

    try:
        conn.execute("SAVEPOINT notif_create_sp;")
        cur = conn.execute(
            """
            INSERT INTO notifications (
                user_id, event_key, content_type, content_id, event_version,
                reason, reason_target, title, summary, url,
                is_urgent, frequency
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, event_key) DO UPDATE SET is_urgent = excluded.is_urgent
            RETURNING id;
            """,
            (
                user_id,
                clean_event,
                content_type,
                str(content_id),
                event_version,
                reason,
                reason_target,
                clean_title,
                summary,
                url,
                1 if is_urgent else 0,
                frequency if frequency in ("instant", "digest") else "instant",
            ),
        )
        res_row = cur.fetchone()
        conn.execute("RELEASE SAVEPOINT notif_create_sp;")
        if res_row:
            return res_row["id"] if hasattr(res_row, "keys") else res_row[0]
        return getattr(cur, "lastrowid", None)
    except Exception as exc:
        try:
            conn.execute("ROLLBACK TO SAVEPOINT notif_create_sp;")
        except Exception:
            pass
        row = conn.execute(
            "SELECT id FROM notifications WHERE user_id = ? AND event_key = ?;",
            (user_id, clean_event),
        ).fetchone()
        if row:
            return row["id"] if hasattr(row, "keys") else row[0]
        from data.database import log_db_error
        log_db_error(logger, "create_logical_notification", "data.repos.notifications", exc)
        raise


def create_notification_delivery(
    conn: sqlite3.Connection,
    notification_id: int,
    user_id: int,
    channel: str,
    destination: str,
    status: str = "pending",
    max_attempts: int = 3,
) -> Optional[int]:
    """
    Idempotently records a delivery attempt for a channel.
    UNIQUE(notification_id, channel) prevents duplicate channel dispatch.
    """
    clean_channel = channel.strip().lower()
    clean_dest = str(destination).strip()
    if clean_channel not in VALID_DELIVERY_CHANNELS or not clean_dest:
        return None

    init_status = status if status in VALID_DELIVERY_STATUSES else "pending"

    row = conn.execute(
        "SELECT id FROM notification_deliveries WHERE notification_id = ? AND channel = ?;",
        (notification_id, clean_channel),
    ).fetchone()
    if row:
        return row["id"] if hasattr(row, "keys") else row[0]

    try:
        conn.execute("SAVEPOINT delivery_create_sp;")
        cur = conn.execute(
            """
            INSERT INTO notification_deliveries (
                notification_id, user_id, channel, destination, status, max_attempts
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(notification_id, channel) DO UPDATE SET status = notification_deliveries.status
            RETURNING id;
            """,
            (notification_id, user_id, clean_channel, clean_dest, init_status, max_attempts),
        )
        res_row = cur.fetchone()
        conn.execute("RELEASE SAVEPOINT delivery_create_sp;")
        if res_row:
            return res_row["id"] if hasattr(res_row, "keys") else res_row[0]
        return getattr(cur, "lastrowid", None)
    except Exception as exc:
        try:
            conn.execute("ROLLBACK TO SAVEPOINT delivery_create_sp;")
        except Exception:
            pass
        row = conn.execute(
            "SELECT id FROM notification_deliveries WHERE notification_id = ? AND channel = ?;",
            (notification_id, clean_channel),
        ).fetchone()
        if row:
            return row["id"] if hasattr(row, "keys") else row[0]
        from data.database import log_db_error
        log_db_error(logger, "create_notification_delivery", "data.repos.notifications", exc)
        raise


def update_delivery_status(
    conn: sqlite3.Connection,
    delivery_id: int,
    status: str,
    error_message: Optional[str] = None,
    increment_attempt: bool = True,
) -> bool:
    """
    Updates the outcome of a delivery attempt with sanitized error logging and bounded retries.
    """
    clean_status = status if status in VALID_DELIVERY_STATUSES else "failed"
    row = conn.execute(
        "SELECT attempt_count, max_attempts FROM notification_deliveries WHERE id = ?;",
        (delivery_id,),
    ).fetchone()
    if not row:
        return False

    attempts = (row["attempt_count"] if hasattr(row, "keys") else row[0]) + (1 if increment_attempt else 0)
    max_att = row["max_attempts"] if hasattr(row, "keys") else row[1]

    # Sanitize error message to prevent leaking tokens or internal secrets
    sanitized_err = None
    if error_message:
        sanitized_err = str(error_message)[:255]
        for secret_kw in ("token", "bot", "password", "secret", "bearer", "authorization"):
            if secret_kw in sanitized_err.lower():
                sanitized_err = "[Redacted security parameter from provider error]"
                break

    now_iso = datetime.now(timezone.utc).isoformat()
    delivered_iso = now_iso if clean_status == "delivered" else None

    # Mark as dead_letter if max attempts reached
    final_status = clean_status
    if clean_status == "failed" and attempts >= max_att:
        final_status = "dead_letter"

    conn.execute(
        """
        UPDATE notification_deliveries
        SET status = ?, attempt_count = ?, error_message = ?, last_attempt_at = ?, delivered_at = COALESCE(delivered_at, ?), updated_at = CURRENT_TIMESTAMP
        WHERE id = ?;
        """,
        (final_status, attempts, sanitized_err, now_iso, delivered_iso, delivery_id),
    )
    return True


def list_user_notifications(
    conn: sqlite3.Connection,
    user_id: int,
    limit: int = 30,
    offset: int = 0,
    unread_only: bool = False,
) -> list[dict[str, Any]]:
    """Retrieve paginated notifications for the user."""
    query = "SELECT * FROM notifications WHERE user_id = ?"
    params: list[Any] = [user_id]
    if unread_only:
        query += " AND is_read = 0"
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?;"
    params.extend([max(1, min(limit, 100)), max(0, offset)])

    rows = conn.execute(query, tuple(params)).fetchall()
    return [dict(r) if hasattr(r, "keys") else {
        "id": r[0], "user_id": r[1], "event_key": r[2], "content_type": r[3],
        "content_id": r[4], "event_version": r[5], "reason": r[6], "reason_target": r[7],
        "title": r[8], "summary": r[9], "url": r[10], "is_urgent": bool(r[11]),
        "frequency": r[12], "is_read": bool(r[13]), "created_at": r[14]
    } for r in rows]


def mark_notification_read(conn: sqlite3.Connection, user_id: int, notification_id: int) -> bool:
    """Mark a single notification as read."""
    cur = conn.execute(
        "UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?;",
        (notification_id, user_id),
    )
    return cur.rowcount > 0


def mark_all_notifications_read(conn: sqlite3.Connection, user_id: int) -> int:
    """Mark all unread notifications as read for the user."""
    cur = conn.execute(
        "UPDATE notifications SET is_read = 1 WHERE user_id = ? AND is_read = 0;",
        (user_id,),
    )
    return cur.rowcount


def get_unread_notification_count(conn: sqlite3.Connection, user_id: int) -> int:
    """Count unread notifications for notification badge."""
    row = conn.execute(
        "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0;",
        (user_id,),
    ).fetchone()
    return row[0] if row else 0


def get_deliveries_for_notification(conn: sqlite3.Connection, notification_id: int) -> list[dict[str, Any]]:
    """Retrieve delivery statuses for a logical notification."""
    rows = conn.execute(
        "SELECT * FROM notification_deliveries WHERE notification_id = ? ORDER BY id ASC;",
        (notification_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_pending_deliveries(
    conn: sqlite3.Connection,
    channel: Optional[str] = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Retrieve actionable deliveries waiting to be dispatched or retried."""
    query = """
        SELECT d.*, n.title, n.summary, n.url, n.content_type, n.is_urgent
        FROM notification_deliveries d
        JOIN notifications n ON d.notification_id = n.id
        WHERE d.status IN ('pending', 'failed') AND d.attempt_count < d.max_attempts
    """
    params: list[Any] = []
    if channel:
        query += " AND d.channel = ?"
        params.append(channel.strip().lower())
    query += " ORDER BY n.is_urgent DESC, d.created_at ASC LIMIT ?;"
    params.append(max(1, min(limit, 100)))

    rows = conn.execute(query, tuple(params)).fetchall()
    return [dict(r) for r in rows]
