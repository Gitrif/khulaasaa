"""
Jobs & Employment Hub Web UI Router.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from core.deps import get_current_user, templates
from data.database import (
    get_db,
    get_job_by_id,
    get_job_disciplines,
    get_user_cv,
    list_sponsored_ads,
    query_jobs,
)
from data.mock_events import JOBS
from scrapers.jobs import JOB_DISCIPLINES
from services.jobs_service import enrich_job

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/jobs", response_class=HTMLResponse)
def jobs_view(request: Request, discipline: Optional[str] = None, q: Optional[str] = None):
    """Jobs directory and employment hub."""
    user = get_current_user(request)
    with get_db() as conn:
        db_jobs = query_jobs(conn, discipline=discipline, search=q)
        all_disciplines = get_job_disciplines(conn)

    if not db_jobs and not discipline and not q:
        db_jobs = JOBS

    if not all_disciplines:
        all_disciplines = sorted({j["discipline"] for j in JOBS} | set(JOB_DISCIPLINES))

    # Golden Rule: If any link is broken, omit it; if no valid link exists, remove the post
    enriched_jobs = [
        ej for ej in (enrich_job(j) for j in db_jobs)
        if ej.get("application_sources") and len(ej["application_sources"]) > 0
    ]

    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.query_params.get("partial") == "1":
        return templates.TemplateResponse(
            "components/jobs_stream.html",
            {
                "request": request,
                "jobs": enriched_jobs,
            },
        )

    active_ads = []
    try:
        with get_db() as conn:
            active_ads = [a for a in list_sponsored_ads(conn) if a.get("is_active") == 1]
    except Exception:
        pass

    return templates.TemplateResponse(
        "jobs.html",
        {
            "request": request,
            "jobs": enriched_jobs,
            "disciplines": all_disciplines,
            "active_discipline": discipline,
            "search_query": q,
            "current_user": user,
            "active_ads": active_ads,
        },
    )


@router.get("/jobs/cv", response_class=HTMLResponse)
def cv_creator_view(request: Request):
    """Maldivian CV Creator workspace."""
    user = get_current_user(request)
    cv_record = None
    if user:
        with get_db() as conn:
            cv_record = get_user_cv(conn, user["id"])

    return templates.TemplateResponse(
        "cv_creator.html",
        {
            "request": request,
            "current_user": user,
            "saved_cv": cv_record,
            "page_title": "Maldivian CV Creator | Khulaasaa Jobs",
        },
    )


@router.get("/jobs/{job_id}")
def job_redirect_or_view(request: Request, job_id: str):
    """Deep link to job notice or application portal."""
    job = None
    with get_db() as conn:
        job = get_job_by_id(conn, job_id)
        if not job:
            row = conn.execute(
                "SELECT * FROM jobs WHERE notice_id = ? OR CAST(id AS TEXT) = ? LIMIT 1;",
                (job_id, job_id),
            ).fetchone()
            if row:
                job = dict(row)

    if not job:
        match_static = next((j for j in JOBS if str(j.get("id")) == job_id or str(j.get("notice_id")) == job_id), None)
        if match_static:
            job = match_static

    if not job:
        return RedirectResponse(url="/jobs", status_code=status.HTTP_303_SEE_OTHER)

    src = job.get("source_url")
    if not src or "/type/vazeefaa" in src or src.endswith("/iulaan") or src.endswith("/iulaan?type=vazeefaa"):
        nid = job.get("notice_id", "").replace("job-", "")
        src = f"https://gazette.gov.mv/iulaan/{nid}" if nid else "/jobs"
    return RedirectResponse(url=src, status_code=status.HTTP_303_SEE_OTHER)
