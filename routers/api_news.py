"""
News and Alert Preferences API Router.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Request

from data.database import get_db, register_or_update_telegram_subscriber
from services.news_service import get_live_news

router = APIRouter()


@router.get("/api/news")
def api_news(
    topic: Optional[str] = None,
    tag: Optional[str] = None,
    section: Optional[str] = None,
    refresh: Optional[str] = None,
):
    """API endpoint to get live news feed items."""
    articles = get_live_news(force_refresh=(refresh == "1"))
    if topic:
        articles = [a for a in articles if a.get("topic") == topic]
    if tag:
        articles = [a for a in articles if tag in a.get("tags", [])]
    if section:
        articles = [a for a in articles if a.get("section") == section]
    return {"count": len(articles), "articles": articles}


@router.post("/api/alerts/preferences")
async def save_alert_preferences(request: Request):
    """Save alert categories and discipline filters for a Telegram subscriber."""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    chat_id = str(data.get("chat_id") or "").strip()
    if not chat_id:
        raise HTTPException(status_code=400, detail="Chat ID is required")

    keywords = list(data.get("keywords") or [])
    if data.get("all_news") and "all_news" not in keywords:
        keywords.append("all_news")
    if data.get("breaking") and "breaking" not in keywords:
        keywords.append("breaking")
    if data.get("janaza") and "janaza" not in keywords:
        keywords.append("janaza")

    for t in (data.get("topics") or data.get("storylines") or []):
        if t not in keywords:
            keywords.append(t)

    disciplines = []
    if data.get("tenders") or data.get("tenders_enabled") or data.get("disciplines"):
        disciplines = data.get("disciplines") or ["All"]

    with get_db() as conn:
        register_or_update_telegram_subscriber(
            conn,
            chat_id=chat_id,
            disciplines=disciplines,
            keywords=keywords,
            is_active=1,
            reset_start_time=False,
        )

    return {"ok": True, "message": "Alert preferences updated successfully"}
