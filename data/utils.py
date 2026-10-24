from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from scrapers.geo_calendar_dict import DAYS_OF_WEEK, MONTHS_DV


def slugify(text: str) -> str:
    """Create a URL-safe lowercase slug from text."""
    t = text.lower().strip()
    t = re.sub(r"[^\w\s-]", "", t)
    t = re.sub(r"[\s_]+", "-", t)
    return t.strip("-") or "entity"


def detect_entity_type(name: str) -> str:
    """Infer the category of an entity from its name."""
    n = name.lower()
    if any(k in n for k in ["council", "ކައުންސިލް", "secretariat"]):
        return "Council"
    if any(k in n for k in ["ministry", "މިނިސްޓްރީ"]):
        return "Ministry"
    if any(k in n for k in ["hospital", "މަރުކަޒު", "health", "clinic", "ޞިއްޙީ"]):
        return "Healthcare"
    if any(k in n for k in ["school", "ސްކޫލް", "university", "college", "polytechnic", "ޔުނިވަރސިޓީ"]):
        return "Education"
    if any(k in n for k in ["ltd", "pvt", "plc", "corporation", "company", "ކޯޕަރޭޝަން", "ކޮމްޕެނީ", "ލިމިޓެޑް"]):
        return "SOE"
    if any(k in n for k in ["authority", "commission", "service", "office", "court", "ސަރވިސް", "އޮތޯރިޓީ"]):
        return "Independent"
    return "Other"


def format_tender_date(dt_str: Optional[str]) -> str:
    """Format ISO or raw date strings into clean English: '04 Nov 2026, 11:00 AM'."""
    if not dt_str:
        return "Not announced"
    clean = dt_str.replace("Z", "").strip()
    try:
        if "T" in clean:
            dt = datetime.fromisoformat(clean)
            if dt.hour == 0 and dt.minute == 0:
                return dt.strftime("%d %b %Y")
            return dt.strftime("%d %b %Y, %I:%M %p")
        elif re.match(r"^\d{4}-\d{2}-\d{2}$", clean):
            dt = datetime.strptime(clean, "%Y-%m-%d")
            return dt.strftime("%d %b %Y")
    except Exception:
        pass
    return normalize_tender_info(clean)


def normalize_tender_info(info_str: Optional[str]) -> str:
    """Normalize Thaana months, days, and timestamps in tender info into clean English."""
    if not info_str:
        return "Not announced / Refer to docs"
    text = info_str.strip()

    # Replace Thaana months with English abbreviations
    for dv_m, en_m in MONTHS_DV.items():
        text = re.sub(re.escape(dv_m), en_m[:3], text)

    # Replace Thaana days of week
    for dv_d, en_d in DAYS_OF_WEEK.items():
        text = re.sub(re.escape(dv_d), en_d, text)

    # Replace common Thaana administrative / venue terms
    replacements = [
        ("ވާ", ""),
        ("ދުވަހުގެ", ""),
        ("ޕްރޮކިއުމަންޓް ސެކްޝަން", "Procurement Section"),
        ("މަޢުލޫމާތު ސާފުކުރުން", "Information Session"),
        ("މަޢުލޫމާތު ދިނުން", "Information Session"),
        ("މީޓިންގ ރޫމް", "Meeting Room"),
        ("ކޮންފަރެންސް ހޯލް", "Conference Hall"),
        ("މާލަމު", "Hall"),
        ("ހެނދުނު", "AM"),
        ("މެންދުރުފަސް", "PM"),
        ("ހަވީރު", "PM"),
        ("ރޭގަނޑު", "PM"),
        ("ގަޑި", "@"),
        ("މިއިދާރާ", "Authority Office"),
        ("ކައުންސިލް އިދާރާ", "Council Office"),
    ]
    for dv_term, en_term in replacements:
        text = text.replace(dv_term, en_term)

    # Clean up excess spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text

