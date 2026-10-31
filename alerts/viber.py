"""
Viber Bot Webhook Handler & Dispatcher for Khulaasaa.
"""
from __future__ import annotations

import html
import json
import logging
import os
from typing import Any, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

from data.database import (
    get_db,
    register_or_update_viber_subscriber,
    upsert_platform_identity,
    mark_platform_identity_inactive,
    get_viber_subscribers,
    unsubscribe_viber_subscriber,
    is_viber_subscriber_paid,
    list_obituaries,
    query_bids,
    query_jobs,
    get_viber_subscriber,
)

# Re-export client functions and constants
from alerts.viber_client import (
    VIBER_API_BASE,
    DEFAULT_VIBER_BOT_TOKEN,
    DEFAULT_VIBER_BOT_NAME,
    DEFAULT_VIBER_BOT_AVATAR,
    get_viber_credentials,
    build_viber_main_keyboard,
    set_viber_webhook,
    send_viber_message,
    send_viber_picture,
    clean_news_summary,
    format_viber_sponsored_block,
    format_viber_news,
    send_viber_news_post,
    format_viber_obituary,
    format_viber_bid,
    format_viber_job,
)

logger = logging.getLogger(__name__)

def handle_viber_webhook_event(event_data: dict[str, Any], base_url: str = "https://khulaasaa.tech") -> dict[str, Any]:
    """
    Process incoming Viber webhook events and return the response payload.
    Handles 'conversation_started', 'subscribed', 'unsubscribed', and 'message'.
    """
    event = event_data.get("event")
    keyboard = build_viber_main_keyboard(base_url)

    # 1. Viber Webhook validation ping
    if event == "webhook":
        return {"status": 0, "message": "ok"}

    # 2. Conversation Started (when user opens 1-on-1 chat in Viber)
    if event == "conversation_started":
        user = event_data.get("user") or {}
        user_id = user.get("id")
        user_name = user.get("name", "Reader")
        if user_id:
            try:
                with get_db() as conn:
                    register_or_update_viber_subscriber(
                        conn, viber_user_id=user_id, name=user_name,
                        avatar=user.get("avatar"),
                        categories=["all", "news", "janaza", "bids", "jobs"], is_active=1,
                    )
                    upsert_platform_identity(
                        conn, "viber", user_id, provider_username=None,
                        display_name=user_name, is_active=True,
                    )
            except Exception as e:
                logger.error("Error auto-subscribing Viber user on conversation_started: %s", e)

        ctx = str(event_data.get("context") or "").strip()
        if user_id and (ctx.startswith("link_") or (len(ctx) == 6 and ctx.isdigit())):
            c_tok = ctx[5:].strip() if ctx.startswith("link_") else ctx
            try:
                with get_db() as conn:
                    from services.channel_linking_service import verify_and_link_channel
                    verify_and_link_channel(conn, "viber", c_tok, user_id, user_name)
            except Exception:
                pass

        welcome_text = (
            f"Assalaamu Alaikum, {user_name}!\n\n"
            f"Welcome to Khulaasaa! You are automatically subscribed to real-time Maldives alerts:\n"
            f"- Breaking & Verified News\n"
            f"- Janaza & Funeral Notices\n"
            f"- Government Gazette Tenders\n"
            f"- Job Vacancies & Free CV Builder\n\n"
            f"Your Viber ID:\n{user_id}\n\n"
            f"Tap an option below to browse news, funeral notices, tenders, or jobs:"
        )
        return {
            "type": "text",
            "text": welcome_text,
            "keyboard": keyboard,
        }

    # 3. Subscribed Event
    if event == "subscribed":
        user = event_data.get("user") or {}
        user_id = user.get("id")
        user_name = user.get("name", "Reader")
        if user_id:
            with get_db() as conn:
                register_or_update_viber_subscriber(
                    conn, viber_user_id=user_id, name=user_name,
                    avatar=user.get("avatar"),
                    categories=["all", "news", "janaza", "bids", "jobs"], is_active=1,
                )
                upsert_platform_identity(conn, "viber", user_id, display_name=user_name, is_active=True)
            send_viber_message(
                user_id,
                f"Subscribed to Khulaasaa alerts!\n\nYour Viber ID: {user_id}\n\nYou will receive real-time news, Janaza announcements, tenders, and job postings.",
                keyboard=keyboard,
            )
        return {"status": 0}

    # 4. Unsubscribed Event
    if event == "unsubscribed":
        user_id = event_data.get("user_id")
        if user_id:
            with get_db() as conn:
                unsubscribe_viber_subscriber(conn, user_id)
                mark_platform_identity_inactive(conn, "viber", user_id)
        return {"status": 0}

    # 5. Incoming Message Event
    if event == "message":
        sender = event_data.get("sender") or {}
        user_id = sender.get("id")
        user_name = sender.get("name", "Reader")
        msg = event_data.get("message") or {}
        raw_msg = (msg.get("text") or "").strip()
        msg_text = raw_msg.lower()

        if not user_id:
            return {"status": 0}

        # Check for channel verification linking token
        if msg_text.startswith("link ") or (len(raw_msg) == 6 and raw_msg.isdigit()):
            tok = raw_msg.split(maxsplit=1)[1].strip() if msg_text.startswith("link ") else raw_msg
            with get_db() as conn:
                from services.channel_linking_service import verify_and_link_channel
                ok, res_msg, uid = verify_and_link_channel(conn, "viber", tok, user_id, user_name)
            if ok:
                send_viber_message(
                    user_id,
                    "Khulaasaa Account Linked\n\nYour Viber channel is successfully verified and linked to your Khulaasaa account.",
                    keyboard=keyboard,
                )
                return {"status": 0}
            else:
                send_viber_message(user_id, f"Linking Failed: {res_msg}", keyboard=keyboard)
                return {"status": 0}

        # Auto-subscribe if from Viber first
        try:
            with get_db() as conn:
                register_or_update_viber_subscriber(
                    conn, viber_user_id=user_id, name=user_name,
                    avatar=sender.get("avatar"),
                    categories=["all", "news", "janaza", "bids", "jobs"], is_active=1,
                )
                upsert_platform_identity(conn, "viber", user_id, display_name=user_name, is_active=True)
        except Exception as e:
            logger.error("Error auto-subscribing Viber user on message: %s", e)

        # Handle Commands
        if msg_text in ["/start", "start", "hi", "hello", "hey", "/subscribe", "subscribe"]:
            welcome_reply = (
                f"Assalaamu Alaikum, {user_name}!\n\n"
                f"You are actively subscribed to Khulaasaa alerts:\n"
                f"• Breaking & Verified News\n"
                f"• Janaza Notices (ކަށުނަމާދު)\n"
                f"• Government Tenders (ބީލަން)\n"
                f"• Job Vacancies & Free CV Builder\n\n"
                f"Your Viber ID: {user_id}\n\n"
                f"Tap an option below to explore:"
            )
            send_viber_message(user_id, welcome_reply, keyboard=keyboard)

        elif msg_text in ["/myid", "myid", "id", "whoami", "/id"]:
            id_reply = (
                f"Your Viber User ID:\n\n"
                f"{user_id}\n\n"
                f"You can use this ID on https://khulaasaa.tech/jobs/cv or in Web Alert Preferences to receive direct alerts!"
            )
            send_viber_message(user_id, id_reply, keyboard=keyboard)

        elif msg_text in ["/cv", "cv"]:
            cv_reply = (
                f"Build your Maldivian CV (Free):\n\n"
                f"Create a verified, ATS-friendly CV formatted specifically for Maldivian government and corporate jobs.\n\n"
                f"{base_url}/jobs/cv"
            )
            send_viber_message(user_id, cv_reply, keyboard=keyboard)

        elif msg_text in ["/unsubscribe", "unsubscribe", "/stop", "stop"]:
            with get_db() as conn:
                unsubscribe_viber_subscriber(conn, user_id)
            send_viber_message(
                user_id,
                "You have been unsubscribed from Khulaasaa alerts. Send /subscribe or /start anytime to re-enable alerts.",
                keyboard=keyboard,
            )

        elif msg_text in ["/pro", "pro", "/premium", "premium"]:
            with get_db() as conn:
                paid = is_viber_subscriber_paid(conn, user_id)
            if paid:
                pro_reply = (
                    "Khulaasaa Pro (Active Subscription)\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "Status: ACTIVE (MVR 50 / month)\n\n"
                    "Your Pro Benefits:\n"
                    "• Custom Tender Alerts by Industry\n"
                    "• Real-time Business Keyword Tracking\n"
                    "• Storyline Topic Alerts\n"
                    "• Immediate Priority Delivery\n\n"
                    f"Viber ID: {user_id}\n"
                    f"Web Dashboard: {base_url}/alerts"
                )
            else:
                pro_reply = (
                    "Upgrade to Khulaasaa Pro (MVR 50 / month)\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "Current Plan: Free Tier (Normal Feed)\n\n"
                    "Free users receive the standard broadcast of all tenders and news. "
                    "Upgrade to Pro to receive customized alerts filtered specifically for your business!\n\n"
                    "Pro Features:\n"
                    "• Custom Industry Filters (Construction, IT, Logistics, Healthcare, etc.)\n"
                    "• Precision Business Keyword Alerts (solar, catering, audit, etc.)\n"
                    "• High-priority instant push delivery\n\n"
                    "How to Activate Pro (MVR 50 / month):\n"
                    "1. Transfer MVR 50 to BML: 7730000123456 (Khulaasaa)\n"
                    f"2. Mention your Viber ID in remark: {user_id}\n"
                    f"3. Send the transfer slip to support or activate at: {base_url}/pro?viber_id={user_id}"
                )
            send_viber_message(user_id, pro_reply, keyboard=keyboard)

        elif msg_text in ["/alerts", "alerts", "/settings", "settings"]:
            with get_db() as conn:
                paid = is_viber_subscriber_paid(conn, user_id)
            plan_badge = "Pro Tier (Active — MVR 50/mo)" if paid else "Free Tier (Normal Feed — /pro to customize)"
            alerts_text = (
                f"Khulaasaa Alert Status:\n\n"
                f"• Status: Active\n"
                f"• Subscription Plan: {plan_badge}\n"
                f"• Channels: News, Janaza, Bids, Jobs\n"
                f"• Viber ID: {user_id}\n\n"
                f"To adjust your preferences or link your CV profile, visit {base_url}/jobs/cv or use the buttons below."
            )
            send_viber_message(user_id, alerts_text, keyboard=keyboard)

        elif msg_text in ["/news", "latest news", "news", "ޙަބަރު"]:
            from scrapers.news import fetch_all_live_news
            try:
                articles = fetch_all_live_news()[:3]
                if articles:
                    for art in articles:
                        send_viber_news_post(user_id, art, base_url=base_url, keyboard=keyboard)
                else:
                    send_viber_message(user_id, "No new articles found right now.", keyboard=keyboard)
            except Exception as e:
                send_viber_message(user_id, f"Error fetching news: {e}", keyboard=keyboard)

        elif msg_text in ["/janaza", "janaza", "ކަށުނަމާދު", "kashunamaadhu"]:
            with get_db() as conn:
                obs = list_obituaries(conn, limit=3, active_only=True)
            if obs:
                for ob in obs:
                    send_viber_message(user_id, format_viber_obituary(ob, base_url), keyboard=keyboard)
            else:
                send_viber_message(user_id, "No active Janaza announcements right now.", keyboard=keyboard)

        elif msg_text in ["/bids", "bids", "tenders", "ބީލަން"]:
            with get_db() as conn:
                bids = query_bids(conn, limit=3, active_only=True)
            if bids:
                for b in bids:
                    send_viber_message(user_id, format_viber_bid(b, base_url), keyboard=keyboard)
            else:
                send_viber_message(user_id, "No active bids found right now.", keyboard=keyboard)

        elif msg_text in ["/jobs", "jobs", "vazeefaa", "vacancies", "career", "ވަޒީފާ"]:
            with get_db() as conn:
                from data.database import query_jobs
                jobs = query_jobs(conn, limit=3)
            if jobs:
                for j in jobs:
                    send_viber_message(user_id, format_viber_job(j, base_url), keyboard=keyboard)
            else:
                send_viber_message(user_id, f"No active job vacancies found right now. Visit {base_url}/jobs for the latest listings.", keyboard=keyboard)

        else:
            # Default Help response
            with get_db() as conn:
                paid = is_viber_subscriber_paid(conn, user_id)
            plan_str = "Pro Tier (Active)" if paid else "Free Tier (Normal Feed — /pro to customize)"
            help_text = (
                f"Khulaasaa Bot Commands:\n\n"
                f"• Plan: {plan_str}\n"
                f"• /pro — Upgrade to Pro (MVR 50/mo) for customized alerts\n"
                f"• /news — Latest multi-outlet news stories\n"
                f"• /janaza — Funeral & Janaza notices (ކަށުނަމާދު)\n"
                f"• /bids — Active government tenders\n"
                f"• /jobs — Verified job vacancies & Maldivian CV creator\n"
                f"• /myid — View your Viber ID for web linking\n"
                f"• /cv — Link to Free Maldivian CV Builder\n\n"
                f"Your Viber ID: {user_id}\n\n"
                f"Or use the buttons below:"
            )
            send_viber_message(user_id, help_text, keyboard=keyboard)

        return {"status": 0}

    return {"status": 0}


def dispatch_viber_news_alerts(
    articles: list[dict[str, Any]],
    bot_token: Optional[str] = None,
    base_url: str = "https://khulaasaa.tech",
) -> int:
    """Broadcast major breaking news articles to all active Viber subscribers."""
    token, _, _ = get_viber_credentials(bot_token)
    if not token or not articles:
        return 0

    with get_db() as conn:
        subscribers = get_viber_subscribers(conn, active_only=True)
    if not subscribers:
        return 0

    keyboard = build_viber_main_keyboard(base_url)
    delivered = 0
    for art in articles[:2]:
        for sub in subscribers:
            res = send_viber_news_post(sub["viber_user_id"], art, base_url=base_url, keyboard=keyboard, bot_token=token)
            if res.get("status") == 0:
                delivered += 1
    return delivered


def dispatch_viber_obituary_alerts(
    obituaries: list[dict[str, Any]],
    bot_token: Optional[str] = None,
    base_url: str = "https://khulaasaa.tech",
) -> int:
    """Broadcast new funeral announcements to all active Viber subscribers."""
    token, _, _ = get_viber_credentials(bot_token)
    if not token or not obituaries:
        return 0

    with get_db() as conn:
        subscribers = get_viber_subscribers(conn, active_only=True)
    if not subscribers:
        return 0

    keyboard = build_viber_main_keyboard(base_url)
    delivered = 0
    for ob in obituaries:
        msg_text = format_viber_obituary(ob, base_url)
        for sub in subscribers:
            res = send_viber_message(sub["viber_user_id"], msg_text, keyboard=keyboard, bot_token=token)
            if res.get("status") == 0:
                delivered += 1
    return delivered


def dispatch_viber_job_alerts(
    jobs: Any, bot_token: Optional[str] = None, base_url: str = "https://khulaasaa.tech"
) -> int:
    """Broadcast new job announcements to all active Viber subscribers."""
    if not isinstance(jobs, list) and isinstance(bot_token, list):
        jobs, bot_token = bot_token, None
    if not isinstance(jobs, list) or not jobs:
        return 0
    token, _, _ = get_viber_credentials(bot_token)
    if not token:
        return 0

    with get_db() as conn:
        subscribers = get_viber_subscribers(conn, active_only=True)
    if not subscribers:
        return 0

    keyboard = build_viber_main_keyboard(base_url)
    delivered = 0
    for job in jobs[:2]:
        msg_text = format_viber_job(job, base_url)
        for sub in subscribers:
            res = send_viber_message(sub["viber_user_id"], msg_text, keyboard=keyboard, bot_token=token)
            if res.get("status") == 0:
                delivered += 1
    return delivered


def dispatch_viber_bid_alerts(
    bids: Any, bot_token: Optional[str] = None, base_url: str = "https://khulaasaa.tech"
) -> int:
    """Broadcast new tender/bid announcements to all active Viber subscribers."""
    if not isinstance(bids, list) and isinstance(bot_token, list):
        bids = bot_token
        bot_token = None

    if not isinstance(bids, list) or not bids:
        return 0

    token, _, _ = get_viber_credentials(bot_token)
    if not token:
        return 0

    with get_db() as conn:
        subscribers = get_viber_subscribers(conn, active_only=True)
        if not subscribers:
            return 0

        keyboard = build_viber_main_keyboard(base_url)
        delivered = 0
        for bid in bids[:2]:
            msg_text = format_viber_bid(bid, base_url)
            for sub in subscribers:
                v_uid = sub["viber_user_id"]
                paid = is_viber_subscriber_paid(conn, v_uid)
                sub_msg = msg_text
                if not paid:
                    sub_msg += "\n\nFree normal feed. Upgrade to Pro (MVR 50/mo) for custom alerts: Send /pro"
                res = send_viber_message(v_uid, sub_msg, keyboard=keyboard, bot_token=token)
                if res.get("status") == 0:
                    delivered += 1
    return delivered


def dispatch_viber_sponsored_broadcast(
    conn: Any,
    campaign_name: str,
    sponsor_name: str,
    html_content: str,
    target_category: str = "all",
    link_url: Optional[str] = None,
    bot_token: Optional[str] = None,
    base_url: str = "https://khulaasaa.tech",
) -> dict[str, Any]:
    """Broadcast a dedicated sponsored message campaign to active Viber subscribers."""
    import re
    token, _, _ = get_viber_credentials(bot_token)
    if not token:
        return {"delivered": 0, "failed": 0, "status": "no_token"}

    subscribers = get_viber_subscribers(conn, active_only=True)
    if not subscribers:
        return {"delivered": 0, "failed": 0, "status": "no_subscribers"}

    clean_content = re.sub(r"<[^>]+>", "", html_content).strip()
    clean_content = clean_content.replace("&bull;", "•").replace("&mdash;", "—").replace("&rarr;", "→")

    lines = [
        f"SPONSORED DISPATCH — {sponsor_name}",
        "━━━━━━━━━━━━━━━━━━━━━━",
        clean_content,
    ]
    if link_url:
        lines.extend(["", f"Learn More: {link_url}"])
    lines.extend([
        "",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "This partner update was sent to Khulaasaa Viber subscribers.",
    ])
    msg_text = "\n".join(lines)
    keyboard = build_viber_main_keyboard(base_url)

    sent_count = fail_count = 0
    for sub in subscribers:
        cats = sub.get("categories") or ["all"]
        if target_category != "all" and "all" not in cats and target_category not in cats:
            continue
        res = send_viber_message(sub["viber_user_id"], msg_text, keyboard=keyboard, bot_token=token)
        if res.get("status") == 0:
            sent_count += 1
        else:
            fail_count += 1

    return {"delivered": sent_count, "failed": fail_count, "status": "ok"}

