from __future__ import annotations

import alerts.telegram as tg
"""
Telegram Multi-Channel Alert Dispatcher (Tenders, News, Obituaries, Jobs, Sponsored).
"""

import html
import json
import logging
import sqlite3
import time
from typing import Any, Optional

import requests

from data.database import (
    get_db,
    get_telegram_subscribers,
    is_subscriber_paid,
    get_active_sponsored_ad,
    record_ad_impression,
)
from alerts.telegram_client import (
    DEFAULT_TELEGRAM_BOT_TOKEN,
    DEFAULT_TELEGRAM_CHAT_ID,
    get_telegram_credentials,
    send_telegram_message,
)
from alerts.telegram_formatters import (
    matches_interest,
    format_tender_alert_html,
    build_tender_keyboard,
    matches_news_interest,
    format_news_alert_html,
    build_news_keyboard,
    format_obituary_alert_html,
    build_obituary_keyboard,
    format_job_alert_html,
    format_sponsored_block,
    format_standalone_ad_post,
)

logger = logging.getLogger(__name__)

def record_alert_sent(conn: sqlite3.Connection, notice_id: str, chat_id: str) -> None:
    """Record that an alert has been delivered for a notice to prevent duplicates."""
    conn.execute(
        """
        INSERT OR IGNORE INTO sent_alerts (notice_id, chat_id, sent_at)
        VALUES (?, ?, CURRENT_TIMESTAMP);
        """,
        (notice_id, chat_id),
    )


def is_alert_already_sent(conn: sqlite3.Connection, notice_id: str, chat_id: str) -> bool:
    """Check if an alert for this notice was already delivered to chat_id."""
    row = conn.execute(
        "SELECT id FROM sent_alerts WHERE notice_id = ? AND chat_id = ? LIMIT 1;",
        (notice_id, chat_id),
    ).fetchone()
    return row is not None


def dispatch_tender_alerts(
    conn: sqlite3.Connection,
    bids: list[dict[str, Any]],
    bot_token: Optional[str] = None,
    force_resend: bool = False,
) -> list[dict[str, Any]]:
    """
    Iterates over bids and sends Telegram alerts to all matching active subscribers.
    Returns audit log of sent alerts.
    """
    token, default_chat = get_telegram_credentials(bot_token=bot_token)
    if not token:
        logger.info("Telegram bot token not configured; skipping dispatch")
        return []

    # Fetch active subscribers from SQLite
    raw_subs = conn.execute(
        "SELECT id, chat_id, name, disciplines, keywords, created_at FROM telegram_subscribers WHERE is_active = 1;"
    ).fetchall()
    subscribers = [dict(r) for r in raw_subs]

    # Include default broadcast channel if configured
    if default_chat and not any(str(s["chat_id"]) == str(default_chat) for s in subscribers):
        subscribers.append({
            "id": 0,
            "chat_id": str(default_chat),
            "name": "Main Broadcast Channel",
            "disciplines": '["All"]',
            "keywords": '["All"]',
            "created_at": None,
        })

    if not subscribers:
        return []

    sent_records: list[dict[str, Any]] = []

    from data.database import get_active_sponsored_ad, record_ad_impression, is_subscriber_paid
    active_ad = get_active_sponsored_ad(conn, target_category="bids")
    ad_footer = format_sponsored_block(active_ad) if active_ad else None

    for sub_row in subscribers:
        chat_id = sub_row["chat_id"]
        sub_started_at = str(sub_row["created_at"] or "")
        paid = is_subscriber_paid(conn, chat_id)
        try:
            disc_list = json.loads(sub_row["disciplines"]) if sub_row["disciplines"] else []
        except Exception:
            disc_list = []
        try:
            kw_list = json.loads(sub_row["keywords"]) if sub_row["keywords"] else []
        except Exception:
            kw_list = []

        sub_prefs = {
            "disciplines": disc_list,
            "keywords": kw_list,
            "is_paid": paid,
        }

        # For free subscribers, append promotional upgrade prompt
        sub_ad_footer = ad_footer
        if not paid:
            free_promo = "[Notice] Free normal feed. Upgrade to Pro (MVR 50/mo) for custom keyword alerts: /pro"
            sub_ad_footer = f"{ad_footer}\n{free_promo}" if ad_footer else free_promo

        for bid in bids:
            notice_id = str(bid.get("notice_id") or bid.get("ref") or bid.get("id"))
            if not notice_id:
                continue

            # Check deduplication
            if not force_resend:
                if is_alert_already_sent(conn, notice_id, chat_id):
                    continue

                # Only send alerts of things received after the user started the bot
                if sub_started_at:
                    bid_created_at = bid.get("created_at")
                    if not bid_created_at:
                        row = conn.execute(
                            "SELECT created_at FROM bids WHERE notice_id = ? OR reference_number = ? LIMIT 1;",
                            (notice_id, notice_id),
                        ).fetchone()
                        if row and row[0]:
                            bid_created_at = row[0]
                    if bid_created_at and str(bid_created_at) <= sub_started_at:
                        continue

            # Check if bid matches subscriber's interest
            if matches_interest(bid, sub_prefs, is_paid=paid):
                msg_html = format_tender_alert_html(bid, ad_footer=sub_ad_footer)
                keyboard = build_tender_keyboard(bid, is_paid=paid)
                ok, err = tg.send_telegram_message(
                    msg_html,
                    chat_id=chat_id,
                    bot_token=token,
                    reply_markup=keyboard,
                )
                if ok:
                    record_alert_sent(conn, notice_id, chat_id)
                    if active_ad:
                        try:
                            record_ad_impression(conn, active_ad["id"])
                        except Exception:
                            pass
                    sent_records.append({
                        "notice_id": notice_id,
                        "chat_id": chat_id,
                        "title": bid.get("title"),
                        "status": "delivered",
                    })
                else:
                    sent_records.append({
                        "notice_id": notice_id,
                        "chat_id": chat_id,
                        "title": bid.get("title"),
                        "status": "failed",
                        "error": err,
                    })

    return sent_records


def dispatch_news_alerts(
    conn: sqlite3.Connection,
    articles: list[dict[str, Any]],
    bot_token: Optional[str] = None,
    force_resend: bool = False,
) -> list[dict[str, Any]]:
    """Iterates over news articles and sends Telegram alerts to matching active subscribers."""
    token, default_chat = get_telegram_credentials(bot_token=bot_token)
    if not token:
        logger.info("Telegram bot token not configured; skipping news dispatch")
        return []

    raw_subs = conn.execute(
        "SELECT id, chat_id, name, keywords, created_at FROM telegram_subscribers WHERE is_active = 1;"
    ).fetchall()
    subscribers = [dict(r) for r in raw_subs]

    # Include default broadcast channel if configured
    if default_chat and not any(str(s["chat_id"]) == str(default_chat) for s in subscribers):
        subscribers.append({
            "id": 0,
            "chat_id": str(default_chat),
            "name": "Main Broadcast Channel",
            "keywords": '["All"]',
            "created_at": None,
        })

    if not subscribers or not articles:
        return []

    sent_records: list[dict[str, Any]] = []

    from data.database import get_active_sponsored_ad, record_ad_impression, is_subscriber_paid
    active_ad = get_active_sponsored_ad(conn, target_category="news")
    # News posts stay clean without partner spotlight / sponsor ads
    ad_footer = None

    for sub_row in subscribers:
        chat_id = str(sub_row["chat_id"])
        sub_started_at = str(sub_row["created_at"] or "")
        paid = is_subscriber_paid(conn, chat_id)
        try:
            kw_list = json.loads(sub_row["keywords"]) if sub_row["keywords"] else []
        except Exception:
            kw_list = []

        for art in articles:
            art_id = str(art.get("id") or art.get("url") or "")
            if not art_id:
                continue

            alert_key = f"news-{art_id}"
            if not force_resend:
                if is_alert_already_sent(conn, alert_key, chat_id):
                    continue

                # Only send alerts of things received after the user started the bot
                if sub_started_at:
                    art_created_at = art.get("created_at")
                    if not art_created_at:
                        row = conn.execute("SELECT created_at FROM articles WHERE id = ? LIMIT 1;", (art_id,)).fetchone()
                        if row and row[0]:
                            art_created_at = row[0]
                    if art_created_at and str(art_created_at) <= sub_started_at:
                        continue

            if not matches_news_interest(art, kw_list, is_paid=paid):
                continue

            msg_html = format_news_alert_html(art, ad_footer=ad_footer)
            keyboard = build_news_keyboard(art)
            ok, status_msg = tg.send_telegram_message(
                msg_html,
                chat_id=chat_id,
                bot_token=token,
                reply_markup=keyboard,
            )
            if ok:
                record_alert_sent(conn, alert_key, chat_id)
                sent_records.append({"article_id": art_id, "chat_id": chat_id, "status": "delivered"})
                if active_ad:
                    try:
                        record_ad_impression(conn, active_ad["id"])
                    except Exception:
                        pass

                # Between every 5 posts, insert an actual ad served by our ad engine
                try:
                    if sub_started_at:
                        count_row = conn.execute(
                            "SELECT COUNT(*) FROM sent_alerts WHERE chat_id = ? AND sent_at > ?;",
                            (chat_id, sub_started_at),
                        ).fetchone()
                    else:
                        count_row = conn.execute(
                            "SELECT COUNT(*) FROM sent_alerts WHERE chat_id = ?;",
                            (chat_id,),
                        ).fetchone()
                    total_sent = count_row[0] if count_row else 0
                    if total_sent > 0 and total_sent % 5 == 0 and active_ad:
                        ad_msg = format_standalone_ad_post(active_ad)
                        ad_kb = None
                        if active_ad.get("link_url"):
                            ad_kb = {"inline_keyboard": [[{"text": f"Visit {active_ad.get('sponsor_name', 'Partner')} ↗", "url": active_ad["link_url"]}]]}
                        tg.send_telegram_message(ad_msg, chat_id=chat_id, bot_token=token, reply_markup=ad_kb)
                        record_ad_impression(conn, active_ad["id"])
                except Exception as ad_err:
                    logger.debug("Failed to dispatch 5th post standalone ad: %s", ad_err)
            else:
                sent_records.append({"article_id": art_id, "chat_id": chat_id, "status": "failed", "error": status_msg})

    return sent_records


def dispatch_obituary_alerts(
    conn: sqlite3.Connection,
    obituaries: list[dict[str, Any]],
    bot_token: Optional[str] = None,
    force_resend: bool = False,
) -> list[dict[str, Any]]:
    """Broadcast new Janaza / funeral announcements to active Telegram subscribers."""
    subscribers = conn.execute(
        "SELECT id, chat_id, name, keywords, created_at FROM telegram_subscribers WHERE is_active = 1;"
    ).fetchall()

    if not subscribers or not obituaries:
        return []

    token, _ = get_telegram_credentials(bot_token=bot_token)
    if not token:
        return []

    sent_records = []
    for sub_row in subscribers:
        chat_id = str(sub_row["chat_id"])
        sub_started_at = str(sub_row["created_at"] or "")
        for ob in obituaries:
            ob_id = str(ob.get("id") or ob.get("slug") or "")
            alert_key = f"janaza-{ob_id}"
            if not force_resend:
                if is_alert_already_sent(conn, alert_key, chat_id):
                    continue

                # Only send alerts of things received after the user started the bot
                if sub_started_at:
                    ob_created_at = ob.get("created_at")
                    if not ob_created_at:
                        row = conn.execute(
                            "SELECT created_at FROM obituaries WHERE slug = ? OR id = ? LIMIT 1;",
                            (ob_id, ob_id),
                        ).fetchone()
                        if row and row[0]:
                            ob_created_at = row[0]
                    if ob_created_at and str(ob_created_at) <= sub_started_at:
                        continue

            msg_html = format_obituary_alert_html(ob)
            keyboard = build_obituary_keyboard(ob)
            ok, status_msg = tg.send_telegram_message(
                msg_html,
                chat_id=chat_id,
                bot_token=token,
                reply_markup=keyboard,
            )
            if ok:
                record_alert_sent(conn, alert_key, chat_id)
                sent_records.append({"obituary_id": ob_id, "chat_id": chat_id, "status": "delivered"})
            else:
                sent_records.append({"obituary_id": ob_id, "chat_id": chat_id, "status": "failed", "error": status_msg})

    return sent_records


def dispatch_job_alerts(
    job: dict[str, Any],
    conn: Optional[sqlite3.Connection] = None,
    bot_token: Optional[str] = None,
    session: Optional[requests.Session] = None,
) -> dict[str, Any]:
    """Broadcast job vacancy notification to matching registered users and Telegram alert subscribers."""
    token, _ = get_telegram_credentials(bot_token=bot_token)
    if not token:
        return {"delivered": 0, "failed": 0, "reason": "No bot token"}

    close_conn = False
    if conn is None:
        from data.database import get_db
        ctx = get_db()
        conn = ctx.__enter__()
        close_conn = True

    try:
        notice_id = str(job.get("notice_id") or job.get("id") or "")
        alert_key = f"job-{notice_id}"
        job_discipline = (job.get("discipline") or "Other").lower()

        # Gather target chat IDs from:
        # 1. Registered users with telegram_chat_id
        target_chats: set[str] = set()

        user_rows = conn.execute(
            "SELECT telegram_chat_id, job_alert_categories FROM users WHERE telegram_chat_id IS NOT NULL AND telegram_chat_id != '';"
        ).fetchall()
        for u in user_rows:
            cid = str(u["telegram_chat_id"]).strip()
            cats_raw = u["job_alert_categories"] or '["all"]'
            try:
                cats = [c.lower() for c in json.loads(cats_raw)]
            except Exception:
                cats = ["all"]
            if "all" in cats or job_discipline in cats or any(c in job_discipline for c in cats):
                target_chats.add(cid)

        # 2. General telegram subscribers who have 'jobs' in keywords or relevant discipline
        sub_rows = conn.execute(
            "SELECT chat_id, disciplines, keywords FROM telegram_subscribers WHERE is_active = 1;"
        ).fetchall()
        for s in sub_rows:
            cid = str(s["chat_id"]).strip()
            keywords_raw = s["keywords"] or "[]"
            disc_raw = s["disciplines"] or "[]"
            try:
                kws = [k.lower() for k in json.loads(keywords_raw)]
            except Exception:
                kws = []
            try:
                discs = [d.lower() for d in json.loads(disc_raw)]
            except Exception:
                discs = []

            if "jobs" in kws or "all" in discs or any(d in job_discipline for d in discs):
                target_chats.add(cid)

        # 3. Default broadcast channel if configured
        if default_chat:
            target_chats.add(str(default_chat).strip())

        msg_html = format_job_alert_html(job)
        delivered = 0
        failed = 0

        for chat_id in target_chats:
            if is_alert_already_sent(conn, alert_key, chat_id):
                continue
            ok, _ = tg.send_telegram_message(msg_html, chat_id=chat_id, bot_token=token, session=session)
            if ok:
                record_alert_sent(conn, alert_key, chat_id)
                delivered += 1
            else:
                failed += 1

        return {"delivered": delivered, "failed": failed, "total_targets": len(target_chats)}
    finally:
        if close_conn:
            ctx.__exit__(None, None, None)


TOPIC_KEYS = [
    ("ras-male", "Ras Malé"),
    ("sultan-park", "Sultan Park"),
    ("tgst", "TGST & Tax"),
    ("green-tax", "Green Tax"),
    ("bridge-safety", "Bridge Safety"),
]

DISCIPLINE_KEYS = [
    ("Construction", "Construction"),
    ("IT", "IT & Telecom"),
    ("Logistics", "Marine & Logistics"),
    ("Healthcare", "Healthcare"),
]


from alerts.telegram_broadcast import dispatch_sponsored_broadcast
