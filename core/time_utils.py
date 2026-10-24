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
