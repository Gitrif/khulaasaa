"""
Alert Delivery Reliability Engine for Khulaasaa.
Handles atomic claiming, lease expiry, retry backoff, and independent channel dispatch to Telegram and Viber.
Guarantees at-least-once delivery semantics without holding database locks across network I/O.
"""
from __future__ import annotations

import logging
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from data.repos.notifications import update_delivery_status

logger = logging.getLogger(__name__)

# Bounded retry backoff schedule (seconds since last attempt)
RETRY_BACKOFF_SECONDS = {
    1: 30,    # First retry after 30s
    2: 120,   # Second retry after 2m
    3: 300,   # Third retry after 5m
}
DEFAULT_LEASE_SECONDS = 180  # 3 minute worker claim lease


def format_notification_message(
    content_type: str,
    title: str,
    summary: Optional[str] = None,
    url: Optional[str] = None,
    reason: Optional[str] = None,
    is_urgent: bool = False,
    channel: str = "telegram",
) -> str:
    """Format a clean alert message strictly adhering to the Zero-Emoji Policy."""
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
    else:  # Viber
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


def claim_actionable_deliveries(
    conn: sqlite3.Connection,
    limit: int = 25,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    worker_id: Optional[str] = None,
    ignore_backoff: bool = False,
) -> list[dict[str, Any]]:
    """
    Atomically claims eligible pending/retryable deliveries using a database-level lease.
    Prevents multiple concurrent workers or processes from dispatching the same delivery.
    """
    now_utc = datetime.now(timezone.utc)
    now_iso = now_utc.isoformat()
    lease_cutoff_iso = (now_utc - timedelta(seconds=lease_seconds)).isoformat()
    claim_token = worker_id or secrets.token_hex(8)

    # 1. Find candidate delivery IDs eligible for processing
    rows = conn.execute(
        """
        SELECT d.id, d.attempt_count, d.last_attempt_at, d.status, d.claimed_at
        FROM notification_deliveries d
        WHERE d.status = 'pending'
           OR (d.status = 'failed' AND d.attempt_count < d.max_attempts)
           OR (d.status = 'claiming' AND d.claimed_at < ?)
        ORDER BY d.id ASC
        LIMIT ?;
        """,
        (lease_cutoff_iso, max(1, min(limit, 50))),
    ).fetchall()

    claimed_ids: list[int] = []
    for r in rows:
        did = r[0]
        attempts = r[1]
        last_att = r[2]
        st = r[3]

        # Enforce retry backoff timing for failed deliveries
        if not ignore_backoff and st == "failed" and last_att:
            try:
                exp_clean = last_att.replace("Z", "+00:00")
                last_dt = datetime.fromisoformat(exp_clean)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                required_delay = RETRY_BACKOFF_SECONDS.get(attempts, 60)
                if (now_utc - last_dt).total_seconds() < required_delay:
                    continue  # Still within backoff period
            except Exception:
                pass

        # Atomic claim: Only one worker will succeed in updating matching row
        cur = conn.execute(
            """
            UPDATE notification_deliveries
            SET status = 'claiming', claim_token = ?, claimed_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND (
                status = 'pending'
                OR (status = 'failed' AND attempt_count < max_attempts)
                OR (status = 'claiming' AND claimed_at < ?)
            );
            """,
            (claim_token, now_iso, did, lease_cutoff_iso),
        )
        if cur.rowcount > 0:
            claimed_ids.append(did)

    if hasattr(conn, "commit"):
        try:
            conn.commit()
        except Exception:
            pass

    if not claimed_ids:
        return []

    # 2. Fetch full payload for claimed deliveries
    placeholders = ",".join("?" for _ in claimed_ids)
    query = f"""
        SELECT d.id, d.notification_id, d.user_id, d.channel, d.destination, d.attempt_count,
               d.max_attempts, d.claim_token, n.title, n.summary, n.url, n.content_type, n.is_urgent
        FROM notification_deliveries d
        JOIN notifications n ON d.notification_id = n.id
        WHERE d.id IN ({placeholders}) AND d.claim_token = ?;
    """
    claimed_rows = conn.execute(query, (*claimed_ids, claim_token)).fetchall()
    return [dict(r) for r in claimed_rows]


def finalize_delivery(
    conn: sqlite3.Connection,
    delivery_id: int,
    claim_token: str,
    success: bool,
    error_message: Optional[str] = None,
) -> bool:
    """Finalize delivery status after network provider call."""
    now_iso = datetime.now(timezone.utc).isoformat()
    clean_err = None
    if error_message:
        clean_err = str(error_message)[:255]
        for secret_kw in ("token", "bot", "password", "secret", "bearer", "authorization"):
            if secret_kw in clean_err.lower():
                clean_err = "[Redacted security parameter from provider error]"
                break

    if success:
        conn.execute(
            """
            UPDATE notification_deliveries
            SET status = 'delivered', delivered_at = ?, attempt_count = attempt_count + 1,
                claim_token = NULL, last_attempt_at = ?, error_message = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND claim_token = ?;
            """,
            (now_iso, now_iso, delivery_id, claim_token),
        )
    else:
        conn.execute(
            """
            UPDATE notification_deliveries
            SET status = CASE WHEN attempt_count + 1 >= max_attempts THEN 'dead_letter' ELSE 'failed' END,
                attempt_count = attempt_count + 1, claim_token = NULL, last_attempt_at = ?,
                error_message = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND claim_token = ?;
            """,
            (now_iso, clean_err, delivery_id, claim_token),
        )

    if hasattr(conn, "commit"):
        try:
            conn.commit()
        except Exception:
            pass
    return True


def dispatch_single_delivery(
    conn: sqlite3.Connection,
    delivery: dict[str, Any],
    mock_mode: bool = False,
) -> tuple[bool, str]:
    """Execute network dispatch for a claimed delivery without holding open DB locks."""
    delivery_id = delivery["id"]
    claim_token = delivery.get("claim_token") or ""
    channel = delivery["channel"]
    destination = str(delivery["destination"]).strip()
    title = delivery.get("title") or "Khulaasaa Update"
    summary = delivery.get("summary")
    url = delivery.get("url")
    content_type = delivery.get("content_type") or "news"
    is_urgent = bool(delivery.get("is_urgent"))

    if mock_mode or os.environ.get("KHULAASAA_MOCK_ALERTS") == "1":
        finalize_delivery(conn, delivery_id, claim_token, success=True)
        return True, "Delivered (mock mode)"

    msg = format_notification_message(
        content_type=content_type, title=title, summary=summary,
        url=url, is_urgent=is_urgent, channel=channel,
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

    finalize_delivery(conn, delivery_id, claim_token, success=success, error_message=err_msg)
    return success, "Delivered successfully" if success else (err_msg or "Delivery failed")


def retry_failed_deliveries(
    conn: sqlite3.Connection,
    limit: int = 25,
    mock_mode: bool = False,
    ignore_backoff: bool = True,
) -> dict[str, int]:
    """Retry pending or retryable deliveries with bounded retries."""
    claimed = claim_actionable_deliveries(conn, limit=limit, ignore_backoff=ignore_backoff)
    success_count = 0
    fail_count = 0
    for deliv in claimed:
        ok, _ = dispatch_single_delivery(conn, deliv, mock_mode=mock_mode)
        if ok:
            success_count += 1
        else:
            fail_count += 1
    return {
        "success": success_count,
        "failed": fail_count,
        "total": len(claimed),
    }


def process_operational_delivery_queue(
    conn: sqlite3.Connection,
    limit: int = 50,
    mock_mode: bool = False,
    worker_id: Optional[str] = None,
) -> dict[str, int]:
    """Operational outbox sweep: releases quiet hours and dispatches claimed deliveries."""
    now_utc = datetime.now(timezone.utc)
    released_count = 0

    # 1. Release quiet hours
    qh_rows = conn.execute(
        """
        SELECT d.id, d.user_id, p.quiet_hours_enabled, p.quiet_hours_start, p.quiet_hours_end, p.timezone
        FROM notification_deliveries d
        JOIN user_notification_preferences p ON d.user_id = p.user_id
        WHERE d.status = 'queued_quiet_hours'
        LIMIT ?;
        """,
        (limit,),
    ).fetchall()

    for row in qh_rows:
        deliv_id = row[0]
        qh_enabled = bool(row[2])
        qh_start = row[3] or "23:00"
        qh_end = row[4] or "07:00"
        tz_name = row[5] or "Indian/Maldives"

        still_quiet = False
        if qh_enabled:
            from services.alert_decision_service import is_in_quiet_hours
            still_quiet = is_in_quiet_hours(now_utc, qh_start, qh_end, tz_name)

        if not still_quiet:
            cur = conn.execute(
                "UPDATE notification_deliveries SET status = 'pending', updated_at = CURRENT_TIMESTAMP WHERE id = ? AND status = 'queued_quiet_hours';",
                (deliv_id,),
            )
            if cur.rowcount > 0:
                released_count += 1

    if hasattr(conn, "commit"):
        try:
            conn.commit()
        except Exception:
            pass

    # 2. Claim actionable deliveries
    claimed = claim_actionable_deliveries(conn, limit=limit, worker_id=worker_id)
    success_count = 0
    fail_count = 0

    # 3. Dispatch each claimed delivery independently
    for deliv in claimed:
        ok, _ = dispatch_single_delivery(conn, deliv, mock_mode=mock_mode)
        if ok:
            success_count += 1
        else:
            fail_count += 1

    return {
        "quiet_hours_released": released_count,
        "dispatched": success_count,
        "failed": fail_count,
        "total_attempted": len(claimed),
    }
