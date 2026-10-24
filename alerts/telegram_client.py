from __future__ import annotations

"""
Telegram Bot HTTP API Client and Credentials for Khulaasaa.
"""

import logging
import os
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

DEFAULT_TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
DEFAULT_TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

DISCIPLINE_KEYS = [
    ("Construction", "const"),
    ("IT", "it"),
    ("Medical", "med"),
    ("Finance", "fin"),
    ("Aviation", "av"),
    ("Marine", "mar"),
    ("Tourism", "tour"),
    ("Education", "edu"),
    ("Other", "oth"),
]


def get_telegram_credentials(
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
) -> tuple[str, str]:
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    target_chat = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")
    return token, target_chat


def send_telegram_message(
    text: str,
    chat_id: Optional[str] = None,
    bot_token: Optional[str] = None,
    reply_markup: Optional[dict[str, Any]] = None,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = False,
    session: Optional[Any] = None,
) -> tuple[bool, str]:
    token, target_chat = get_telegram_credentials(bot_token, chat_id)
    if not token or not target_chat:
        return False, "Missing bot_token or chat_id"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": target_chat,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_web_page_preview,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        http = session or requests
        resp = http.post(url, json=payload, timeout=10)
        data = resp.json()
        if not data.get("ok"):
            return False, f"Telegram API error: {data.get('description', 'Unknown error')}"
        return True, "Alert sent successfully"
    except Exception as e:
        return False, f"Network exception: {e}"


def edit_telegram_message(
    chat_id: str,
    message_id: int,
    text: str,
    reply_markup: Optional[dict[str, Any]] = None,
    parse_mode: str = "HTML",
    bot_token: Optional[str] = None,
    session: Optional[Any] = None,
) -> tuple[bool, str]:
    token, _ = get_telegram_credentials(bot_token, chat_id)
    if not token or not chat_id:
        return False, "Missing bot_token or chat_id"
    url = f"https://api.telegram.org/bot{token}/editMessageText"
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        http = session or requests
        resp = http.post(url, json=payload, timeout=10)
        data = resp.json()
        if not data.get("ok"):
            return False, f"Telegram API error: {data.get('description', 'Unknown')}"
        return True, "Message edited successfully"
    except Exception as e:
        return False, f"Network exception: {e}"


def answer_telegram_callback_query(
    callback_query_id: str,
    text: Optional[str] = None,
    show_alert: bool = False,
    bot_token: Optional[str] = None,
) -> bool:
    token, _ = get_telegram_credentials(bot_token)
    if not token:
        return False
    url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
    payload: dict[str, Any] = {"callback_query_id": callback_query_id, "show_alert": show_alert}
    if text:
        payload["text"] = text
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.json().get("ok", False)
    except Exception:
        return False


def set_telegram_chat_menu_button(
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
    web_app_url: str = "https://khulaasaa.tech/bids",
) -> bool:
    token, _ = get_telegram_credentials(bot_token)
    if not token:
        return False
    url = f"https://api.telegram.org/bot{token}/setChatMenuButton"
    payload: dict[str, Any] = {
        "menu_button": {
            "type": "web_app",
            "text": "Browse Bids & Jobs",
            "web_app": {"url": web_app_url},
        }
    }
    if chat_id:
        payload["chat_id"] = chat_id
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.json().get("ok", False)
    except Exception:
        return False
