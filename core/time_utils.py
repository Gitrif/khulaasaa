"""
Time and formatting utilities.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional


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


def parse_datetime_components(
    iso_or_raw: Optional[str],
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Extract structured temporal fields from an ISO or raw date string.
    Returns: (published_at_iso, post_date, post_time)
    Example: '2026-10-26T14:30:00+05:00' -> ('2026-10-26T14:30:00+05:00', '2026-10-26', '14:30:00')
    """
    if not iso_or_raw or not str(iso_or_raw).strip():
        now = datetime.now()
        return now.isoformat(), now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")

    s = str(iso_or_raw).strip()
    try:
        # Standard ISO format with or without tz
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.isoformat(), dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S")
    except Exception:
        pass

    # Try common formats e.g. "26 Oct 2026, 11:37"
    for fmt in (
        "%d %b %Y, %H:%M",
        "%d %B %Y, %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.isoformat(), dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S")
        except Exception:
            continue

    # Fallback to date pattern match if present
    import re
    m_date = re.search(r"(\d{4}-\d{2}-\d{2})", s)
    post_date = m_date.group(1) if m_date else datetime.now().strftime("%Y-%m-%d")
    m_time = re.search(r"(\d{2}:\d{2}(?::\d{2})?)", s)
    post_time = m_time.group(1) if m_time else "00:00:00"
    if len(post_time) == 5:
        post_time += ":00"

    return f"{post_date}T{post_time}", post_date, post_time

