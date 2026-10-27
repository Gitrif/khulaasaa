"""
API Router for User Notification Preferences.
Manages breaking alerts, followed content, frequency (instant/digest), quiet hours, and global pause.
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from core.deps import get_current_user
from data.database import get_db, get_user_preferences, update_user_preferences
from services.channel_linking_service import get_channel_connection_status

router = APIRouter(prefix="/api/account/preferences", tags=["preferences"])


@router.get("")
def api_get_preferences(request: Request):
    """Retrieve current notification preferences and verified channel status."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    with get_db() as conn:
        prefs = get_user_preferences(conn, user["id"])
        channels = get_channel_connection_status(conn, user["id"])

    return {
        "status": "ok",
        "preferences": prefs,
        "channels": channels,
    }


@router.put("")
async def api_save_preferences(request: Request):
    """Update notification preferences for the authenticated user."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    try:
        with get_db() as conn:
            updated = update_user_preferences(
                conn,
                user_id=user["id"],
                breaking_alerts=payload.get("breaking_alerts"),
                followed_content_alerts=payload.get("followed_content_alerts"),
                telegram_enabled=payload.get("telegram_enabled"),
                viber_enabled=payload.get("viber_enabled"),
                frequency=payload.get("frequency"),
                quiet_hours_enabled=payload.get("quiet_hours_enabled"),
                quiet_hours_start=payload.get("quiet_hours_start"),
                quiet_hours_end=payload.get("quiet_hours_end"),
                timezone=payload.get("timezone"),
                is_paused=payload.get("is_paused"),
            )
            channels = get_channel_connection_status(conn, user["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "ok",
        "message": "Notification preferences updated successfully",
        "preferences": updated,
        "channels": channels,
    }
