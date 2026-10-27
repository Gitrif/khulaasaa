from __future__ import annotations

import alerts.telegram as tg
"""
Telegram Bot Webhook Update Handler and Background Polling Service.
"""

import html
import json
import logging
import os
import threading
import time
from typing import Any, Optional

import requests

from data.database import (
    get_db,
    register_or_update_telegram_subscriber,
    get_telegram_subscriber,
    update_telegram_subscriber_plan,
    is_subscriber_paid,
    query_bids,
    query_jobs,
    list_obituaries,
)
from alerts.telegram_client import (
    DISCIPLINE_KEYS,
    get_telegram_credentials,
    send_telegram_message,
    edit_telegram_message,
    answer_telegram_callback_query,
    set_telegram_chat_menu_button,
    DEFAULT_TELEGRAM_BOT_TOKEN,
)
from alerts.telegram_formatters import (
    format_tender_alert_html,
    build_tender_keyboard,
    format_job_alert_html,
    format_obituary_alert_html,
    format_pro_tier_message,
    build_settings_keyboard_and_text,
)

logger = logging.getLogger(__name__)

def handle_incoming_telegram_update(update: dict[str, Any]) -> None:
    """Handle an update from Telegram Bot API (message, /commands, or callback_query)."""
    from data.database import (
        get_db,
        register_or_update_telegram_subscriber,
        get_telegram_subscriber,
        is_subscriber_paid,
        query_bids,
    )

    # 1. Handle Inline Keyboard Toggles (callback_query)
    callback = update.get("callback_query")
    if callback:
        cb_id = callback.get("id")
        cb_data = callback.get("data") or ""
        msg = callback.get("message") or {}
        msg_id = msg.get("message_id")
        chat = msg.get("chat") or {}
        chat_id = str(chat.get("id") or callback.get("from", {}).get("id") or "")

        if not chat_id:
            return

        with get_db() as conn:
            sub = get_telegram_subscriber(conn, chat_id)
            paid = is_subscriber_paid(conn, chat_id)
            if not sub:
                from_u = callback.get("from") or {}
                uname = from_u.get("username")
                fname = from_u.get("first_name", "User")
                display_name = f"{fname} (@{uname})" if uname else fname
                sub = {
                    "chat_id": chat_id,
                    "name": display_name,
                    "disciplines": ["All"],
                    "keywords": ["all_news", "breaking", "janaza", "ras-male", "sultan-park", "tgst"],
                    "is_active": 1,
                    "is_paid": 1 if paid else 0,
                }

            if cb_data == "upgrade:pro":
                pro_text, pro_kb = format_pro_tier_message(paid, chat_id)
                if msg_id:
                    tg.edit_telegram_message(chat_id, msg_id, pro_text, reply_markup=pro_kb)
                else:
                    tg.send_telegram_message(pro_text, chat_id=chat_id, reply_markup=pro_kb)
                if cb_id:
                    tg.answer_telegram_callback_query(cb_id, text="Khulaasaa Pro (MVR 50/mo)")
                return

            disciplines = list(sub.get("disciplines") or [])
            keywords = list(sub.get("keywords") or [])

            feedback = "Updated"
            if cb_data == "open:settings":
                pass
            elif cb_data == "toggle:breaking":
                if "breaking" in keywords:
                    keywords.remove("breaking")
                    feedback = "Breaking News Muted"
                else:
                    keywords.append("breaking")
                    feedback = "Breaking News Active"
            elif cb_data == "toggle:all_news":
                if "all_news" in keywords:
                    keywords.remove("all_news")
                    feedback = "All News Muted"
                else:
                    keywords.append("all_news")
                    feedback = "All News Active"
            elif cb_data == "toggle:janaza":
                if "janaza" in keywords:
                    keywords.remove("janaza")
                    feedback = "Janaza / Obituaries Muted"
                else:
                    keywords.append("janaza")
                    feedback = "Janaza / Obituaries Active"
            elif cb_data == "toggle:tenders":
                if "All" in disciplines or any(d in disciplines for d, _ in DISCIPLINE_KEYS):
                    disciplines = []
                    feedback = "Tender Alerts Muted"
                else:
                    disciplines = ["All"]
                    feedback = "Tender Alerts Active"
            elif cb_data == "toggle:jobs":
                if "jobs" in keywords:
                    keywords.remove("jobs")
                    feedback = "Job Alerts Muted"
                else:
                    keywords.append("jobs")
                    feedback = "Job Alerts Active"
            elif cb_data == "toggle:rentals":
                feedback = "Rentals aggregation is on the Phase 3 Roadmap!"
            elif cb_data.startswith("topic:"):
                slug = cb_data.split(":", 1)[1]
                if slug in keywords:
                    keywords.remove(slug)
                    feedback = f"Unfollowed {slug}"
                else:
                    keywords.append(slug)
                    feedback = f"Following {slug}"
            elif cb_data.startswith("disc:"):
                disc = cb_data.split(":", 1)[1]
                if "All" in disciplines:
                    disciplines = [d for d, _ in DISCIPLINE_KEYS if d != disc]
                    feedback = f"Muted {disc}"
                elif disc in disciplines:
                    disciplines.remove(disc)
                    feedback = f"Muted {disc}"
                else:
                    disciplines.append(disc)
                    feedback = f"Subscribed {disc}"

            # Save updated preferences
            sub["disciplines"] = disciplines
            sub["keywords"] = keywords
            register_or_update_telegram_subscriber(
                conn,
                chat_id=chat_id,
                name=sub.get("name"),
                disciplines=disciplines,
                keywords=keywords,
                is_active=1,
            )

        if cb_id:
            tg.answer_telegram_callback_query(cb_id, text=feedback)

        if msg_id:
            new_text, new_kb = build_settings_keyboard_and_text(sub, is_paid=paid)
            tg.edit_telegram_message(chat_id, msg_id, new_text, reply_markup=new_kb)
        return

    # 2. Handle Text Messages and Commands
    message = update.get("message")
    if not message:
        return

    chat = message.get("chat", {})
    chat_id = str(chat.get("id", ""))
    from_user = message.get("from", {})
    first_name = from_user.get("first_name", "")
    username = from_user.get("username", "")
    name = f"{first_name} (@{username})" if username else (first_name or "Telegram User")
    text = (message.get("text") or "").strip()

    if not chat_id or not text:
        return

    if text.startswith("/pro"):
        with get_db() as conn:
            paid = is_subscriber_paid(conn, chat_id)
        pro_text, pro_kb = format_pro_tier_message(paid, chat_id)
        tg.send_telegram_message(pro_text, chat_id=chat_id, reply_markup=pro_kb)

    elif text.startswith("/link") or (text.startswith("/start") and len(text.split(maxsplit=1)) > 1 and text.split(maxsplit=1)[1].startswith("link_")):
        parts = text.split(maxsplit=1)
        raw_token = parts[1].strip()
        if raw_token.startswith("link_"):
            raw_token = raw_token[5:].strip()

        with get_db() as conn:
            from services.channel_linking_service import verify_and_link_channel
            ok, msg, uid = verify_and_link_channel(conn, "telegram", raw_token, chat_id, name)

        if ok:
            tg.send_telegram_message(
                "<b>Khulaasaa Account Linked</b>\n\n"
                "Your Telegram channel is successfully verified and linked to your Khulaasaa account. "
                "You will receive alerts according to your notification preferences.",
                chat_id=chat_id,
            )
        else:
            tg.send_telegram_message(
                f"<b>Linking Failed</b>\n\n{msg}",
                chat_id=chat_id,
            )
        return

    elif text.startswith("/start"):
        # Check for deep linking payload (e.g. /start alerts_breaking_followed or /start tenders)
        parts = text.split(maxsplit=1)
        payload = parts[1].strip() if len(parts) > 1 else ""

        disciplines: list[str] = []
        keywords: list[str] = []

        if payload:
            p_lower = payload.lower()
            if "breaking" in p_lower:
                keywords.append("breaking")
            if "followed" in p_lower or "stories" in p_lower or "story" in p_lower:
                keywords.extend(["ras-male", "sultan-park", "tgst", "bridge-safety"])
            if "tender" in p_lower or "bid" in p_lower:
                found_discs = [d for d, _ in DISCIPLINE_KEYS if d.lower().replace(" ", "").replace("&", "") in p_lower]
                disciplines = found_discs if found_discs else ["All"]

            # If payload had nothing recognized, default to all alerts active
            if not keywords and not disciplines:
                disciplines = ["All"]
                keywords = ["all_news", "breaking", "janaza", "ras-male", "sultan-park", "tgst"]
        else:
            # Default /start without payload: ALL feeds active
            disciplines = ["All"]
            keywords = ["all_news", "breaking", "janaza", "ras-male", "sultan-park", "tgst"]

        # Auto-register or refresh subscriber preferences
        with get_db() as conn:
            register_or_update_telegram_subscriber(
                conn,
                chat_id=chat_id,
                name=name,
                disciplines=disciplines,
                keywords=keywords,
                is_active=1,
                reset_start_time=True,
            )
            sub = get_telegram_subscriber(conn, chat_id)
            paid = is_subscriber_paid(conn, chat_id)

        # Build list of active channels for the welcome message
        active_items = []
        if "all_news" in keywords:
            active_items.append("• <b>All News</b> (real-time briefings & summaries)")
        if "breaking" in keywords:
            active_items.append("• <b>Breaking News</b> (urgent alerts)")
        if "janaza" in keywords:
            active_items.append("• <b>Janaza & Obituaries</b> (funeral notices across Maldives)")
        if disciplines:
            discs_str = "All Disciplines" if "All" in disciplines else ", ".join(disciplines)
            active_items.append(f"• <b>Government Tenders</b> ({discs_str})")
        if any(k in keywords for k in ["ras-male", "sultan-park", "tgst", "bridge-safety"]):
            active_items.append("• <b>Followed Storylines</b> (Ras Malé, Tax reforms, infrastructure)")
        if "jobs" in keywords:
            active_items.append("• <b>Job Vacancies</b> (Civil service, SOEs & Gazette)")

        if not active_items:
            active_desc = "<i>Alerts currently muted. Tap Settings below to enable channels anytime.</i>"
        else:
            active_desc = "\n".join(active_items)

        _, kb = build_settings_keyboard_and_text(sub, is_paid=paid)
        tier_status = "<b>Plan: [PRO] Pro Tier (Active)</b>" if paid else "<b>Plan: Free Tier (Normal Feed)</b> — Upgrade: /pro"
        welcome_text = (
            f"<b>Maruhabaa, {html.escape(first_name or 'Friend')}!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>You are connected to Khulaasaa!</b>\n"
            f"Telegram ID: <code>{chat_id}</code>\n"
            f"{tier_status}\n\n"
            f"<b>Active Alert Channels (All enabled by default):</b>\n"
            f"{active_desc}\n\n"
            f"Tap any button below to toggle feeds, or tap <b>Filter Preferences on Web ↗</b> for detailed filters:"
        )

        tg.send_telegram_message(welcome_text, chat_id=chat_id, reply_markup=kb)

    elif text.startswith("/settings"):
        with get_db() as conn:
            sub = get_telegram_subscriber(conn, chat_id)
            paid = is_subscriber_paid(conn, chat_id)
        settings_text, kb = build_settings_keyboard_and_text(sub, is_paid=paid)
        tg.send_telegram_message(settings_text, chat_id=chat_id, reply_markup=kb)

    elif text.startswith("/tenders"):
        with get_db() as conn:
            recent_bids = query_bids(conn, limit=3, open_only=True)
            if not recent_bids:
                recent_bids = query_bids(conn, limit=3)

        if not recent_bids:
            tg.send_telegram_message("No active tenders found right now. Check back shortly!", chat_id=chat_id)
            return

        lines = [
            "<b>LATEST GOVERNMENT TENDERS — Khulaasaa</b>",
            "━━━━━━━━━━━━━━━━━━━━━━",
        ]
        for b in recent_bids:
            t_en = b.get("title_en") or b.get("title") or "Tender"
            agency = b.get("agency_name_en") or b.get("agency") or "Public Body"
            disc = b.get("discipline") or "General"
            deadline = b.get("submission_date") or b.get("deadline_iso") or "TBD"
            src_url = b.get("source_url") or "https://gazette.gov.mv"
            lines.extend([
                f"<b>{html.escape(disc)}</b> | {html.escape(agency)}",
                f"<a href=\"{html.escape(src_url)}\">{html.escape(t_en)}</a>",
                f"Deadline: <code>{html.escape(deadline)}</code>",
                "",
            ])
        app_url = os.environ.get("APP_URL", "https://khulaasaa.tech").strip()
        lines.append(f"<i>More tenders & filters at:</i> {app_url}/bids")

        tenders_kb = []
        if app_url:
            tenders_kb.append([{"text": "Browse All Tenders ↗", "url": f"{app_url}/bids"}])
        tenders_kb.append([{"text": "Configure Tender Alerts", "callback_data": "open:settings"}])

        tg.send_telegram_message("\n".join(lines), chat_id=chat_id, reply_markup={"inline_keyboard": tenders_kb})

    elif text.startswith("/breaking"):
        app_url = os.environ.get("APP_URL", "https://khulaasaa.tech").strip()
        msg = (
            "<b>BREAKING NEWS MONITOR — Khulaasaa</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "All active news stories are cross-referenced across Sun, Avas, Mihaaru, Edition, and PSM News.\n\n"
            "Active developing topics in the Maldives:\n"
            "• <b>Ras Malé Project</b> — Land reclamation & developer tenders\n"
            "• <b>Sultan Park Renovation</b> — Infrastructure & heritage development\n"
            "• <b>TGST & Green Tax Reforms</b> — Tourism tax changes\n"
            "• <b>Sinamalé Bridge Safety</b> — Traffic management & vehicle lane rules\n\n"
            f"<i>Follow stories on the live feed:</i> {app_url}"
        )
        breaking_kb = [
            [{"text": "Configure Alert Topics", "callback_data": "open:settings"}]
        ]
        tg.send_telegram_message(msg, chat_id=chat_id, reply_markup={"inline_keyboard": breaking_kb})

    elif text.startswith("/follow"):
        msg = (
            "<b>FOLLOWED TOPICS & TIMELINES</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "You can follow key national issues and receive push updates whenever new articles or gazette notices appear:\n\n"
            "1. <b>#ras-male</b>: Dredging, foreign contractors, housing financing\n"
            "2. <b>#sultan-park</b>: City Council approvals & heritage works\n"
            "3. <b>#tgst</b>: MIRA revenue acts and resort sector impact\n"
            "4. <b>#bridge-safety</b>: Police enforcement & surveillance\n\n"
            "To follow topics instantly, use <b>/settings</b> or tap below."
        )
        follow_kb = [
            [{"text": "Toggle Followed Topics", "callback_data": "open:settings"}]
        ]
        tg.send_telegram_message(msg, chat_id=chat_id, reply_markup={"inline_keyboard": follow_kb})

    elif text.startswith("/help"):
        with get_db() as conn:
            paid = is_subscriber_paid(conn, chat_id)
        plan_line = "<b>Plan:</b> [PRO] Pro Tier (Active — MVR 50/mo)" if paid else "<b>Plan:</b> Free Tier (Normal Feed) — Upgrade for custom alerts: /pro"
        msg = (
            "<b>Khulaasaa Bot Help</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{plan_line}\n\n"
            "Khulaasaa is an automated aggregator tracking Maldivian news and government procurement.\n\n"
            "• <b>/pro</b> — Upgrade to Pro (MVR 50/mo) for customized alerts\n"
            "• <b>/settings</b> — Choose which updates you receive (interactive buttons)\n"
            "• <b>/tenders</b> — Check recent government procurement\n"
            "• <b>/breaking</b> — Verified breaking news\n"
            "• <b>/follow</b> — Developing story topics\n"
            "• <b>/start</b> — Reset or verify your subscription\n\n"
            f"Your Chat ID: <code>{html.escape(chat_id)}</code>\n"
            "Use this Chat ID on the Khulaasaa website to connect your Telegram."
        )
        help_kb = [
            [{"text": "[PRO] Pro Tier (MVR 50/mo)", "callback_data": "upgrade:pro"}],
            [{"text": "Open Settings", "callback_data": "open:settings"}],
        ]
        tg.send_telegram_message(msg, chat_id=chat_id, reply_markup={"inline_keyboard": help_kb})


_BOT_POLLING_ACTIVE = False
_BOT_POLLING_THREAD: Optional[threading.Thread] = None


def _telegram_bot_polling_worker(bot_token: str) -> None:
    """Long-polling worker that retrieves updates from Telegram Bot API."""
    offset = 0
    session = requests.Session()
    logger.info("Telegram bot polling started for token %s...", bot_token[:8])
    while _BOT_POLLING_ACTIVE:
        try:
            url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
            params = {"offset": offset, "timeout": 20}
            resp = session.get(url, params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok"):
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        try:
                            handle_incoming_telegram_update(update)
                        except Exception as e:
                            logger.error("Error processing Telegram update %s: %s", update.get("update_id"), e)
            elif resp.status_code == 409:
                # Webhook or another poll is active, sleep and retry
                time.sleep(5)
            else:
                time.sleep(3)
        except Exception as exc:
            logger.debug("Telegram polling exception: %s", exc)
            time.sleep(3)


def start_telegram_bot_polling(bot_token: Optional[str] = None) -> bool:
    """Start background long-polling for the bot if token is configured."""
    global _BOT_POLLING_ACTIVE, _BOT_POLLING_THREAD
    token, _ = get_telegram_credentials(bot_token=bot_token)
    if not token:
        return False
    if _BOT_POLLING_ACTIVE:
        return True

    _BOT_POLLING_ACTIVE = True
    _BOT_POLLING_THREAD = threading.Thread(
        target=_telegram_bot_polling_worker,
        args=(token,),
        daemon=True,
        name="TelegramBotPolling",
    )
    _BOT_POLLING_THREAD.start()
    return True
