"""
Alert Delivery Reliability Engine for Khulaasaa.
Handles independent, bounded-retry channel dispatch to Telegram and Viber with error sanitization.
"""
from __future__ import annotations

import logging
import os
import sqlite3
from typing import Any, Optional

from data.repos.notifications import update_delivery_status

logger = logging.getLogger(__name__)


def format_notification_message(
    content_type: str,
    title: str,
    summary: Optional[str] = None,
    url: Optional[str] = None,
    reason: Optional[str] = None,
    is_urgent: bool = False,
    channel: str = "telegram",
) -> str:
    """
    Format a clean alert message strictly adhering to the Zero-Emoji Policy.
    """
    clean_type = content_type.upper()
    prefix = f"[BREAKING {clean_type}]" if is_urgent else f"[{clean_type} ALERT]"

    lines: list[str]
    if channel == "telegram":
        header = f"<b>{prefix} {title}</b>"
        lines = [header]
        if summary:
            clean_sum = summary.strip()
            if len(clean_sum) > 280:
                clean_sum = clean_sum[:277] + "..."
            lines.extend(["", clean_sum])
        if url:
            lines.extend(["", f'<a href="{url}">Read full report on Khulaasaa</a>'])
    else:  # Viber (plain text formatting)
        header = f"{prefix} {title}"
        lines = [header]
        if summary:
            clean_sum = summary.strip()
            if len(clean_sum) > 280:
                clean_sum = clean_sum[:277] + "..."
            lines.extend(["", clean_sum])
        if url:
            lines.extend(["", f"Read more: {url}"])

    return "\n".join(lines)


def dispatch_single_delivery(
    conn: sqlite3.Connection,
    delivery: dict[str, Any],
    mock_mode: bool = False,
) -> tuple[bool, str]:
    """
    Dispatch a single delivery record to Telegram or Viber independently.
    Records delivery outcome in the database.
    Returns (success, message).
    """
    delivery_id = delivery["id"]
    channel = delivery["channel"]
    destination = str(delivery["destination"]).strip()
    title = delivery.get("title") or "Khulaasaa Update"
    summary = delivery.get("summary")
    url = delivery.get("url")
    content_type = delivery.get("content_type") or "news"
    is_urgent = bool(delivery.get("is_urgent"))

    # Test mode / mock mode short-circuit
    if mock_mode or os.environ.get("KHULAASAA_MOCK_ALERTS") == "1":
        update_delivery_status(conn, delivery_id, status="delivered")
        return True, "Delivered (mock mode)"

    msg = format_notification_message(
        content_type=content_type,
        title=title,
        summary=summary,
        url=url,
        is_urgent=is_urgent,
        channel=channel,
    )

    success = False
    err_msg: Optional[str] = None

    try:
        if channel == "telegram":
            from alerts.telegram_client import send_telegram_message
            ok, res_text = send_telegram_message(msg, chat_id=destination)
            if ok:
                success = True
            else:
                err_msg = res_text or "Telegram delivery failed"

        elif channel == "viber":
            from alerts.viber import send_viber_message
            res = send_viber_message(destination, msg)
            if isinstance(res, dict) and res.get("status") == 0:
                success = True
            else:
                err_msg = res.get("status_message") if isinstance(res, dict) else "Viber delivery failed"
        else:
            err_msg = f"Unsupported channel {channel}"

    except Exception as exc:
        err_msg = f"Provider connection error: {type(exc).__name__}"

    if success:
        update_delivery_status(conn, delivery_id, status="delivered")
        return True, "Delivered successfully"
    else:
        update_delivery_status(conn, delivery_id, status="failed", error_message=err_msg)
        return False, err_msg or "Delivery failed"


def retry_failed_deliveries(
    conn: sqlite3.Connection,
    limit: int = 25,
    mock_mode: bool = False,
) -> dict[str, int]:
    """
    Retry pending or retryable failed deliveries with bounded retries.
    """
    rows = conn.execute(
        """
        SELECT d.*, n.title, n.summary, n.url, n.content_type, n.is_urgent
        FROM notification_deliveries d
        JOIN notifications n ON d.notification_id = n.id
        WHERE d.status IN ('pending', 'failed') AND d.attempt_count < d.max_attempts
        ORDER BY n.is_urgent DESC, d.created_at ASC
        LIMIT ?;
        """,
        (limit,),
    ).fetchall()

    results = {"success": 0, "failed": 0, "total": len(rows)}
    for r in rows:
        deliv = dict(r)
        ok, _ = dispatch_single_delivery(conn, deliv, mock_mode=mock_mode)
        if ok:
            results["success"] += 1
        else:
            results["failed"] += 1

    return results
