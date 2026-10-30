"""
Facebook Graph API scraper for KashuNamaadhuMV obituary announcements.
Pure scraper module: fetches and returns raw obituary post dicts without database writes.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

import requests

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
    Fetch latest obituary announcements from KashuNamaadhuMV Facebook page via Graph API.
    Does not write to the database; returns candidate dicts for obituary_ingestion.
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
        results: list[dict[str, Any]] = []
        for p in posts:
            message = (p.get("message") or "").strip()
            if not message:
                continue
            permalink = p.get("permalink_url") or f"{DEFAULT_FB_PAGE_URL}posts/{p.get('id')}"
            results.append({
                "id": p.get("id"),
                "text": message,
                "picture": p.get("full_picture"),
                "url": permalink,
                "created_time": p.get("created_time"),
            })
        return results
    except Exception as exc:
        logger.error("Error fetching Facebook posts for %s: %s", page, exc)
        return []
