"""
User Alert Settings & Notification Channel Verification Router.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from core.deps import get_current_user
from data.database import (
    get_db,
    get_user_by_id,
    update_user_alert_settings,
)

router = APIRouter()


@router.get("/api/user/alert-settings")
def api_get_user_alert_settings(request: Request):
    """Retrieve full alert and connection preferences for the authenticated user."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return {"status": "ok", "user": user}


@router.post("/api/user/alert-settings")
async def api_save_user_alert_settings(request: Request):
    """Save user alert preferences (Tenders by Source/Discipline, Jobs, Telegram & Viber IDs)."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    payload = await request.json()
    tg_id = payload.get("telegram_chat_id")
    vb_id = payload.get("viber_user_id")
    t_disc = payload.get("tender_alert_disciplines") or ["All"]
    t_sources = payload.get("tender_alert_sources") or ["all"]
    j_cats = payload.get("job_alert_categories") or ["all"]
    j_sources = payload.get("job_alert_sources") or ["all"]
    enabled = payload.get("alerts_enabled", True)

    with get_db() as conn:
        update_user_alert_settings(
            conn,
            user_id=user["id"],
            telegram_chat_id=tg_id,
            viber_user_id=vb_id,
            tender_alert_disciplines=t_disc,
            tender_alert_sources=t_sources,
            job_alert_categories=j_cats,
            job_alert_sources=j_sources,
            alerts_enabled=1 if enabled else 0,
        )
        updated_user = get_user_by_id(conn, user["id"])

    return {
        "status": "ok",
        "message": "Alert preferences saved successfully",
        "user": updated_user,
    }


@router.post("/api/alerts/test-connection")
async def api_test_alert_connection(request: Request):
    """Send a real-time verification message to Telegram or Viber."""
    payload = await request.json()
    channel = payload.get("channel", "telegram").lower()
    target_id = (payload.get("target_id") or "").strip()

    user = get_current_user(request)
    if not target_id and user:
        if channel == "telegram":
            target_id = user.get("telegram_chat_id") or ""
        elif channel == "viber":
            target_id = user.get("viber_user_id") or ""

    if not target_id:
        raise HTTPException(status_code=400, detail=f"Please provide your {channel.capitalize()} ID first")

    if channel == "telegram":
        from alerts.telegram import send_telegram_message
        msg = (
            "<b>Khulaasaa Alert Connection Verified</b>\n\n"
            "Your Telegram channel is successfully linked to Khulaasaa! "
            "You will receive instant alerts for your selected tenders and job vacancies."
        )
        ok, res_msg = send_telegram_message(msg, chat_id=str(target_id).strip())
        if not ok:
            return JSONResponse(status_code=400, content={"ok": False, "detail": res_msg})
        return {"ok": True, "message": "Telegram test alert sent successfully!"}

    elif channel == "viber":
        from alerts.viber import send_viber_message
        msg = (
            "Khulaasaa Alert Connection Verified\n\n"
            "Your Viber channel is successfully linked to Khulaasaa! "
            "You will receive instant alerts for your selected tenders and job vacancies."
        )
        res = send_viber_message(str(target_id).strip(), msg)
        if res.get("status") == 0:
            return {"ok": True, "message": "Viber test alert sent successfully!"}
        return JSONResponse(status_code=400, content={"ok": False, "detail": res.get("status_message", "Failed to deliver Viber alert")})

    raise HTTPException(status_code=400, detail="Invalid alert channel")


@router.get("/api/account/notifications")
def api_get_user_notifications(request: Request, limit: int = 30, offset: int = 0):
    """Retrieve in-app notifications and unread count for the authenticated user."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    with get_db() as conn:
        from data.repos.notifications import (
            get_unread_notification_count,
            list_user_notifications,
        )
        notifs = list_user_notifications(conn, user["id"], limit=limit, offset=offset)
        unread = get_unread_notification_count(conn, user["id"])

    return {
        "status": "ok",
        "notifications": notifs,
        "unread_count": unread,
    }


@router.post("/api/account/notifications/{notification_id}/read")
def api_mark_notification_read(request: Request, notification_id: int):
    """Mark a specific notification as read."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    with get_db() as conn:
        from data.repos.notifications import mark_notification_read
        ok = mark_notification_read(conn, user["id"], notification_id)

    return {"status": "ok", "success": ok}


@router.post("/api/account/notifications/read-all")
def api_mark_all_notifications_read(request: Request):
    """Mark all unread notifications as read for current user."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    with get_db() as conn:
        from data.repos.notifications import mark_all_notifications_read
        count = mark_all_notifications_read(conn, user["id"])

    return {"status": "ok", "marked_read": count}
