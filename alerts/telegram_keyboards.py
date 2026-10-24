from __future__ import annotations

"""
Telegram Settings and Pro Tier Keyboard Builders for Khulaasaa.
"""

import os
from typing import Any, Optional

from alerts.telegram_client import DISCIPLINE_KEYS


def format_pro_tier_message(is_paid: bool, chat_id: str = "") -> tuple[str, dict[str, Any]]:
    """Format pro subscription status explanation and upgrade prompt."""
    app_url = os.environ.get("APP_URL", "https://khulaasaa.tech").rstrip("/")
    if is_paid:
        text = (
            "<b>Khulaasaa Pro — Active Subscription</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Status: <b>ACTIVE (MVR 50 / month)</b>\n\n"
            "You are receiving dedicated real-time notifications filtered strictly "
            "to your chosen industries and priority keywords.\n\n"
            "<i>Manage your custom keywords and industries anytime in Settings.</i>"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "Back to Settings", "callback_data": "open:settings"}],
            ]
        }
    else:
        text = (
            "<b>Upgrade to Khulaasaa Pro (MVR 50 / month)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Current Status: <b>Free Tier (Normal Feed)</b>\n\n"
            "Free members receive regular alerts across all public announcements. "
            "Upgrade to Khulaasaa Pro (MVR 50 / month) for precision benefits:\n\n"
            "• <b>Custom Industry Filtering:</b> Select exactly which trade disciplines alert you\n"
            "• <b>Keyword Subscriptions:</b> Follow specific islands, councils, or projects\n"
            "• <b>Instant Prioritized Delivery:</b> Bypasses batched delivery queues\n\n"
            "<b>Payment & Activation:</b>\n"
            "Transfer <b>MVR 50</b> to BML Account: <code>7730000123456</code> (Khulaasaa MV)\n"
            f"Reference: <code>PRO-{chat_id or 'SUB'}</code>\n\n"
            "<i>Your account will be activated immediately upon receipt!</i>"
        )
        kb = {
            "inline_keyboard": [
                [{"text": "Upgrade Online (MVR 50/mo) ↗", "url": f"{app_url}/pro?chat_id={chat_id}" if chat_id else f"{app_url}/pro"}],
                [{"text": "Back to Settings", "callback_data": "open:settings"}],
            ]
        }
    return text, kb


def build_settings_keyboard_and_text(
    subscriber: Optional[dict[str, Any]] = None,
    is_paid: bool = False,
) -> tuple[str, dict[str, Any]]:
    """Build the interactive settings message and inline keyboard markup with toggles."""
    disciplines = set((subscriber.get("disciplines") if subscriber else None) or ["All"])
    keywords = set((subscriber.get("keywords") if subscriber else None) or ["all_news", "breaking", "janaza", "ras-male", "sultan-park", "tgst"])

    chat_id = str(subscriber.get("chat_id") or "") if subscriber else ""
    paid = is_paid or bool(subscriber.get("is_paid")) if subscriber else is_paid

    breaking_on = "breaking" in keywords
    all_news_on = "all_news" in keywords
    janaza_on = "janaza" in keywords
    tenders_on = "All" in disciplines or any(d in disciplines for d, _ in DISCIPLINE_KEYS)

    tier_status = "<b>[PRO] Pro Tier (Active — MVR 50/mo)</b>" if paid else "<b>Free Tier (Normal Feed)</b> — Upgrade: /pro"

    lines = [
        "<b>Khulaasaa Alert Preferences</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"• <b>Subscription Plan:</b> {tier_status}",
        "",
        "By default, all feeds are active. Toggle quick channels below:",
        "",
        f"• <b>All News:</b> {'ACTIVE' if all_news_on else 'MUTED'}",
        f"• <b>Breaking News:</b> {'ACTIVE' if breaking_on else 'MUTED'}",
        f"• <b>Gazette Bids & Tenders:</b> {'ACTIVE' if tenders_on else 'MUTED'}",
        f"• <b>Janaza & Obituaries:</b> {'ACTIVE' if janaza_on else 'MUTED'}",
        "",
    ]
    if paid:
        lines.append("<i>[PRO] Pro Subscriber: Custom industry & keyword filtering active.</i>")
    else:
        lines.append("<i>[Notice] Free normal feed active. Upgrade to Pro (MVR 50/mo) for custom keyword & industry filters: /pro</i>")

    app_url = os.environ.get("APP_URL", "https://khulaasaa.tech").rstrip("/")
    web_filter_url = f"{app_url}/alerts?chat_id={chat_id}" if chat_id else f"{app_url}/alerts"

    keyboard: list[list[dict[str, Any]]] = [
        [
            {"text": f"All News {'[ON]' if all_news_on else '[OFF]'}", "callback_data": "toggle:all_news"},
            {"text": f"Breaking News {'[ON]' if breaking_on else '[OFF]'}", "callback_data": "toggle:breaking"},
        ],
        [
            {"text": f"Gazette Bids {'[ON]' if tenders_on else '[OFF]'}", "callback_data": "toggle:tenders"},
            {"text": f"Janaza / Obituaries {'[ON]' if janaza_on else '[OFF]'}", "callback_data": "toggle:janaza"},
        ],
    ]

    if not paid:
        keyboard.append([
            {"text": "[PRO] Upgrade to Pro (MVR 50/mo)", "callback_data": "upgrade:pro"},
        ])
    else:
        keyboard.append([
            {"text": "[PRO] Pro Status & Benefits", "callback_data": "upgrade:pro"},
        ])

    keyboard.append([
        {"text": "Filter Preferences on Web ↗", "url": web_filter_url},
    ])

    return "\n".join(lines), {"inline_keyboard": keyboard}
