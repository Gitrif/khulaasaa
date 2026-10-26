"""
Telegram Feedback & Issue Alert Dispatcher for Khulaasaa Alpha/Beta.
Dispatches user suggestions, issue reports, and feedback directly to admin Telegram chat.
"""
from __future__ import annotations

import html
import logging
from typing import Any

from alerts.telegram_client import get_telegram_credentials, send_telegram_message

logger = logging.getLogger("khulaasaa.alerts.feedback")


def dispatch_feedback_alert(feedback: dict[str, Any]) -> bool:
    """Send immediate push notification to Telegram admin chat when a user submits feedback."""
    bot_token, chat_id = get_telegram_credentials()
    if not bot_token or not chat_id:
        logger.info("Telegram credentials not set; feedback stored in DB.")
        return False

    fb_type = (feedback.get("feedback_type") or "feedback").upper()
    contact = feedback.get("contact_info") or "Anonymous / None Provided"
    page = feedback.get("page_url") or "/"
    msg = feedback.get("message") or ""

    type_tag = "[BUG REPORT]" if "ISSUE" in fb_type or "BUG" in fb_type else "[SUGGESTION]" if "SUGGEST" in fb_type else "[FEEDBACK]"

    text = (
        f"<b>{type_tag} NEW KHULAASAA ALPHA FEEDBACK</b>\n"
        f"----------------------------------------\n"
        f"<b>Category:</b> {html.escape(fb_type)}\n"
        f"<b>Submitted by:</b> {html.escape(contact)}\n"
        f"<b>Page:</b> {html.escape(page)}\n"
        f"----------------------------------------\n"
        f"<b>Message:</b>\n"
        f"<i>{html.escape(msg)}</i>\n"
        f"----------------------------------------"
    )
    ok, err = send_telegram_message(text, chat_id=chat_id, bot_token=bot_token)
    if not ok:
        logger.warning("Failed to send Telegram feedback alert: %s", err)
    return ok
