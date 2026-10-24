"""
Base configurations and shared helpers for news scrapers.
"""
from __future__ import annotations

import html
import re
from datetime import datetime
from typing import Optional

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

NEWS_SOURCES_CONFIG = {
    "haftha": {
        "id": "haftha",
        "name": "Haftha",
        "initial": "H",
        "kind": "press",
        "type": "wp_rest",
        "url": "https://haftha.mv/wp-json/wp/v2/posts?per_page=12",
    },
    "atolltimes": {
        "id": "atolltimes",
        "name": "Atoll Times",
        "initial": "A",
        "kind": "press",
        "type": "rss",
        "url": "https://atolltimes.mv/feed/",
    },
    "dhauru": {
        "id": "dhauru",
        "name": "Dhauru",
        "initial": "D",
        "kind": "press",
        "type": "rss",
        "url": "https://dhauru.com/feed/",
    },
    "adhadhu": {
        "id": "adhadhu",
        "name": "Adhadhu",
        "initial": "A",
        "kind": "press",
        "type": "rss",
        "url": "https://adhadhu.com/feed/",
    },
    "sun": {
        "id": "sun",
        "name": "Sun Online",
        "initial": "S",
        "kind": "press",
        "type": "rss",
        "url": "https://sun.mv/feed",
    },
    "psm": {
        "id": "psm",
        "name": "PSM News",
        "initial": "P",
        "kind": "official",
        "type": "rss",
        "url": "https://psmnews.mv/feed",
    },
    "standard": {
        "id": "standard",
        "name": "The Standard",
        "initial": "S",
        "kind": "press",
        "type": "rss",
        "url": "https://standard.mv/feed/",
    },
    "mvcrisis": {
        "id": "mvcrisis",
        "name": "MV Crisis",
        "initial": "C",
        "kind": "wire",
        "type": "telegram",
        "url": "https://t.me/s/mvcrisis",
    },
    "mihaaru": {
        "id": "mihaaru",
        "name": "Mihaaru",
        "initial": "M",
        "kind": "press",
        "type": "html_mihaaru",
        "url": "https://mihaaru.com",
    },
    "miadhu": {
        "id": "miadhu",
        "name": "Miadhu",
        "initial": "M",
        "kind": "press",
        "type": "html_miadhu",
        "url": "https://miadhu.mv/en",
    },
    "voice": {
        "id": "voice",
        "name": "Voice",
        "initial": "V",
        "kind": "press",
        "type": "rss",
        "url": "https://voice.mv/feed",
    },
}


def strip_html_tags(text: Optional[str]) -> str:
    """Remove HTML tags and unescape HTML entities."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = html.unescape(clean)
    clean = re.sub(r"[\u200E\u200F\u200B\r\n\t]+", " ", clean)
    return " ".join(clean.split()).strip()


def classify_topic(title: str, summary: str = "") -> str:
    """Classify article into topic: economy, health, weather, crime, policy."""
    t = f"{title} {summary}".lower()
    if any(k in t for k in ["tax", "dollar", "bank", "economy", "mvr", "inflation", "finance", "business", "ޑޮލަރު", "ފައިސާ", "ވިޔަފާރި", "އިޤްތިޞާދު", "ބޭންކް"]):
        return "economy"
    if any(k in t for k in ["health", "hospital", "doctor", "disease", "covid", "clinic", "ޞިއްޙީ", "ހޮސްޕިޓަލް", "ޑޮކްޓަރު", "ބަލި"]):
        return "health"
    if any(k in t for k in ["weather", "rain", "storm", "cyclone", "met", "wind", "ވިއްސާރަ", "މޫސުން", "ކަނޑު"]):
        return "weather"
    if any(k in t for k in ["arrested", "police", "court", "crime", "alcohol", "drugs", "assault", "stabbing", "ހައްޔަރު", "ފުލުހުން", "ކޯޓު", "ބަނގުރާ", "މަސްތުވާތަކެތި", "ހަމަލާ"]):
        return "crime"
    return "policy"


def classify_section(title: str, minutes_ago: int, topic: str) -> str:
    """
    Classify into breaking, major, or general section.
    Rule: Breaking ONLY if the reporting outlet explicitly labels it as breaking or urgent news.
    """
    t_low = title.lower()
    is_explicit_breaking = any(k in t_low for k in [
        "breaking", "breaking news", "urgent", "flash:", "kulli", "alert",
        "ކުއްލި", "ކުއްލި ޚަބަރު", "އެލާޓް", "ސަމާލު"
    ])
    if is_explicit_breaking:
        return "breaking"
    if any(k in t_low for k in ["muizzu", "nasheed", "parliament", "majlis", "agreement", "scandal", "audit", "މުއިއްޒު", "ނަޝީދު", "މަޖިލިސް", "ސަރުކާރު"]):
        return "major"
    return "general"


def calculate_minutes_ago(dt_iso: Optional[str]) -> int:
    """Calculate minutes between article publication and now."""
    if not dt_iso:
        return 60
    try:
        dt = datetime.fromisoformat(dt_iso.replace("Z", "+00:00"))
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        diff = (now - dt).total_seconds() / 60
        return max(1, int(diff))
    except Exception:
        return 60


def format_relative_time(minutes_ago: int, dt_iso: Optional[str] = None) -> str:
    """Format minutes into human-readable relative time: 15m ago, 2h ago, Yesterday, 2d ago, Last week, 2w ago."""
    if minutes_ago < 1:
        return "Just now"
    if minutes_ago < 60:
        return f"{minutes_ago}m ago"
    hours = minutes_ago // 60
    if hours < 24:
        return f"{hours}h ago"
    days = hours // 24
    if days == 1:
        return "Yesterday"
    if days < 7:
        return f"{days}d ago"
    weeks = days // 7
    if weeks == 1:
        return "Last week"
    if weeks < 4:
        return f"{weeks}w ago"
    months = days // 30
    if months == 1:
        return "1mo ago"
    return f"{months}mo ago"
