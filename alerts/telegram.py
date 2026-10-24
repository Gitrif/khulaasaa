"""
Telegram Bot Alert Service Facade for Khulaasaa.
Provides backward-compatible re-exports for client, formatters, dispatches, and bot updates.
"""
from __future__ import annotations

# Re-export HTTP client methods & credentials
from alerts.telegram_client import (
    DEFAULT_TELEGRAM_BOT_TOKEN,
    DEFAULT_TELEGRAM_CHAT_ID,
    get_telegram_credentials,
    send_telegram_message,
    edit_telegram_message,
    answer_telegram_callback_query,
    set_telegram_chat_menu_button,
)

# Re-export formatters & keyboard builders
from alerts.telegram_formatters import (
    matches_interest,
    format_tender_alert_html,
    format_sponsored_block,
    format_standalone_ad_post,
    build_tender_keyboard,
    build_news_keyboard,
    format_news_alert_html,
    matches_news_interest,
    format_obituary_alert_html,
    build_obituary_keyboard,
    format_job_alert_html,
    format_pro_tier_message,
    build_settings_keyboard_and_text,
)

# Re-export alert dispatchers
from alerts.telegram_dispatch import (
    record_alert_sent,
    is_alert_already_sent,
    dispatch_tender_alerts,
    dispatch_news_alerts,
    dispatch_obituary_alerts,
    dispatch_sponsored_broadcast,
    dispatch_job_alerts,
)

# Re-export bot update handling & background polling
from alerts.telegram_bot import (
    handle_incoming_telegram_update,
    start_telegram_bot_polling,
)
