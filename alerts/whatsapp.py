"""
WhatsApp Alert Service for Khulaasaa Government Tenders & SOE Bids.
"""
from __future__ import annotations
import urllib.parse
from typing import Any, Optional


def format_whatsapp_bid(bid: dict[str, Any], base_url: str = "https://khulaasaa.tech") -> str:
    """Format a tender notice into a clean WhatsApp alert message."""
    title = bid.get("title") or "Government Tender Notice"
    ref = bid.get("ref") or bid.get("reference_number") or "N/A"
    agency = bid.get("agency") or "Government Agency"
    deadline = bid.get("deadline_iso") or bid.get("published_date") or "See notice"
    url = bid.get("source_url") or f"{base_url}/bids"

    msg = (
        f"*KHULAASAA PRO TENDER ALERT*\n"
        f"--------------------\n"
        f"Agency: {agency}\n"
        f"Notice: {title}\n"
        f"Ref: {ref}\n"
        f"Deadline: {deadline}\n"
        f"Details: {url}\n"
        f"--------------------\n"
        f"Verified via Khulaasaa Intelligence"
    )
    return msg


def get_whatsapp_share_link(bid: dict[str, Any], base_url: str = "https://khulaasaa.tech") -> str:
    """Generate a WhatsApp click-to-chat / share link for a bid notice."""
    text = format_whatsapp_bid(bid, base_url)
    return f"https://wa.me/?text={urllib.parse.quote(text)}"
