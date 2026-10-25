"""
Viber REST API Client and Message Formatters for Khulaasaa.
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
    get_active_sponsored_ad,
)

logger = logging.getLogger(__name__)

VIBER_API_BASE = "https://chatapi.viber.com/pa"

DEFAULT_VIBER_BOT_TOKEN = os.environ.get("VIBER_BOT_TOKEN", "")
DEFAULT_VIBER_BOT_NAME = os.environ.get("VIBER_BOT_NAME", "Khulaasaa")
DEFAULT_VIBER_BOT_AVATAR = os.environ.get(
    "VIBER_BOT_AVATAR", "https://khulaasaa.tech/static/logos/khulaasaa.png"
)

def get_viber_credentials(
    bot_token: Optional[str] = None,
) -> tuple[str, str, str]:
    """Retrieve Viber credentials (token, name, avatar) from parameters or environment."""
    token = (bot_token or os.environ.get("VIBER_BOT_TOKEN") or DEFAULT_VIBER_BOT_TOKEN).strip()
    name = (os.environ.get("VIBER_BOT_NAME") or DEFAULT_VIBER_BOT_NAME).strip()
    avatar = (os.environ.get("VIBER_BOT_AVATAR") or DEFAULT_VIBER_BOT_AVATAR).strip()
    return token, name, avatar


def build_viber_main_keyboard(base_url: str = "https://khulaasaa.tech") -> dict[str, Any]:
    """
    Construct Viber persistent keyboard menu for easy, 1-tap subscriber interaction.
    """
    return {
        "Type": "keyboard",
        "DefaultHeight": True,
        "Buttons": [
            {
                "Columns": 3,
                "Rows": 1,
                "ActionType": "reply",
                "ActionBody": "/news",
                "Text": "<font color=\"#10222E\"><b>Latest News</b></font>",
                "TextSize": "regular",
                "BgColor": "#F6F3EC",
            },
            {
                "Columns": 3,
                "Rows": 1,
                "ActionType": "reply",
                "ActionBody": "/janaza",
                "Text": "<font color=\"#10222E\"><b>Janaza / ކަށުނަމާދު</b></font>",
                "TextSize": "regular",
                "BgColor": "#F6F3EC",
            },
            {
                "Columns": 3,
                "Rows": 1,
                "ActionType": "reply",
                "ActionBody": "/bids",
                "Text": "<font color=\"#10222E\"><b>Bids &amp; Tenders</b></font>",
                "TextSize": "regular",
                "BgColor": "#F6F3EC",
            },
            {
                "Columns": 3,
                "Rows": 1,
                "ActionType": "reply",
                "ActionBody": "/jobs",
                "Text": "<font color=\"#10222E\"><b>Jobs &amp; CV</b></font>",
                "TextSize": "regular",
                "BgColor": "#F6F3EC",
            },
            {
                "Columns": 6,
                "Rows": 1,
                "ActionType": "open-url",
                "ActionBody": base_url,
                "Text": "<font color=\"#FFFFFF\"><b>Open Web App</b></font>",
                "TextSize": "regular",
                "BgColor": "#10222E",
            },
        ],
    }


def set_viber_webhook(
    webhook_url: str,
    bot_token: Optional[str] = None,
    event_types: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Register the public HTTPS webhook URL with the Viber Bot platform.
    """
    token, _, _ = get_viber_credentials(bot_token)
    if not token:
        return {"status": 1, "status_message": "VIBER_BOT_TOKEN is not configured"}

    headers = {
        "X-Viber-Auth-Token": token,
        "Content-Type": "application/json",
    }
    payload = {
        "url": webhook_url,
        "event_types": event_types or [
            "delivered",
            "seen",
            "failed",
            "subscribed",
            "unsubscribed",
            "conversation_started",
            "message",
        ],
        "send_name": True,
        "send_photo": True,
    }

    try:
        resp = requests.post(
            f"{VIBER_API_BASE}/set_webhook",
            headers=headers,
            json=payload,
            timeout=12,
        )
        return resp.json()
    except Exception as e:
        logger.error("Failed to set Viber webhook: %s", e)
        return {"status": -1, "status_message": str(e)}


def send_viber_message(
    receiver_id: str,
    text: str,
    keyboard: Optional[dict[str, Any]] = None,
    bot_token: Optional[str] = None,
    sender_name: Optional[str] = None,
    sender_avatar: Optional[str] = None,
) -> dict[str, Any]:
    """
    Send a direct text message with optional interactive keyboard to a Viber user.
    """
    token, default_name, default_avatar = get_viber_credentials(bot_token)
    if not token:
        logger.warning("send_viber_message skipped: VIBER_BOT_TOKEN not set")
        return {"status": 1, "status_message": "No token"}

    headers = {
        "X-Viber-Auth-Token": token,
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "receiver": receiver_id,
        "min_api_version": 1,
        "sender": {
            "name": sender_name or default_name,
            "avatar": sender_avatar or default_avatar,
        },
        "type": "text",
        "text": text,
    }
    if keyboard:
        payload["keyboard"] = keyboard

    try:
        resp = requests.post(
            f"{VIBER_API_BASE}/send_message",
            headers=headers,
            json=payload,
            timeout=10,
        )
        return resp.json()
    except Exception as e:
        logger.error("Failed to send Viber message: %s", e)
        return {"status": -1, "status_message": str(e)}


def send_viber_picture(
    receiver_id: str,
    media_url: str,
    text: str = "",
    keyboard: Optional[dict[str, Any]] = None,
    bot_token: Optional[str] = None,
) -> dict[str, Any]:
    """
    Send a picture message with optional caption to a Viber subscriber.
    """
    token, name, avatar = get_viber_credentials(bot_token)
    if not token:
        return {"status": 1, "status_message": "No token"}

    headers = {
        "X-Viber-Auth-Token": token,
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "receiver": receiver_id,
        "min_api_version": 1,
        "sender": {"name": name, "avatar": avatar},
        "type": "picture",
        "text": text,
        "media": media_url,
    }
    if keyboard:
        payload["keyboard"] = keyboard

    try:
        resp = requests.post(
            f"{VIBER_API_BASE}/send_message",
            headers=headers,
            json=payload,
            timeout=10,
        )
        return resp.json()
    except Exception as e:
        logger.error("Failed to send Viber picture message: %s", e)
        return {"status": -1, "status_message": str(e)}


def clean_news_summary(headline: str, summary: str) -> str:
    """Ensure summary is not a duplicate repetition of the headline."""
    if not summary:
        return ""
    h = headline.strip().rstrip(".!?:").lower()
    s = summary.strip().rstrip(".").lower()
    if s == h or s.startswith(h[:min(35, len(h))]):
        remainder = summary.strip()[len(headline.strip()):].lstrip(" .!?:-\n\r")
        if len(remainder) > 25:
            return remainder
        return ""
    return summary.strip()


def format_viber_sponsored_block(conn=None, target_category: str = "all") -> str:
    """Format an active sponsored ad campaign for Viber."""
    try:
        from data.database import get_active_sponsored_ad, record_ad_impression, get_db
        ad = None
        if conn is None:
            with get_db() as c:
                ad = get_active_sponsored_ad(c, target_category=target_category)
                if ad:
                    try:
                        record_ad_impression(c, ad["id"])
                    except Exception:
                        pass
        else:
            ad = get_active_sponsored_ad(conn, target_category=target_category)
            if ad:
                try:
                    record_ad_impression(conn, ad["id"])
                except Exception:
                    pass

        if not ad:
            return ""

        sponsor = ad.get("sponsor_name") or "Khulaasaa Partner"
        raw_text = ad.get("text_html") or ""
        import re
        text_clean = re.sub(r'<[^>]+>', '', raw_text).strip()
        link_url = ad.get("link_url") or "https://khulaasaa.tech"

        return (
            f"\n\n━━━━━━━━━━━━━━━━━━━━\n"
            f"SPONSORED: {sponsor}\n"
            f"{text_clean}\n"
            f"Learn more: {link_url}"
        )
    except Exception:
        return ""


def format_viber_news(article: dict[str, Any], base_url: str = "https://khulaasaa.tech", include_ad: bool = True) -> str:
    """Format an aggregated news story for Viber message text, preventing duplicate text."""
    headline = (article.get("headline") or "News Story").strip()
    summary = clean_news_summary(headline, article.get("summary") or "")
    sources = article.get("sources") or ["Khulaasaa"]
    sources_str = ", ".join([s.title() for s in sources])
    url = article.get("url") or f"{base_url}/#story-{article.get('id')}"

    parts = [f"🔴 {headline}"]
    if summary:
        parts.append(f"\n\n{summary[:200]}...")
    parts.append(f"\n\n📰 Outlets: {sources_str}\n🔗 Read full: {url}")

    if include_ad:
        ad_text = format_viber_sponsored_block(target_category="news")
        if ad_text:
            parts.append(ad_text)

    return "".join(parts)


def send_viber_news_post(
    receiver_id: str,
    article: dict[str, Any],
    base_url: str = "https://khulaasaa.tech",
    keyboard: Optional[dict[str, Any]] = None,
    bot_token: Optional[str] = None,
) -> dict[str, Any]:
    """Send Viber news post with image for standardized, consistent card width (like Telegram)."""
    text = format_viber_news(article, base_url=base_url)
    image_url = article.get("image_url") or article.get("image") or article.get("photo_url")
    if not image_url or not str(image_url).startswith("http"):
        image_url = f"{base_url}/static/logos/khulaasaa.png"

    res = send_viber_picture(receiver_id, media_url=image_url, text=text, keyboard=keyboard, bot_token=bot_token)
    if res.get("status") != 0:
        return send_viber_message(receiver_id, text=text, keyboard=keyboard, bot_token=bot_token)
    return res


def format_viber_obituary(ob: dict[str, Any], base_url: str = "https://khulaasaa.tech") -> str:
    """Format a respectful Islamic Janaza / funeral announcement for Viber."""
    name_dv = ob.get("name_dv") or "މަރުޙޫމް"
    age = f" ({ob['age']}އ)" if ob.get("age") else ""
    address = f" / {ob['address_dv']}" if ob.get("address_dv") else ""
    mosque = ob.get("funeral_mosque_dv") or "މަސްޖިދުލް ތަޢާވުން (އާސަހަރާ މިސްކިތް)"
    prayer_time = ob.get("prayer_time_dv") or "ޢަޞްރު ނަމާދަށްފަހު"
    contacts = f"\n📞 އާއިލާ: {ob['contact_numbers']}" if ob.get("contact_numbers") else ""

    return (
        f"إِنَّا لِلَّهِ وَإِنَّا إِلَيْهِ رَاجِعُونَ\n\n"
        f"ކަށުނަމާދު:\n"
        f"• {name_dv}{age}{address}\n\n"
        f"🕌 މިސްކިތް: {mosque}\n"
        f"⏰ ވަގުތު: {prayer_time}"
        f"{contacts}\n\n"
        f"🔗 {base_url}/obituaries"
    )


def format_viber_bid(bid: dict[str, Any], base_url: str = "https://khulaasaa.tech", include_ad: bool = True) -> str:
    """Format a government tender notice for Viber."""
    title = bid.get("title_en") or bid.get("title") or "Tender Notice"
    agency = bid.get("agency_name_en") or bid.get("agency") or "Government Agency"
    ref = bid.get("reference_number") or bid.get("ref") or "N/A"
    deadline = bid.get("submission_date") or "See notice"
    url = bid.get("source_url") or f"{base_url}/bids"

    parts = [
        f"📑 TENDER ALERT\n"
        f"• {title}\n\n"
        f"🏛 Agency: {agency}\n"
        f"🏷 Ref: {ref}\n"
        f"⏰ Deadline: {deadline}\n\n"
        f"🔗 View tender: {url}"
    ]
    if include_ad:
        ad_text = format_viber_sponsored_block(target_category="bids")
        if ad_text:
            parts.append(ad_text)
    return "".join(parts)


def format_viber_job(job: dict[str, Any], base_url: str = "https://khulaasaa.tech", include_ad: bool = True) -> str:
    """Format a job opening announcement for Viber."""
    title = job.get("title_en") or job.get("title") or "Job Vacancy"
    agency = job.get("agency_name_en") or job.get("agency") or "Employer"
    discipline = job.get("discipline") or "Other"
    location = job.get("location") or "Male'"
    deadline = job.get("deadline_iso") or "Open"
    if "T" in str(deadline):
        deadline = str(deadline)[:10]
    salary = job.get("salary_raw")
    url = job.get("source_url") or f"{base_url}/jobs"

    salary_line = f"💰 Salary: {salary}\n" if salary and salary != "None" else ""

    parts = [
        f"💼 JOB VACANCY ALERT\n"
        f"• {title}\n\n"
        f"🏢 Employer: {agency}\n"
        f"🏷 Category: {discipline}\n"
        f"📍 Location: {location}\n"
        f"{salary_line}"
        f"⏰ Deadline: {deadline}\n\n"
        f"🔗 Apply: {url}\n"
        f"📝 Maldivian CV Creator: {base_url}/jobs/cv"
    ]
    if include_ad:
        ad_text = format_viber_sponsored_block(target_category="jobs")
        if ad_text:
            parts.append(ad_text)
    return "".join(parts)


