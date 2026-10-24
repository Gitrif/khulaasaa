"""
Authentication API Router (Registration, Login, Sessions, OAuth / Telegram / Viber).
"""
from __future__ import annotations

import secrets
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from core.deps import get_current_user
from data.database import (
    authenticate_user,
    create_user,
    create_user_session,
    delete_user_session,
    get_db,
    get_user_by_email,
    get_user_by_id,
    get_user_by_telegram_id,
    get_user_by_viber_id,
    register_or_update_telegram_subscriber,
    register_or_update_viber_subscriber,
    update_user_job_alerts,
    update_user_alert_settings,
    update_user_plan,
)
from services.hooks85_service import login_via_hooks85, register_via_hooks85

router = APIRouter()

@router.post("/api/auth/register")
async def api_register(request: Request):
    """Register a new user account with hooks85 Gateway or local storage."""
    payload = await request.json()
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")
    full_name = payload.get("full_name", "").strip()
    phone = payload.get("phone", "").strip() or None
    telegram_chat_id = payload.get("telegram_chat_id", "").strip() or None
    viber_user_id = payload.get("viber_user_id", "").strip() or None
    cats = payload.get("job_alert_categories") or ["all"]

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email address is required")
    if not password or len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if not full_name:
        raise HTTPException(status_code=400, detail="Full name is required")

    h85_session_cookie = ""
    # Attempt registration via hooks85 Gateway
    h85_res = register_via_hooks85(email, password, full_name)
    if h85_res and h85_res.get("status") == "ok":
        h85_session_cookie = h85_res.get("cookie_val") or ""

    with get_db() as conn:
        existing = get_user_by_email(conn, email)
        if existing:
            user_id = existing["id"]
        else:
            user_id = create_user(
                conn,
                email=email,
                password=password,
                full_name=full_name,
                phone=phone,
                telegram_chat_id=telegram_chat_id,
                viber_user_id=viber_user_id,
                job_alert_categories=cats,
                is_paid=0,
            )
        if telegram_chat_id:
            register_or_update_telegram_subscriber(
                conn,
                chat_id=str(telegram_chat_id).strip(),
                name=full_name,
                disciplines=cats,
                keywords=["jobs"] + cats,
            )
        if viber_user_id:
            register_or_update_viber_subscriber(
                conn,
                viber_user_id=str(viber_user_id).strip(),
                name=full_name,
                categories=["jobs"] + cats,
                is_active=1,
            )
        token = create_user_session(conn, user_id)
        user = get_user_by_id(conn, user_id)

    response = JSONResponse({"status": "ok", "user": user, "token": token})
    response.set_cookie(
        key="session_token",
        value=token,
        max_age=30 * 24 * 3600,
        httponly=True,
        samesite="lax",
    )
    if h85_session_cookie:
        response.set_cookie(
            key="hooks85_session",
            value=h85_session_cookie,
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax",
        )
    return response


@router.post("/api/auth/login")
async def api_login(request: Request):
    """Authenticate and sign in user via hooks85 Gateway or local credentials."""
    payload = await request.json()
    email = payload.get("email", "").strip()
    password = payload.get("password", "")

    h85_session_cookie = ""
    user = None

    # 1. Primary auth check: hooks85 Gateway
    h85_res = login_via_hooks85(email, password)
    if h85_res and h85_res.get("status") == "ok":
        h85_session_cookie = h85_res.get("cookie_val") or ""
        with get_db() as conn:
            existing = get_user_by_email(conn, email)
            if not existing:
                h85_user = h85_res.get("user") or {}
                uid = create_user(
                    conn,
                    email=email,
                    password="sso_managed_by_hooks85",
                    full_name=h85_user.get("full_name") or email.split("@")[0],
                    is_paid=h85_user.get("is_paid", 0),
                )
                user = get_user_by_id(conn, uid)
            else:
                user = existing
            token = create_user_session(conn, user["id"])
    else:
        # 2. Fallback: local SQLite accounts
        with get_db() as conn:
            user = authenticate_user(conn, email, password)
            if not user:
                raise HTTPException(status_code=401, detail="Invalid email or password")
            token = create_user_session(conn, user["id"])

    response = JSONResponse({"status": "ok", "user": user, "token": token})
    response.set_cookie(
        key="session_token",
        value=token,
        max_age=30 * 24 * 3600,
        httponly=True,
        samesite="lax",
    )
    if h85_session_cookie:
        response.set_cookie(
            key="hooks85_session",
            value=h85_session_cookie,
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite="lax",
        )
    return response


@router.post("/api/auth/demo-login")
async def api_demo_login(request: Request):
    """Fast 1-click demo login for evaluating the CV Creator and alerts."""
    payload = await request.json()
    user_key = payload.get("user_key", "shifau")

    demo_profiles = {
        "sample1": {
            "email": "ahmed.naseem.demo@example.mv",
            "name": "Ahmed Naseem",
            "phone": "+960 700 0001",
        },
        "sample2": {
            "email": "mariyam.zoya.demo@example.mv",
            "name": "Mariyam Zoya",
            "phone": "+960 700 0002",
        },
        "sample3": {
            "email": "hassan.rasheed.demo@example.mv",
            "name": "Hassan Rasheed",
            "phone": "+960 700 0003",
        },
    }
    # Backward compatibility aliases for previous test keys
    demo_profiles["shifau"] = demo_profiles["sample1"]
    demo_profiles["simah"] = demo_profiles["sample3"]
    demo_profiles["zeenath"] = demo_profiles["sample2"]

    prof = demo_profiles.get(user_key, demo_profiles["sample1"])

    with get_db() as conn:
        user = get_user_by_email(conn, prof["email"])
        if not user:
            uid = create_user(
                conn,
                email=prof["email"],
                password="demopassword123",
                full_name=prof["name"],
                phone=prof["phone"],
                job_alert_categories=["all"],
                is_paid=1 if user_key == "simah" else 0,
            )
            user = get_user_by_id(conn, uid)
        token = create_user_session(conn, user["id"])

    response = JSONResponse({"status": "ok", "user": user, "token": token})
    response.set_cookie(
        key="session_token",
        value=token,
        max_age=30 * 24 * 3600,
        httponly=True,
        samesite="lax",
    )
    return response


@router.post("/api/auth/telegram-login")
async def api_telegram_login(request: Request):
    """Authenticate or auto-register a user via Telegram web connect or Mini App."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    chat_id = str(body.get("chat_id") or body.get("id") or "").strip()
    username = (body.get("username") or "").strip().lstrip("@")
    name = body.get("name") or body.get("first_name") or username or "Telegram User"

    if not chat_id and username:
        chat_id = f"tg_{username.lower()}"

    if not chat_id:
        raise HTTPException(status_code=400, detail="Telegram Chat ID or @username is required")

    with get_db() as conn:
        user = get_user_by_telegram_id(conn, chat_id)
        if not user:
            clean_email = f"telegram_{chat_id.replace('tg_', '')}@khulaasaa.tech"
            user = get_user_by_email(conn, clean_email)
            if not user:
                uid = create_user(
                    conn,
                    email=clean_email,
                    password=secrets.token_urlsafe(16),
                    full_name=name,
                    telegram_chat_id=chat_id,
                    job_alert_categories=["all"],
                )
                user = get_user_by_id(conn, uid)
            else:
                conn.execute("UPDATE users SET telegram_chat_id = ? WHERE id = ?;", (chat_id, user["id"]))
                user["telegram_chat_id"] = chat_id

        token = create_user_session(conn, user["id"])

    response = JSONResponse({"status": "ok", "user": user, "token": token})
    response.set_cookie(
        key="session_token",
        value=token,
        max_age=30 * 24 * 3600,
        httponly=True,
        samesite="lax",
    )
    return response


@router.post("/api/auth/viber-login")
async def api_viber_login(request: Request):
    """Authenticate or auto-register a user via Viber web connect."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    viber_id = str(body.get("viber_user_id") or body.get("phone") or "").strip()
    name = body.get("name") or "Viber Subscriber"

    if not viber_id:
        raise HTTPException(status_code=400, detail="Viber User ID or phone number is required")

    with get_db() as conn:
        user = get_user_by_viber_id(conn, viber_id)
        if not user:
            clean_email = f"viber_{viber_id.replace('+', '')}@khulaasaa.tech"
            user = get_user_by_email(conn, clean_email)
            if not user:
                uid = create_user(
                    conn,
                    email=clean_email,
                    password=secrets.token_urlsafe(16),
                    full_name=name,
                    phone=viber_id if viber_id.replace("+", "").isdigit() else None,
                    viber_user_id=viber_id,
                    job_alert_categories=["all"],
                )
                user = get_user_by_id(conn, uid)
            else:
                conn.execute("UPDATE users SET viber_user_id = ? WHERE id = ?;", (viber_id, user["id"]))
                user["viber_user_id"] = viber_id

        register_or_update_viber_subscriber(
            conn,
            viber_user_id=viber_id,
            name=name,
            categories=["all", "news", "janaza", "bids", "jobs"],
            is_active=1,
        )
        token = create_user_session(conn, user["id"])

    response = JSONResponse({"status": "ok", "user": user, "token": token})
    response.set_cookie(
        key="session_token",
        value=token,
        max_age=30 * 24 * 3600,
        httponly=True,
        samesite="lax",
    )
    return response


@router.post("/api/auth/logout")
def api_logout(request: Request):
    """Log out user and invalidate session."""
    token = request.cookies.get("session_token")
    if token:
        with get_db() as conn:
            delete_user_session(conn, token)
    response = JSONResponse({"status": "ok"})
    response.delete_cookie("session_token")
    response.delete_cookie("hooks85_session")
    return response


@router.get("/api/auth/me")
def api_auth_me(request: Request):
    """Get current authenticated user info."""
    user = get_current_user(request)
    return {"user": user}


@router.post("/api/auth/start-trial")
async def api_start_trial(request: Request):
    """Start 1-month free trial for the current user or guest session."""
    user = get_current_user(request)
    with get_db() as conn:
        if user:
            update_user_plan(conn, user["id"], is_paid=1)
            return JSONResponse({"status": "ok", "message": "1-Month Pro Trial activated!", "is_paid": True})
        else:
            import uuid
            guest_email = f"trial_{uuid.uuid4().hex[:8]}@khulaasaa.tech"
            user_id = create_user(
                conn,
                email=guest_email,
                password="trial_user_secret",
                full_name="Trial Member",
                is_paid=1,
            )
            token = create_user_session(conn, user_id, days_valid=30)
            response = JSONResponse({"status": "ok", "message": "1-Month Pro Trial activated!", "is_paid": True, "token": token})
            response.set_cookie(key="session_token", value=token, max_age=86400 * 30, httponly=True, samesite="lax")
            return response


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


