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
    """Send immediate notification to Telegram admin chat for user feedback / bug reports."""
    bot_token, chat_id = get_telegram_credentials()
    if not bot_token or not chat_id:
        logger.info("Telegram credentials not set; feedback saved to DB only.")
        return False

    fb_type = (feedback.get("feedback_type") or "feedback").upper()
    contact = feedback.get("contact_info") or "Anonymous / hooks.connect@gmail.com"
    page = feedback.get("page_url") or "Khulaasaa App"
    msg = feedback.get("message") or ""

    type_tag = "[BUG REPORT]" if "ISSUE" in fb_type or "BUG" in fb_type else "[SUGGESTION]" if "SUGGEST" in fb_type else "[FEEDBACK]"

    text = (
        f"<b>{type_tag} KHULAASAA ALPHA FEEDBACK</b>\n\n"
        f"<b>Category:</b> {html.escape(fb_type)}\n"
        f"<b>From:</b> {html.escape(contact)}\n"
        f"<b>Page:</b> {html.escape(page)}\n\n"
        f"<b>Message:</b>\n<i>{html.escape(msg)}</i>\n\n"
        f"<b>Target Inbox:</b> hooks.connect@gmail.com"
    )
    ok, _ = send_telegram_message(text, chat_id=chat_id, bot_token=bot_token)
    return ok
