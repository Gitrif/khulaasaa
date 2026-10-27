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


STREAM_PREF_MAP: dict[str, tuple[str, str]] = {
    "news": ("news_alerts", "News Stream"),
    "tender": ("tender_alerts", "Tenders Stream"),
    "job": ("job_alerts", "Jobs Stream"),
    "rental": ("rental_alerts", "Rentals Stream"),
}


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
    Identify all candidate recipients based on category streams, breaking alerts, and follows.
    - Category Streams (Free): Users receive all events in enabled content streams (news, tender, job, rental).
    - Breaking Alerts: Urgent breaking news reaches users with breaking_alerts = 1.
    - Personalization (Pro): Followed story/topic/section/source matching. Pro subscribers (is_paid = 1)
      can receive granular followed alerts even when broad category streams are disabled.
    Returns mapping: user_id -> {'reason': ..., 'reason_target': ...}.
    """
    candidates: dict[int, dict[str, Any]] = {}
    clean_type = content_type.strip().lower()
    clean_id = str(content_id).strip()

    # 1. Content Stream Matching (Free tier default feeds)
    if clean_type in STREAM_PREF_MAP:
        col_name, display_name = STREAM_PREF_MAP[clean_type]
        stream_rows = conn.execute(
            f"""
            SELECT u.id
            FROM users u
            JOIN user_notification_preferences p ON u.id = p.user_id
            WHERE p.{col_name} = 1 AND p.is_paused = 0;
            """
        ).fetchall()
        for r in stream_rows:
            uid = r[0]
            candidates[uid] = {"reason": f"stream_{clean_type}", "reason_target": display_name}

    # 2. Breaking News Candidates (Urgent priority)
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

    # 3. Follow matching with strict content-type compatibility rules
    # Compatibility rules:
    # - 'story', 'topic', 'source': strictly valid only for content_type == 'news'.
    # - 'section':
    #     news: 'major', 'general', or 'breaking'
    #     tender: 'tenders'
    #     job: 'jobs'
    #     rental: 'rentals'
    follow_clauses: list[tuple[str, str]] = []
    if clean_type == "news":
        if clean_id:
            follow_clauses.append(("story", clean_id))
        if topics:
            for t in topics:
                if t:
                    follow_clauses.append(("topic", t.strip().lower()))
        if source_id:
            follow_clauses.append(("source", str(source_id).strip().lower()))
        if section:
            sec_clean = section.strip().lower()
            if sec_clean in {"major", "general", "breaking"}:
                follow_clauses.append(("section", sec_clean))
        if is_breaking:
            follow_clauses.append(("section", "breaking"))

    elif clean_type == "tender":
        follow_clauses.append(("section", "tenders"))

    elif clean_type == "job":
        follow_clauses.append(("section", "jobs"))

    elif clean_type == "rental":
        follow_clauses.append(("section", "rentals"))

    if follow_clauses:
        for f_type, f_id in follow_clauses:
            query = """
                SELECT f.user_id, f.target_type, f.target_id, u.is_paid
                FROM user_follows f
                JOIN users u ON f.user_id = u.id
                JOIN user_notification_preferences p ON u.id = p.user_id
                WHERE f.target_type = ? AND LOWER(f.target_id) = LOWER(?)
                  AND p.followed_content_alerts = 1 AND p.is_paused = 0;
            """
            rows = conn.execute(query, (f_type, f_id)).fetchall()
            for r in rows:
                uid = r[0]
                is_paid = bool(r[3])

                # Only Pro users qualify for personalized follow reasons
                if is_paid:
                    if uid in candidates:
                        # Upgrade broad stream reason to personalized follow reason (breaking remains urgent)
                        if candidates[uid]["reason"].startswith("stream_"):
                            candidates[uid] = {
                                "reason": f"followed_{f_type}",
                                "reason_target": f_id,
                            }
                    else:
                        # Pro Entitlement: Pro users receive targeted follows even if broad category stream is muted
                        candidates[uid] = {
                            "reason": f"followed_{f_type}",
                            "reason_target": f_id,
                        }
                # Free users who qualified through an enabled broad stream retain reason: stream_{clean_type}.
                # Free users whose broad stream is muted do NOT match.

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

        # Quiet hours evaluation
        in_quiet = False
        if qh_enabled:
            in_quiet = is_in_quiet_hours(now_utc, qh_start, qh_end, tz_name)

        # Urgent breaking news bypasses quiet hours; routine follows queue
        defer_for_quiet_hours = in_quiet and not is_breaking
        defer_for_digest = (frequency == "digest")

        # Deduplication check: Has user already been alerted for this exact event?
        already_alerted = conn.execute(
            "SELECT id FROM notifications WHERE user_id = ? AND event_key = ?;",
            (user_id, event_key),
        ).fetchone()
        if already_alerted:
            continue

        # 1. Create 1 logical notification record (recorded independently for in-app center)
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

        # Channel eligibility: Preference enabled AND truthfully verified AND address exists
        eligible_channels: list[tuple[str, str]] = []
        if tg_pref and tg_verified and tg_chat:
            eligible_channels.append(("telegram", str(tg_chat)))
        if vb_pref and vb_verified and vb_id:
            eligible_channels.append(("viber", str(vb_id)))

        # 2. Create channel delivery records for eligible channels
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

    # Commit durable database state. A failed database commit must never be treated as successful.
    if hasattr(conn, "commit"):
        conn.commit()

    return stats
