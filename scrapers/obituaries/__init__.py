"""
Obituary scraper package for Maldivian funeral & Janaza notices (Telegram & Facebook).
"""
from __future__ import annotations

from scrapers.obituaries.facebook import (
    DEFAULT_FB_PAGE,
    DEFAULT_FB_PAGE_URL,
    fetch_facebook_kashunamaadhu_posts,
    get_facebook_credentials,
)
from scrapers.obituaries.telegram import (
    OBITUARY_KEYWORDS,
    fetch_telegram_obituaries,
    is_obituary_text,
)

__all__ = [
    "DEFAULT_FB_PAGE",
    "DEFAULT_FB_PAGE_URL",
    "OBITUARY_KEYWORDS",
    "fetch_facebook_kashunamaadhu_posts",
    "fetch_telegram_obituaries",
    "get_facebook_credentials",
    "is_obituary_text",
]
