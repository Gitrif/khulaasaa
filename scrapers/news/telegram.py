"""
Atomic Telegram Public Channel Scraper (e.g. MV Crisis / t.me/s/mvcrisis).
Extracts breaking alert wires and strips out ads, obituaries, and casual banter.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup

from scrapers.news.base import (
    HEADERS,
    classify_topic,
    calculate_minutes_ago,
    format_relative_time,
)

logger = logging.getLogger(__name__)


def fetch_telegram_posts(source_key: str, url: str) -> list[dict[str, Any]]:
    """Fetch live public posts from Telegram channel preview (e.g. https://t.me/s/mvcrisis)."""
    articles = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        messages = soup.select(".tgme_widget_message")
        for m in messages:
            text_el = m.select_one(".tgme_widget_message_text")
            if not text_el:
                continue
            txt = text_el.get_text(" ", strip=True)
            if len(txt) < 15:
                continue

            txt_low = txt.lower()

            # Filter out tip-line promo / self-promotion
            is_self_promo = any(k in txt_low for k in [
                "got breaking news", "share it with us", "safely and instantly",
                "messagemvcrisis", "m.me/mvcrisis", "report tips", "send tips",
                "tip line", "dm us tips", "send us your videos", "message us on"
            ])
            if is_self_promo:
                continue

            # Filter out sponsored ads and commercial promos
            is_promo = any(k in txt_low for k in [
                "mattress", "subscription", "follow @", "ewitypos", "v2h", "giveaway",
                "enrol through", "enroll through", "85 mvr meals", "yummo",
                "residence opens bookings", "e-sim on avas", "buy now", "inquiries",
                "sponsored", "promo", "discount", "call for orders", "dm us for details",
                "dm for inquiries", "contact us on", "call / viber", "for sale:", "for rent:",
                "room for rent", "flat for rent", "apartment for rent", "order now",
                "limited slots", "special offer"
            ])
            if is_promo:
                continue

            # Filter out non-news: casual rain/weather chatter that is not an official warning
            is_casual_weather = any(k in txt_low for k in [
                "it's gonna rain", "its gonna rain", "gonna rain",
                "vaarey veheyne", "vaarey vehen", "vaarey vehi", "vaarey vehe",
                "rain expected", "rain soon", "looks like rain", "weather mood",
                "rain hopes", "hope it rains", "raining in male", "is it raining",
                "raining now", "ވިއްސާރަ ވެދާނެ", "ވާރޭ ވެހިދާނެ", "ވާރޭ ވެހެނީ", "މޫސުން ގޯސްވެދާނެ ކަމަށް"
            ]) and not any(k in txt_low for k in [
                "alert", "warning", "met office", "meteorological", "white alert",
                "yellow alert", "orange alert", "އެލާޓް", "މެޓް", "ސަމާލު"
            ])
            if is_casual_weather:
                continue

            # Filter out non-news: casual greetings, Friday blessings, and engagement chatter
            is_chatter = any(k in txt_low for k in [
                "good morning", "good afternoon", "good evening", "good night",
                "jumaa mubarak", "jummah mubarak", "ހުކުރު މުބާރަކް", "ހެނދުނުގެ ސަލާމް",
                "comment below", "share your thoughts", "what do you think", "vote here"
            ])
            if is_chatter:
                continue

            # Filter out obituary / funeral notices from general news feed
            is_obituary = any(k in txt_low or k in txt for k in [
                "kashunamaadhu", "ކަށުނަމާދު", "صلاة الجنازة", "ޖަނާޒާ", "جنازة",
                "niyaavejje", "ނިޔާވެއްޖެ", "ނިޔާވުން", "މަރުޙޫމް", "މަރުހޫމް",
                "ކަށުކަމާކެމީގެ", "إِنَّا لِلَّهِ", "އިންނާލިއްލާހި", "އާސަހަރާ މިސްކިތް"
            ])
            if is_obituary:
                try:
                    from data.database import get_db, upsert_scraped_obituary
                    with get_db() as db_conn:
                        upsert_scraped_obituary(db_conn, txt, link_el.get("href") if link_el else url)
                except Exception:
                    pass
                continue

            date_el = m.select_one(".tgme_widget_message_date time")
            link_el = m.select_one(".tgme_widget_message_date")
            date_iso = date_el.get("datetime") if date_el else None
            link = link_el.get("href") if link_el else url

            # Generate stable ID from telegram post link or text hash
            post_id = link.rstrip("/").split("/")[-1] if link else str(abs(hash(txt)))

            # Clean first line as headline
            headline = txt.split("\n")[0].strip()
            headline = re.sub(r"^🚨\s*#Breaking\s*:\s*", "", headline, flags=re.I)
            if len(headline) > 110:
                headline = headline[:107] + "..."

            published_raw = "Today"
            if date_iso:
                try:
                    dt = datetime.fromisoformat(date_iso.replace("Z", "+00:00"))
                    published_raw = dt.strftime("%d %b %Y, %H:%M")
                except Exception:
                    published_raw = date_iso[:16]

            minutes_ago = calculate_minutes_ago(date_iso)
            time_ago = format_relative_time(minutes_ago, date_iso)
            topic = classify_topic(headline, txt)
            section = "breaking"  # Real-time incident alert wire

            articles.append({
                "id": f"{source_key}-{post_id}",
                "headline": headline,
                "summary": txt[:240] + ("..." if len(txt) > 240 else ""),
                "published_raw": published_raw,
                "published_iso": date_iso,
                "minutes_ago": minutes_ago,
                "time_ago": time_ago,
                "sources": [source_key],
                "url": link,
                "section": section,
                "topic": topic,
                "tags": [],
            })
    except Exception as e:
        logger.warning("Failed to fetch Telegram posts from %s: %s", url, e)
    return articles
