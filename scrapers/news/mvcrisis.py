"""
Dedicated MV Crisis Channel Scraper (t.me/s/mvcrisis).
Extracts breaking news, police reports, court developments, and national incident wires.
Strictly filters out commercial retail ads, sponsored posts, tip lines, and viral social banter.
Preserves original Latin Dhivehi text without transliteration.
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

logger = logging.getLogger("khulaasaa.news.mvcrisis")

# Commercial shops, brands, retail adverts, and service promotions
COMMERCIAL_AD_KEYWORDS = [
    # Retailers & Brands
    "bestbuy mobile", "gizmo", "chessnut", "hayat mattress", "mattress",
    "zedex", "study abroad", "asters", "redwave", "yummo", "85 mvr meals",
    "ewitypos", "v2h", "residence opens bookings", "e-sim on avas",
    # Commercial action phrases
    "authorized reseller", "authorised reseller", "genuine products",
    "take pride in offering", "available at", "visit our store",
    "order now", "call for orders", "dm us for details", "dm for inquiries",
    "dm for", "contact us on", "call / viber", "viber / call", "viber:",
    "for sale:", "for rent:", "room for rent", "flat for rent", "apartment for rent",
    "special offer", "limited stock", "pre-order", "discount", "sale now on",
    "retail price", "special discount", "buy now", "inquiries", "sponsored",
    "promo", "limited slots", "admission open", "enrol through", "enroll through",
    "free delivery", "cash on delivery", "warranty", "giveaway",
]

# Tip lines, channel cross-promotions, and self-promotion
SELF_PROMO_KEYWORDS = [
    "@thestandardmv", "follow @", "subscribe to", "join our channel",
    "stay informed, stay ahead", "got breaking news", "share it with us",
    "safely and instantly", "messagemvcrisis", "m.me/mvcrisis",
    "report tips", "send tips", "tip line", "dm us tips",
    "send us your videos", "message us on", "whatsapp / telegram",
]

# Casual social banter, memes, and non-news video chatter
NON_NEWS_CHATTER = [
    "dressing table eh cycle gai", "dressing table",
    "it's gonna rain", "its gonna rain", "gonna rain",
    "vaarey veheyne", "vaarey vehen", "vaarey vehi", "vaarey vehe",
    "rain expected", "rain soon", "looks like rain", "weather mood",
    "rain hopes", "hope it rains", "raining in male", "is it raining",
    "raining now", "good morning", "good afternoon", "good evening",
    "good night", "jumaa mubarak", "jummah mubarak", "comment below",
    "share your thoughts", "what do you think", "vote here",
]


def is_official_weather_alert(txt_lower: str) -> bool:
    """Check if post is an official meteorological alert rather than casual rain banter."""
    return any(k in txt_lower for k in [
        "alert", "warning", "met office", "meteorological", "white alert",
        "yellow alert", "orange alert", "އެލާޓް", "މެޓް", "ސަމާލު"
    ])


def fetch_mvcrisis_posts(source_key: str = "mvcrisis", url: str = "https://t.me/s/mvcrisis") -> list[dict[str, Any]]:
    """Fetch and filter live breaking wires from MV Crisis public channel preview."""
    articles: list[dict[str, Any]] = []
    seen_texts: set[str] = set()

    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if resp.status_code != 200:
            logger.warning("MV Crisis fetch failed with HTTP %d", resp.status_code)
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

            # Deduplicate repeated identical telegram posts (e.g. repeated ads or wire echoes)
            clean_hash = re.sub(r"\W+", "", txt.lower())[:80]
            if clean_hash in seen_texts:
                continue
            seen_texts.add(clean_hash)

            txt_low = txt.lower()

            # 1. Aggressively filter out commercial advertisements and shop promos
            if any(k in txt_low for k in COMMERCIAL_AD_KEYWORDS):
                continue

            # 2. Filter out self-promo, tip lines, and follow recommendations
            if any(k in txt_low for k in SELF_PROMO_KEYWORDS):
                continue

            # 3. Filter out casual non-news banter & weather chatter
            if any(k in txt_low for k in NON_NEWS_CHATTER) and not is_official_weather_alert(txt_low):
                continue

            # 4. Filter and record obituaries to obituary store
            is_obituary = any(k in txt_low or k in txt for k in [
                "kashunamaadhu", "ކަށުނަމާދު", "صلاة الجنازة", "ޖަނާޒާ", "جنازة",
                "niyaavejje", "ނިޔާވެއްޖެ", "ނިޔާވުން", "މަރުޙޫމް", "މަރުހޫމް",
                "ކަށުކަމާކެމީގެ", "إِنَّا لِلَّهِ", "އިންނާލިއްލާހި", "އާސަހަރާ މިސްކިތް"
            ])
            date_el = m.select_one(".tgme_widget_message_date time")
            link_el = m.select_one(".tgme_widget_message_date")
            date_iso = date_el.get("datetime") if date_el else None
            link = link_el.get("href") if link_el else url

            if is_obituary:
                # Exclude obituary notices from general news feed; obituary ingestion handles persistence.
                continue

            post_id = link.rstrip("/").split("/")[-1] if link else str(abs(hash(txt)))

            # Clean first line as headline: strip breaking prefixes and symbols
            headline = txt.split("\n")[0].strip()
            headline = re.sub(r"^\uD83D\uDEA8\s*#Breaking\s*:\s*", "", headline, flags=re.I)
            headline = re.sub(r"^[\uD83D\uDEA8\u26A0\uFE0F\uD83D\uDCE2\u2705\s]+", "", headline).strip()

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
                "section": "breaking",
                "topic": topic,
                "tags": [],
                "is_latin": True,
                "is_dhivehi": False,
                "is_latin_transliterated": False,
            })
    except Exception as exc:
        logger.warning("Failed to fetch MV Crisis posts: %s", exc)

    return articles
