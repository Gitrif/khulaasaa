"""
Alert Decision Engine for Khulaasaa.
Evaluates persisted content against user follows, breaking news preferences, quiet hours, and channel eligibility.
Creates 1 logical notification per qualifying event and records per-channel deliveries.
"""
from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from data.repos.notifications import (
    create_logical_notification,
    create_notification_delivery,
)
from services.alert_delivery_service import dispatch_single_delivery

logger = logging.getLogger(__name__)


def get_user_timezone(tz_name: Optional[str]) -> timezone:
    """Resolve user timezone cross-platform, defaulting to Maldives UTC+5."""
    clean = (tz_name or "").strip().lower()
    if not clean or "maldives" in clean or clean in ("mvt", "+05:00", "+05", "utc+5"):
        return timezone(timedelta(hours=5))
    if clean in ("utc", "gmt", "z", "+00:00"):
        return timezone.utc
    try:
        return ZoneInfo(tz_name.strip())
    except Exception:
        return timezone(timedelta(hours=5))


def is_in_quiet_hours(
    now_utc: datetime,
    start_str: str = "23:00",
    end_str: str = "07:00",
    tz_name: str = "Indian/Maldives",
) -> bool:
    """
    Check if the current time falls within user quiet hours.
    Handles midnight crossovers (e.g. 23:00 to 07:00).
    """
    user_tz = get_user_timezone(tz_name)
    local_dt = now_utc.astimezone(user_tz)
    cur_mins = local_dt.hour * 60 + local_dt.minute

    try:
        sh, sm = map(int, start_str.strip().split(":"))
        eh, em = map(int, end_str.strip().split(":"))
        start_mins = sh * 60 + sm
        end_mins = eh * 60 + em
    except Exception:
        start_mins = 23 * 60  # Default 23:00
        end_mins = 7 * 60     # Default 07:00

    if start_mins < end_mins:
        return start_mins <= cur_mins < end_mins
    else:  # Spans midnight (e.g. 23:00 to 07:00)
        return cur_mins >= start_mins or cur_mins < end_mins


def build_event_key(
    content_type: str,
    content_id: str,
    event_version: int = 1,
    update_fingerprint: Optional[str] = None,
) -> str:
    """
    Generate a stable, canonical event key.
    Unchanged re-scrapes yield identical keys; meaningful updates yield a distinct versioned key.
    """
    clean_type = content_type.strip().lower()
    clean_id = str(content_id).strip()
    if update_fingerprint:
        clean_fp = str(update_fingerprint).strip()[:10]
        return f"{clean_type}:{clean_id}:upd_{clean_fp}"
    return f"{clean_type}:{clean_id}:v{max(1, event_version)}"


def evaluate_candidate_recipients(
    conn: sqlite3.Connection,
    content_type: str,
    content_id: str,
    is_breaking: bool = False,
    topics: Optional[list[str]] = None,
    section: Optional[str] = None,
    source_id: Optional[str] = None,
) -> dict[int, dict[str, Any]]:
    """
    Identify all users matching breaking news or follows (story, topic, section, source).
    Returns mapping: user_id -> {'reason': ..., 'reason_target': ...}.
    """
    candidates: dict[int, dict[str, Any]] = {}
    clean_type = content_type.strip().lower()
    clean_id = str(content_id).strip()

    # 1. Breaking news candidates
    if is_breaking:
        breaking_rows = conn.execute(
            """
            SELECT u.id
            FROM users u
            JOIN user_notification_preferences p ON u.id = p.user_id
            WHERE p.breaking_alerts = 1 AND p.is_paused = 0;
            """
        ).fetchall()
        for r in breaking_rows:
            uid = r[0]
            candidates[uid] = {"reason": "breaking", "reason_target": "Breaking News"}

    # 2. Follow matching (story, topic, section, source)
    follow_clauses: list[tuple[str, str]] = []
    if clean_type == "news" and clean_id:
        follow_clauses.append(("story", clean_id))
    if topics:
        for t in topics:
            if t:
                follow_clauses.append(("topic", t.strip().lower()))
    if section:
        follow_clauses.append(("section", section.strip().lower()))
    if source_id:
        follow_clauses.append(("source", str(source_id).strip().lower()))

    if follow_clauses:
        # Match follows where user has followed_content_alerts = 1 and is_paused = 0
        for f_type, f_id in follow_clauses:
            query = """
                SELECT f.user_id, f.target_type, f.target_id
                FROM user_follows f
                JOIN users u ON f.user_id = u.id
                JOIN user_notification_preferences p ON u.id = p.user_id
                WHERE f.target_type = ? AND LOWER(f.target_id) = LOWER(?)
                  AND p.followed_content_alerts = 1 AND p.is_paused = 0;
            """
            rows = conn.execute(query, (f_type, f_id)).fetchall()
            for r in rows:
                uid = r[0]
                # If already matched via breaking, keep breaking or upgrade
                if uid not in candidates:
                    candidates[uid] = {
                        "reason": f"followed_{f_type}",
                        "reason_target": f_id,
                    }

    return candidates


def process_content_event(
    conn: sqlite3.Connection,
    content_type: str,
    content_id: str,
    title: str,
    summary: Optional[str] = None,
    url: Optional[str] = None,
    is_breaking: bool = False,
    topics: Optional[list[str]] = None,
    section: Optional[str] = None,
    source_id: Optional[str] = None,
    event_version: int = 1,
    update_fingerprint: Optional[str] = None,
    mock_mode: bool = False,
) -> dict[str, Any]:
    """
    Core entrypoint for alert evaluation after content persistence.
    Evaluates recipients, creates logical notifications, builds channel deliveries, and dispatches.
    """
    clean_type = content_type.strip().lower()
    clean_id = str(content_id).strip()
    event_key = build_event_key(clean_type, clean_id, event_version, update_fingerprint)

    candidates = evaluate_candidate_recipients(
        conn,
        content_type=clean_type,
        content_id=clean_id,
        is_breaking=is_breaking,
        topics=topics,
        section=section,
        source_id=source_id,
    )

    stats = {
        "event_key": event_key,
        "eligible_users": len(candidates),
        "notifications_created": 0,
        "deliveries_queued": 0,
        "deliveries_dispatched": 0,
    }

    if not candidates:
        return stats

    now_utc = datetime.now(timezone.utc)

    for user_id, match_meta in candidates.items():
        # Fetch user preferences & connection flags
        pref_row = conn.execute(
            """
            SELECT p.is_paused, p.breaking_alerts, p.followed_content_alerts,
                   p.telegram_enabled, p.viber_enabled, p.frequency,
                   p.quiet_hours_enabled, p.quiet_hours_start, p.quiet_hours_end, p.timezone,
                   u.telegram_chat_id, u.telegram_verified, u.viber_user_id, u.viber_verified
            FROM user_notification_preferences p
            JOIN users u ON p.user_id = u.id
            WHERE p.user_id = ?;
            """,
            (user_id,),
        ).fetchone()

        if not pref_row:
            continue

        is_paused = bool(pref_row[0])
        if is_paused:
            continue  # Global pause is absolute

        tg_pref = bool(pref_row[3])
        vb_pref = bool(pref_row[4])
        frequency = pref_row[5] or "instant"
        qh_enabled = bool(pref_row[6])
        qh_start = pref_row[7] or "23:00"
        qh_end = pref_row[8] or "07:00"
        tz_name = pref_row[9] or "Indian/Maldives"

        tg_chat = pref_row[10]
        tg_verified = bool(pref_row[11])
        vb_id = pref_row[12]
        vb_verified = bool(pref_row[13])

        # Channel eligibility: Preference enabled AND truthfully verified AND address exists
        eligible_channels: list[tuple[str, str]] = []
        if tg_pref and tg_verified and tg_chat:
            eligible_channels.append(("telegram", str(tg_chat)))
        if vb_pref and vb_verified and vb_id:
            eligible_channels.append(("viber", str(vb_id)))

        if not eligible_channels:
            continue  # No verified or enabled channels for this user

        # Quiet hours evaluation
        in_quiet = False
        if qh_enabled:
            in_quiet = is_in_quiet_hours(now_utc, qh_start, qh_end, tz_name)

        # Urgent breaking news bypasses quiet hours; routine follows queue
        defer_for_quiet_hours = in_quiet and not is_breaking
        defer_for_digest = (frequency == "digest")

        # 1. Create 1 logical notification record
        notif_id = create_logical_notification(
            conn,
            user_id=user_id,
            event_key=event_key,
            content_type=clean_type,
            content_id=clean_id,
            title=title,
            summary=summary,
            url=url,
            reason=match_meta["reason"],
            reason_target=match_meta["reason_target"],
            is_urgent=1 if is_breaking else 0,
            frequency=frequency,
            event_version=event_version,
        )

        if not notif_id:
            continue  # Duplicate or error

        stats["notifications_created"] += 1

        # 2. Create channel delivery records
        for channel, destination in eligible_channels:
            delivery_status = "pending"
            if defer_for_quiet_hours:
                delivery_status = "queued_quiet_hours"
            elif defer_for_digest:
                delivery_status = "queued_digest"

            deliv_id = create_notification_delivery(
                conn,
                notification_id=notif_id,
                user_id=user_id,
                channel=channel,
                destination=destination,
                status=delivery_status,
            )

            if deliv_id:
                stats["deliveries_queued"] += 1
                # If actionable instant delivery, dispatch immediately
                if delivery_status == "pending":
                    deliv_dict = {
                        "id": deliv_id,
                        "channel": channel,
                        "destination": destination,
                        "title": title,
                        "summary": summary,
                        "url": url,
                        "content_type": clean_type,
                        "is_urgent": is_breaking,
                    }
                    dispatch_single_delivery(conn, deliv_dict, mock_mode=mock_mode)
                    stats["deliveries_dispatched"] += 1

    return stats
