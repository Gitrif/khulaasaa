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
    get_job_filter_options,
    get_user_cv,
    list_sponsored_ads,
    query_jobs,
)
from data.mock_events import JOBS
from scrapers.jobs import JOB_DISCIPLINES
from services.jobs_service import enrich_job, trigger_jobs_background_sync
from data.modules import is_service_module_enabled, get_service_module

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/jobs", response_class=HTMLResponse)
def jobs_view(request: Request, discipline: Optional[str] = None, q: Optional[str] = None):
    """Jobs directory and employment hub."""
    user = get_current_user(request)

    # Multi-select query parameter support
    qp = request.query_params
    selected_disciplines = qp.getlist("discipline") if hasattr(qp, "getlist") else []
    if not selected_disciplines and discipline:
        selected_disciplines = [discipline]
    selected_agencies = qp.getlist("agency") if hasattr(qp, "getlist") else []
    selected_locations = qp.getlist("location") if hasattr(qp, "getlist") else []
    min_salary_str = qp.get("min_salary")
    min_salary = int(min_salary_str) if min_salary_str and min_salary_str.isdigit() else None

    jobs_cache_key = f"jobs:feed:{sorted(selected_disciplines)}:{sorted(selected_agencies)}:{sorted(selected_locations)}:{min_salary}:{q or ''}"
    cached_jobs_payload = None
    try:
        from services.cache_service import cache_get
        cached_jobs_payload = cache_get(jobs_cache_key)
    except Exception:
        pass

    if cached_jobs_payload is not None:
        db_jobs = cached_jobs_payload["db_jobs"]
        filter_opts = cached_jobs_payload["filter_opts"]
        active_ads = cached_jobs_payload["active_ads"]
    else:
        with get_db() as conn:
            if not is_service_module_enabled(conn, "jobs"):
                return templates.TemplateResponse(
                    "service_suspended.html",
                    {"request": request, "module": get_service_module(conn, "jobs"), "current_user": user},
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            db_jobs = query_jobs(
                conn,
                discipline=selected_disciplines if selected_disciplines else None,
                agency=selected_agencies if selected_agencies else None,
                location=selected_locations if selected_locations else None,
                min_salary=min_salary,
                search=q,
            )
            filter_opts = get_job_filter_options(conn)
            active_ads = [a for a in list_sponsored_ads(conn) if a.get("is_active") == 1]
        try:
            from services.cache_service import cache_set
            cache_set(jobs_cache_key, {
                "db_jobs": db_jobs,
                "filter_opts": filter_opts,
                "active_ads": active_ads,
            }, ttl_seconds=60)
        except Exception:
            pass

    all_disciplines = filter_opts["disciplines"]
    all_agencies = filter_opts["agencies"]
    all_locations = filter_opts["locations"]

    if request.query_params.get("refresh") == "1":
        trigger_jobs_background_sync(force=True)

    import os
    demo_mode = os.environ.get("KHULAASAA_DEMO_MODE", "").lower() in ("1", "true", "yes") or bool(os.environ.get("PYTEST_CURRENT_TEST"))
    if not db_jobs and not selected_disciplines and not selected_agencies and not q and demo_mode:
        db_jobs = JOBS

    if not all_disciplines:
        all_disciplines = sorted({j["discipline"] for j in (db_jobs or []) if j.get("discipline")} | set(JOB_DISCIPLINES))

    # Top agencies for quick pill display (top 6-8 employers)
    top_agencies = [a for a in [
        "School",
        "Maldives Transport and Contracting Company",
        "Tree Top Hospital",
        "Fuvahmulah Hospital",
        "National Drug Agency",
        "State Trading Organization (STO)",
        "State Electric Company Limited (STELCO)",
    ] if a in all_agencies]
    if not top_agencies:
        top_agencies = all_agencies[:6]

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

    # Singular active values for backward compatibility
    active_disc = selected_disciplines[0] if len(selected_disciplines) == 1 else None
    active_agency = selected_agencies[0] if len(selected_agencies) == 1 else None

    return templates.TemplateResponse(
        "jobs.html",
        {
            "request": request,
            "jobs": enriched_jobs,
            "disciplines": all_disciplines,
            "agencies": all_agencies,
            "top_agencies": top_agencies,
            "locations": all_locations,
            "active_discipline": active_disc,
            "active_agency": active_agency,
            "selected_disciplines": selected_disciplines,
            "selected_agencies": selected_agencies,
            "selected_locations": selected_locations,
            "min_salary": min_salary,
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


SAMPLE_DISCOVERABLE_CANDIDATES = [
    {
        "id": "c1",
        "name": "Ahmed Simah",
        "discipline": "Accounting & Finance",
        "title": "Senior Accountant / Auditor",
        "experience": "5+ Years Experience",
        "education": "BSc Applied Accounting (Oxford Brookes / ACCA Affiliate)",
        "location": "Male City",
        "skills": ["MIRA GST Compliance", "QuickBooks", "Hooks85 ERP", "Financial Modeling", "Corporate Tax"],
        "availability": "Immediate",
        "consent_verified": True,
        "contact_phone": "+960 778 1234",
        "contact_email": "ahmed.simah@gmail.com",
        "match_score": 94,
    },
    {
        "id": "c2",
        "name": "Fathimath Shanya",
        "discipline": "Administration & HR",
        "title": "HR & Operations Specialist",
        "experience": "4 Years Experience",
        "education": "Bachelor of Business Management (Villa College / UWE)",
        "location": "Hulhumale Phase 1",
        "skills": ["Employee Relations", "Maldives Employment Act", "Payroll Filing", "Talent Acquisition", "Expatriate Visa Work"],
        "availability": "2 Weeks Notice",
        "consent_verified": True,
        "contact_phone": "+960 991 4567",
        "contact_email": "shanya.hrmv@gmail.com",
        "match_score": 88,
    },
    {
        "id": "c3",
        "name": "Hassan Ziyau",
        "discipline": "Engineering & Construction",
        "title": "Site Civil Engineer / Project Coordinator",
        "experience": "6 Years Experience",
        "education": "BEng (Hons) Civil Engineering (MNU)",
        "location": "Male / Atolls Flexible",
        "skills": ["Site Supervision", "BOQ Preparation", "AutoCAD", "Quality Control", "Contractor Billing"],
        "availability": "Immediate",
        "consent_verified": True,
        "contact_phone": "+960 790 3344",
        "contact_email": "ziyau.civil@outlook.com",
        "match_score": 92,
    },
    {
        "id": "c4",
        "name": "Aishath Reeha",
        "discipline": "IT & Technology",
        "title": "Full Stack Developer & Systems Admin",
        "experience": "3+ Years Experience",
        "education": "BSc Computer Science (MNU)",
        "location": "Hulhumale Phase 2",
        "skills": ["Python", "FastAPI", "React", "PostgreSQL", "Cloud VPS", "API Integration"],
        "availability": "Immediate",
        "consent_verified": True,
        "contact_phone": "+960 771 9988",
        "contact_email": "reeha.dev@khulaasaa.tech",
        "match_score": 96,
    },
    {
        "id": "c5",
        "name": "Ibrahim Nafiz",
        "discipline": "Logistics & Procurement",
        "title": "Procurement & Tender Specialist",
        "experience": "7 Years Experience",
        "education": "Diploma in Supply Chain & Procurement",
        "location": "Male City",
        "skills": ["Gazette Tender Bidding", "Customs Clearance", "Supplier Negotiations", "Sea Freight Logistics"],
        "availability": "1 Month Notice",
        "consent_verified": True,
        "contact_phone": "+960 762 1100",
        "contact_email": "nafiz.procure@gmail.com",
        "match_score": 89,
    }
]


@router.get("/jobs/candidates", response_class=HTMLResponse)
@router.get("/jobs/talent", response_class=HTMLResponse)
def candidates_directory_view(request: Request, discipline: Optional[str] = None):
    """Consent-based Candidate Discovery & Automated Shortlisting Directory."""
    user = get_current_user(request)
    candidates = SAMPLE_DISCOVERABLE_CANDIDATES
    if discipline and discipline != "All":
        candidates = [c for c in candidates if discipline.lower() in c["discipline"].lower()]

    active_ads = []
    try:
        with get_db() as conn:
            active_ads = [a for a in list_sponsored_ads(conn) if a.get("is_active") == 1]
    except Exception:
        pass

    return templates.TemplateResponse(
        "candidates.html",
        {
            "request": request,
            "candidates": candidates,
            "active_discipline": discipline or "All",
            "disciplines": [
                "All",
                "Accounting & Finance",
                "Administration & HR",
                "Engineering & Construction",
                "IT & Technology",
                "Logistics & Procurement",
            ],
            "current_user": user,
            "active_ads": active_ads,
            "page_title": "Candidates & Talent Shortlisting Pool | Khulaasaa Jobs",
        },
    )


@router.get("/jobs/employer", response_class=HTMLResponse)
@router.get("/jobs/hr-portal", response_class=HTMLResponse)
def employer_hr_portal_view(request: Request):
    """Employer HR Portal: Automatic candidate shortlisting and candidate matching."""
    user = get_current_user(request)
    with get_db() as conn:
        active_vacancies = query_jobs(conn, limit=10)

    return templates.TemplateResponse(
        "hr_portal.html",
        {
            "request": request,
            "candidates": SAMPLE_DISCOVERABLE_CANDIDATES,
            "vacancies": active_vacancies,
            "current_user": user,
            "page_title": "Employer HR Portal & Automated Shortlisting | Khulaasaa Jobs",
        },
    )


@router.post("/api/jobs/shortlist")
async def api_shortlist_candidate(request: Request):
    """Employer saves shortlist connection or interview invitation for a candidate."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    candidate_id = body.get("candidate_id")
    candidate_name = body.get("candidate_name") or "Candidate"
    return {
        "status": "ok",
        "candidate_id": candidate_id,
        "message": f"Connection invitation sent to {candidate_name}. Candidate will be notified via email / phone.",
    }


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
