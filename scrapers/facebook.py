"""
Facebook Scraper and Graph API Client for Maldivian Community Pages.
Specifically tailored for KashuNamaadhuMV (https://www.facebook.com/KashuNamaadhuMV/).

Supports:
1. Facebook Graph API polling when FACEBOOK_ACCESS_TOKEN is configured.
2. Direct text and post parsing for rapid import of Kashunamaadhu announcements.
3. Webhook receiver for Facebook Page Real-Time Updates.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Optional

import requests

from data.database import (
    get_db,
    parse_obituary_text,
    upsert_obituary,
    upsert_scraped_obituary,
)

logger = logging.getLogger(__name__)

DEFAULT_FB_PAGE = "KashuNamaadhuMV"
DEFAULT_FB_PAGE_URL = "https://www.facebook.com/KashuNamaadhuMV/"


def get_facebook_credentials() -> tuple[str, str]:
    """Retrieve Facebook page name and access token from environment."""
    page_name = os.environ.get("FACEBOOK_PAGE_NAME", DEFAULT_FB_PAGE).strip()
    token = os.environ.get("FACEBOOK_ACCESS_TOKEN", "").strip()
    return page_name, token


def fetch_facebook_kashunamaadhu_posts(
    access_token: Optional[str] = None,
    page_name: Optional[str] = None,
    limit: int = 15,
) -> list[dict[str, Any]]:
    """
    Fetch latest obituary announcements from KashuNamaadhuMV Facebook page.
    Uses Facebook Graph API if access token is available.
    """
    default_page, default_token = get_facebook_credentials()
    page = page_name or default_page
    token = access_token or default_token

    if not token:
        logger.info("Facebook Graph API: FACEBOOK_ACCESS_TOKEN not set; skipping live Graph API fetch.")
        return []

    url = f"https://graph.facebook.com/v19.0/{page}/posts"
    params = {
        "access_token": token,
        "fields": "id,message,created_time,full_picture,permalink_url",
        "limit": limit,
    }

    try:
        resp = requests.get(url, params=params, timeout=12)
        if resp.status_code != 200:
            logger.warning("Facebook Graph API returned %s: %s", resp.status_code, resp.text[:200])
            return []

        posts = resp.json().get("data", [])
        processed = []

        with get_db() as conn:
            for p in posts:
                message = p.get("message", "").strip()
                if not message:
                    continue

                parsed = parse_obituary_text(message)
                pic_url = p.get("full_picture")
                permalink = p.get("permalink_url") or f"{DEFAULT_FB_PAGE_URL}posts/{p.get('id')}"

                # Ingest into SQLite obituaries
                ob_id = upsert_scraped_obituary(conn, message, permalink)
                processed.append({
                    "id": p.get("id"),
                    "text": message,
                    "picture": pic_url,
                    "url": permalink,
                    "parsed": parsed,
                    "obituary_id": ob_id,
                })

        return processed
    except Exception as e:
        logger.error("Error fetching Facebook posts for %s: %s", page, e)
        return []


def import_kashunamaadhu_text(
    raw_text: str,
    photo_url: Optional[str] = None,
    source_url: Optional[str] = DEFAULT_FB_PAGE_URL,
) -> dict[str, Any]:
    """
    Parse a copied Kashunamaadhu Facebook post or wire message and save it to the obituaries database.
    """
    parsed = parse_obituary_text(raw_text)
    slug = f"kashunamaadhu-{abs(hash(raw_text[:100])) % 100000}"

    from datetime import datetime, timezone
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    ob_data = {
        "slug": slug,
        "name_dv": parsed["name_dv"],
        "name_en": parsed["name_en"],
        "address_dv": parsed["address_dv"],
        "address_en": parsed["address_en"],
        "age": parsed["age"],
        "funeral_mosque_dv": parsed["funeral_mosque_dv"],
        "funeral_mosque_en": parsed["funeral_mosque_en"],
        "prayer_time_dv": parsed["prayer_time_dv"],
        "prayer_time_en": parsed["prayer_time_en"],
        "funeral_date": today_str,
        "death_date": today_str,
        "photo_url": photo_url,
        "contact_numbers": parsed["contact_numbers"],
        "source_channel": "KashuNamaadhuMV Facebook",
        "announcement_type": "Janaza",
        "is_active": 1,
    }

    with get_db() as conn:
        ob_id = upsert_obituary(conn, ob_data)

    return {"status": "ok", "obituary_id": ob_id, "data": ob_data}
