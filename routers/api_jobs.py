"""
Jobs, Employment Alerts, CV Creator, and Company Profile API Router.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from core.deps import get_current_user, require_editor
from data.database import (
    EDUCATION_LEVELS,
    LANGUAGE_PROFICIENCIES,
    STANDARD_INSTITUTIONS,
    STANDARD_LANGUAGES,
    get_company_profile,
    get_db,
    get_user_cv,
    register_or_update_telegram_subscriber,
    register_or_update_viber_subscriber,
    save_company_profile,
    save_user_cv,
    update_user_job_alerts,
    update_user_plan,
)
from scrapers.jobs import sync_jobs
from alerts.telegram import format_job_alert_html, send_telegram_message
from alerts.viber import format_viber_job, send_viber_message

# Include auth router for backward compatibility
from routers.api_auth import router as auth_router

router = APIRouter()
router.include_router(auth_router)

@router.get("/api/cv")
def api_get_cv(request: Request):
    """Retrieve saved CV for the authenticated user."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required to access saved CVs")

    with get_db() as conn:
        cv_record = get_user_cv(conn, user["id"])
    return {"cv": cv_record}


@router.post("/api/cv")
async def api_save_cv(request: Request):
    """Save or update user's CV in cloud storage. Exclusively for Pro/Paid subscribers."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required to save CV")

    if not user.get("is_paid"):
        raise HTTPException(
            status_code=403,
            detail="CV cloud saving and updating requires Khulaasaa Pro (MVR 30/mo). Free users can customize and print/export to PDF anytime!"
        )

    payload = await request.json()
    title = payload.get("title", "Maldivian Curriculum Vitae")
    template = payload.get("template", "standard")
    cv_data = payload.get("data", {})
    photo_data = payload.get("photo_data")

    with get_db() as conn:
        cv_id = save_user_cv(
            conn,
            user_id=user["id"],
            cv_data=cv_data,
            title=title,
            template=template,
            photo_data=photo_data,
        )
    return {"status": "ok", "cv_id": cv_id}


@router.get("/api/cv/standards")
def api_cv_standards():
    """Retrieve pre-configured standard languages, proficiencies, education levels, and colleges."""
    return {
        "languages": STANDARD_LANGUAGES,
        "proficiencies": LANGUAGE_PROFICIENCIES,
        "education_levels": EDUCATION_LEVELS,
        "institutions": STANDARD_INSTITUTIONS,
    }


@router.get("/api/company-profile")
def api_get_company_profile(request: Request):
    """Retrieve company profile for current user or default."""
    user = get_current_user(request)
    with get_db() as conn:
        profile = get_company_profile(conn, user_id=user["id"]) if user else get_company_profile(conn)
    return {"status": "ok", "profile": profile}


@router.post("/api/company-profile")
async def api_save_company_profile(request: Request):
    """Save or update company profile."""
    user = get_current_user(request)
    payload = await request.json()
    user_id = user["id"] if user else None
    profile_id = payload.get("id")

    with get_db() as conn:
        saved_id = save_company_profile(
            conn,
            profile_data=payload,
            user_id=user_id,
            profile_id=profile_id,
        )
        saved_profile = get_company_profile(conn, profile_id=saved_id)

    return {"status": "ok", "profile_id": saved_id, "profile": saved_profile}


@router.post("/api/user/job-alerts")
async def api_update_job_alerts(request: Request):
    """Update job alert categories, telegram chat ID, and viber user ID for current user."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    payload = await request.json()
    cats = payload.get("categories") or ["all"]
    telegram_chat_id = payload.get("telegram_chat_id")
    viber_user_id = payload.get("viber_user_id")

    with get_db() as conn:
        update_user_job_alerts(
            conn,
            user_id=user["id"],
            categories=cats,
            telegram_chat_id=telegram_chat_id,
            viber_user_id=viber_user_id,
        )
        if telegram_chat_id:
            register_or_update_telegram_subscriber(
                conn,
                chat_id=str(telegram_chat_id).strip(),
                name=user["full_name"],
                disciplines=cats,
                keywords=["jobs"] + cats,
            )
        if viber_user_id:
            register_or_update_viber_subscriber(
                conn,
                viber_user_id=str(viber_user_id).strip(),
                name=user["full_name"],
                categories=["jobs"] + cats,
                is_active=1,
            )

    return {
        "status": "ok",
        "categories": cats,
        "telegram_chat_id": telegram_chat_id,
        "viber_user_id": viber_user_id,
    }


@router.post("/api/user/upgrade")
def api_upgrade_user(request: Request):
    """Upgrade user to Pro/Paid tier for designer CV templates and VIP job alerts."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required to upgrade")

    with get_db() as conn:
        update_user_plan(conn, user["id"], is_paid=1)
    return {"status": "ok", "is_paid": True}


@router.post("/api/jobs/sync")
def api_jobs_sync():
    """Trigger live sync of job vacancies from gazette.gov.mv and broadcast new alerts."""
    from services.jobs_service import run_jobs_sync
    return run_jobs_sync(pages=1, trigger_alerts=True)


@router.post("/api/jobs/test-alert")
async def api_jobs_test_alert(request: Request, editor: str = Depends(require_editor)):
    """Send a test job alert to the provided Telegram chat ID."""
    payload = await request.json()
    chat_id = payload.get("chat_id")
    if not chat_id:
        user = get_current_user(request)
        if user and user.get("telegram_chat_id"):
            chat_id = user["telegram_chat_id"]
    if not chat_id:
        raise HTTPException(status_code=400, detail="Telegram chat_id is required")

    test_job = {
        "title": "Senior Administrative Officer",
        "title_en": "Senior Administrative Officer",
        "agency": "Malé City Council",
        "agency_name_en": "Malé City Council",
        "discipline": "Administration & Management",
        "location": "Male'",
        "salary_raw": "MVR 12,000 - 15,000",
        "deadline_iso": (datetime.now()).strftime("%Y-%m-%dT14:00:00"),
        "source_url": "https://gazette.gov.mv/iulaan/type/vazeefaa",
        "source_portal": "gazette.gov.mv",
    }
    import main
    msg_html = format_job_alert_html(test_job)
    send_fn = getattr(main, "send_telegram_message", send_telegram_message)
    ok, status_msg = send_fn(msg_html, chat_id=str(chat_id))
    return {"ok": ok, "message": status_msg}


@router.post("/api/jobs/test-viber-alert")
async def api_jobs_test_viber_alert(request: Request, editor: str = Depends(require_editor)):
    """Send a test job alert to the provided Viber user ID."""
    payload = await request.json()
    viber_user_id = payload.get("viber_user_id")
    if not viber_user_id:
        user = get_current_user(request)
        if user and user.get("viber_user_id"):
            viber_user_id = user["viber_user_id"]
    if not viber_user_id:
        raise HTTPException(status_code=400, detail="Viber user ID is required")

    test_job = {
        "title": "Senior Administrative Officer",
        "title_en": "Senior Administrative Officer",
        "agency": "Malé City Council",
        "agency_name_en": "Malé City Council",
        "discipline": "Administration & Management",
        "location": "Male'",
        "salary_raw": "MVR 12,000 - 15,000",
        "deadline_iso": (datetime.now()).strftime("%Y-%m-%dT14:00:00"),
        "source_url": "https://gazette.gov.mv/iulaan/type/vazeefaa",
        "source_portal": "gazette.gov.mv",
    }
    import main
    msg_text = format_viber_job(test_job)
    viber_send_fn = getattr(main, "send_viber_message", send_viber_message)
    res = viber_send_fn(str(viber_user_id).strip(), msg_text)
    if res.get("status") == 0:
        return {"ok": True, "message": "Test job alert successfully sent to Viber!"}
    else:
        return {"ok": False, "error": res.get("status_message", "Failed to send to Viber")}
