"""
Obituary Ingestion Service.
Normalizes, parses, and persists obituary candidates scraped from news feeds,
Telegram channels, and Facebook KashuNamaadhuMV.
"""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import sqlite3
from typing import Any, Optional

from data.database import (
    get_db,
    parse_obituary_text,
    upsert_obituary,
    upsert_scraped_obituary,
)
from scrapers.obituaries import (
    DEFAULT_FB_PAGE_URL,
    fetch_facebook_kashunamaadhu_posts,
    fetch_telegram_obituaries,
)

logger = logging.getLogger(__name__)


def ingest_obituary_candidates(
    conn: sqlite3.Connection,
    candidates: list[dict[str, Any]],
) -> int:
    """
    Persist a list of obituary candidate dicts (from news split or Telegram/Facebook scrapers)
    into the obituaries repository.
    """
    count = 0
    for ob in candidates:
        raw_text = f"{ob.get('headline') or ''}\n{ob.get('summary') or ob.get('text') or ''}".strip()
        if not raw_text:
            continue
        url = ob.get("url")
        if upsert_scraped_obituary(conn, raw_text, url):
            count += 1
    return count


def sync_external_obituaries(conn: Optional[sqlite3.Connection] = None) -> int:
    """
    Fetch obituary notices from Telegram and Facebook scrapers and persist them.
    """
    tg_candidates = fetch_telegram_obituaries("mvcrisis", "https://t.me/s/mvcrisis")
    fb_candidates = fetch_facebook_kashunamaadhu_posts()
    all_candidates = tg_candidates + fb_candidates
    if not all_candidates:
        return 0

    if conn is not None:
        return ingest_obituary_candidates(conn, all_candidates)

    with get_db() as db_conn:
        return ingest_obituary_candidates(db_conn, all_candidates)


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
