"""
Authentication API Router (Registration, Login, Sessions, OAuth / Telegram / Viber).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from urllib.parse import parse_qsl
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from core.deps import get_current_user
from alerts.telegram_client import get_telegram_credentials
from data.database import (
    authenticate_user,
    create_user,
    create_user_session,
    delete_user_session,
    get_db,
    get_user_by_email,
    get_user_by_id,
    get_user_by_telegram_id,
    get_platform_identity,
    upsert_platform_identity,
    update_user_plan,
    create_password_reset_token,
    verify_and_consume_password_reset_token,
    update_user_profile,
    change_user_password,
    get_user_follow_counts,
)
from services.hooks85_service import login_via_hooks85, register_via_hooks85
from routers.api_user_alerts import router as alerts_router

router = APIRouter()
router.include_router(alerts_router)

@router.post("/api/auth/register")
async def api_register(request: Request):
    """Register a new user account with hooks85 Gateway or local storage."""
    payload = await request.json()
    email = payload.get("email", "").strip().lower()
    password = payload.get("password", "")
    full_name = payload.get("full_name", "").strip()
    phone = payload.get("phone", "").strip() or None
    cats = payload.get("job_alert_categories") or ["all"]

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email address is required")
    if not password or len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if not full_name:
        raise HTTPException(status_code=400, detail="Full name is required")

    # Registration must never become an alternate sign-in path for an existing account.
    # Channel IDs are intentionally not accepted here: linking requires provider verification.
    with get_db() as conn:
        if get_user_by_email(conn, email):
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists. Please sign in instead.",
            )

    h85_session_cookie = ""
    # Attempt registration via hooks85 Gateway. If the Gateway is unavailable,
    # preserve the established local-registration fallback.
    h85_res = register_via_hooks85(email, password, full_name)
    if h85_res and h85_res.get("status") == "ok":
        h85_session_cookie = h85_res.get("cookie_val") or ""
    elif h85_res and h85_res.get("code") == 409:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists. Please sign in instead.",
        )

    with get_db() as conn:
        # Recheck inside the write transaction to close the registration race.
        if get_user_by_email(conn, email):
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists. Please sign in instead.",
            )
        user_id = create_user(
            conn,
            email=email,
            password=password,
            full_name=full_name,
            phone=phone,
            job_alert_categories=cats,
            is_paid=0,
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
        "sample1": {"email": "ahmed.naseem.demo@example.mv", "name": "Ahmed Naseem", "phone": "+960 700 0001"},
        "sample2": {"email": "mariyam.zoya.demo@example.mv", "name": "Mariyam Zoya", "phone": "+960 700 0002"},
        "sample3": {"email": "hassan.rasheed.demo@example.mv", "name": "Hassan Rasheed", "phone": "+960 700 0003"},
    }
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


def _validate_telegram_webapp_init_data(
    init_data: str,
    bot_token: str,
    max_age_seconds: int = 86400,
) -> Optional[dict[str, Any]]:
    """Validate Telegram Mini App initData using Telegram's documented HMAC scheme."""
    if not init_data or not bot_token:
        return None

    fields = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = fields.pop("hash", "")
    if not received_hash:
        return None

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in sorted(fields.items())
    )
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        return None

    try:
        auth_date = int(fields.get("auth_date", "0"))
    except (TypeError, ValueError):
        return None

    now = int(time.time())
    if auth_date <= 0 or now - auth_date > max_age_seconds or auth_date > now + 60:
        return None

    try:
        user_data = json.loads(fields.get("user") or "{}")
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(user_data, dict) or not user_data.get("id"):
        return None
    return user_data


@router.post("/api/auth/telegram-login")
async def api_telegram_login(request: Request):
    """Authenticate a Telegram Mini App only from a valid signed initData payload."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    init_data = str(body.get("init_data") or "").strip()
    bot_token, _ = get_telegram_credentials()
    telegram_user = _validate_telegram_webapp_init_data(init_data, bot_token)
    if not telegram_user:
        raise HTTPException(
            status_code=401,
            detail="Telegram authentication could not be verified. Reopen Khulaasaa from Telegram.",
        )

    telegram_id = str(telegram_user["id"]).strip()
    username = str(telegram_user.get("username") or "").strip().lstrip("@")
    first_name = str(telegram_user.get("first_name") or "").strip()
    last_name = str(telegram_user.get("last_name") or "").strip()
    name = " ".join(part for part in (first_name, last_name) if part) or username or "Telegram User"

    with get_db() as conn:
        identity = get_platform_identity(conn, "telegram", telegram_id)
        user = (
            get_user_by_id(conn, identity["user_id"])
            if identity and identity.get("user_id") is not None
            else get_user_by_telegram_id(conn, telegram_id)
        )
        if not user:
            clean_email = f"telegram_{telegram_id}@khulaasaa.tech"
            user = get_user_by_email(conn, clean_email)
            if not user:
                uid = create_user(
                    conn,
                    email=clean_email,
                    password=secrets.token_urlsafe(32),
                    full_name=name,
                    telegram_chat_id=telegram_id,
                    job_alert_categories=["all"],
                )
                user = get_user_by_id(conn, uid)

        if not user:
            raise HTTPException(status_code=500, detail="Unable to resolve Telegram account")

        # A valid signed Telegram payload proves control of this provider identity.
        # Keep the canonical identity mapping and legacy user fields synchronized.
        conn.execute(
            "UPDATE users SET telegram_chat_id = ?, telegram_verified = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
            (telegram_id, user["id"]),
        )
        upsert_platform_identity(
            conn, "telegram", telegram_id,
            provider_username=username or None,
            display_name=name,
            user_id=user["id"],
            verified=True,
        )
        user = get_user_by_id(conn, user["id"])
        token = create_user_session(conn, user["id"])

    response = JSONResponse({"status": "ok", "user": user, "token": token})
    response.set_cookie(
        key="session_token",
        value=token,
        max_age=30 * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    return response


@router.post("/api/auth/viber-login")
async def api_viber_login(request: Request):
    """Reject unverified Viber-ID login; Viber IDs alone do not prove account ownership."""
    raise HTTPException(
        status_code=403,
        detail=(
            "Viber IDs cannot be used to sign in directly. Sign in with your Khulaasaa "
            "account, then connect Viber through Account → Connected Channels."
        ),
    )


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


@router.post("/api/auth/forgot-password")
async def api_forgot_password(request: Request):
    """
    Initiate single-use password reset flow.
    Always returns non-enumerating generic response to prevent email harvesting.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    email = (payload.get("email") or "").strip().lower()
    raw_token = None
    if email and "@" in email:
        with get_db() as conn:
            raw_token = create_password_reset_token(conn, email, expiry_hours=1)

    resp_data: dict[str, Any] = {
        "status": "ok",
        "message": "If this email is registered, instructions to reset your password have been generated.",
    }
    # Expose token for automated test assertions and local staging
    if raw_token and (os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("KHULAASAA_DEBUG")):
        resp_data["reset_token"] = raw_token

    return JSONResponse(resp_data)


@router.post("/api/auth/reset-password")
async def api_reset_password(request: Request):
    """
    Consume single-use password reset token and update account credentials.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    token = (payload.get("token") or "").strip()
    new_password = payload.get("new_password") or ""

    if not token:
        raise HTTPException(status_code=400, detail="Password reset token is required")
    if not new_password or len(new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")

    with get_db() as conn:
        success = verify_and_consume_password_reset_token(conn, token, new_password)

    if not success:
        raise HTTPException(status_code=400, detail="Invalid or expired password reset token")

    return {
        "status": "ok",
        "message": "Your password has been successfully reset. Please log in with your new password.",
    }


@router.get("/api/account/me")
def api_account_me(request: Request):
    """Retrieve detailed profile and following statistics for authenticated user."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    with get_db() as conn:
        counts = get_user_follow_counts(conn, user["id"])
        full_user = get_user_by_id(conn, user["id"])

    return {
        "status": "ok",
        "user": full_user,
        "follow_counts": counts,
    }


@router.patch("/api/account/profile")
async def api_update_profile(request: Request):
    """Update user personal profile details."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    full_name = payload.get("full_name")
    phone = payload.get("phone")

    with get_db() as conn:
        ok = update_user_profile(conn, user["id"], full_name=full_name, phone=phone)
        updated = get_user_by_id(conn, user["id"])

    return {"status": "ok", "user": updated}


@router.post("/api/account/change-password")
async def api_change_password(request: Request):
    """Change authenticated user password."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    old_password = payload.get("old_password") or ""
    new_password = payload.get("new_password") or ""

    if not old_password:
        raise HTTPException(status_code=400, detail="Current password is required")
    if not new_password or len(new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters")

    with get_db() as conn:
        ok = change_user_password(conn, user["id"], old_password, new_password)

    if not ok:
        raise HTTPException(status_code=400, detail="Incorrect current password")

    return {"status": "ok", "message": "Password changed successfully"}

