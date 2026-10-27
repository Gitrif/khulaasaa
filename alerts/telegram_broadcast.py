from __future__ import annotations

"""
Telegram Sponsored Commercial Broadcast Dispatcher for Khulaasaa.
"""
import logging
import sqlite3
from typing import Any, Optional

from data.database import record_ad_impression
from alerts.telegram_client import get_telegram_credentials, send_telegram_message
from alerts.telegram_formatters import format_standalone_ad_post

logger = logging.getLogger(__name__)


def dispatch_sponsored_broadcast(
    conn: sqlite3.Connection,
    campaign_name: str,
    sponsor_name: str,
    html_content: str,
    target_category: str = "bids",
    link_url: Optional[str] = None,
    bot_token: Optional[str] = None,
) -> dict[str, Any]:
    """Broadcast an ad or commercial spotlight to registered subscribers."""
    token, _ = get_telegram_credentials(bot_token=bot_token)
    if not token:
        return {"status": "error", "message": "Bot token not configured"}

    cursor = conn.execute(
        """
        SELECT id, chat_id, name, is_active FROM telegram_subscribers 
        WHERE is_active = 1;
        """
    )
    subscribers = cursor.fetchall()
    if not subscribers:
        return {"status": "ok", "delivered": 0, "message": "No active subscribers found"}

    broadcast_html = format_standalone_ad_post({
        "sponsor_name": sponsor_name,
        "text_html": html_content,
        "link_url": link_url or "https://khulaasaa.tech/bids",
    })

    delivered_count = 0
    failed_count = 0

    import alerts.telegram as tg

    for sub in subscribers:
        chat_id = str(sub["chat_id"])
        ok, _ = tg.send_telegram_message(
            broadcast_html,
            chat_id=chat_id,
            bot_token=token,
            disable_web_page_preview=False,
        )
        if ok:
            delivered_count += 1
            cursor_ad = conn.execute(
                "SELECT id FROM sponsored_ads WHERE campaign_name = ? LIMIT 1;",
                (campaign_name,),
            ).fetchone()
            if cursor_ad:
                record_ad_impression(conn, cursor_ad[0])
        else:
            failed_count += 1

    return {
        "status": "ok",
        "delivered": delivered_count,
        "failed": failed_count,
        "sponsor": sponsor_name,
        "campaign": campaign_name,
    }
