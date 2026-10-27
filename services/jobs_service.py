"""
Jobs Intelligence and Card Enrichment Service.
Handles employer branding, official logo mapping, deadline formatting,
and multi-source application hierarchy (including strict HDC-only prioritization).
"""
from __future__ import annotations

import datetime
import logging
import re
import threading
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

_LIVE_JOBS_LOCK = threading.Lock()
_LIVE_JOBS_LAST_SYNC: float = 0.0
_LIVE_JOBS_IS_SYNCING: bool = False
JOBS_CACHE_TTL_SECONDS = 900  # 15 minutes

_JOBS_SYNC_STATUS: dict[str, Any] = {
    "status": "idle",
    "last_run": None,
    "last_success": None,
    "last_error": None,
    "fetched": 0,
    "new": 0,
    "updated": 0,
    "alerts_sent": 0,
}


def get_jobs_sync_status() -> dict[str, Any]:
    """Return operational status of the jobs synchronization pipeline."""
    return dict(_JOBS_SYNC_STATUS)


def run_jobs_sync(pages: int = 1, trigger_alerts: bool = True) -> dict[str, Any]:
    """Execute jobs synchronization with concurrency protection and operational tracking."""
    global _LIVE_JOBS_IS_SYNCING, _LIVE_JOBS_LAST_SYNC
    with _LIVE_JOBS_LOCK:
        if _LIVE_JOBS_IS_SYNCING:
            return {"status": "already_running"}
        _LIVE_JOBS_IS_SYNCING = True

    start_iso = datetime.datetime.now().isoformat()
    _JOBS_SYNC_STATUS["status"] = "running"
    _JOBS_SYNC_STATUS["last_run"] = start_iso

    try:
        from data.database import get_db
        from scrapers.jobs import sync_jobs
        with get_db() as conn:
            result = sync_jobs(conn, pages=pages, trigger_alerts=trigger_alerts)

        _JOBS_SYNC_STATUS.update({
            "status": "success",
            "last_success": datetime.datetime.now().isoformat(),
            "fetched": result.get("fetched", 0),
            "new": result.get("new", 0),
            "updated": result.get("updated", 0),
            "alerts_sent": result.get("alerts_sent", 0),
            "last_error": None,
        })
        _LIVE_JOBS_LAST_SYNC = time.time()
        return result
    except Exception as exc:
        logger.error("Jobs synchronization failed: %s", exc, exc_info=True)
        _JOBS_SYNC_STATUS.update({
            "status": "failed",
            "last_error": str(exc),
        })
        return {"status": "failed", "error": str(exc)}
    finally:
        _LIVE_JOBS_IS_SYNCING = False


def trigger_jobs_background_sync(force: bool = False, pages: int = 1) -> bool:
    """Schedule asynchronous jobs synchronization if TTL expired and not already active."""
    global _LIVE_JOBS_IS_SYNCING, _LIVE_JOBS_LAST_SYNC
    now = time.time()
    with _LIVE_JOBS_LOCK:
        if _LIVE_JOBS_IS_SYNCING:
            return False
        if not force and _LIVE_JOBS_LAST_SYNC > 0 and (now - _LIVE_JOBS_LAST_SYNC < JOBS_CACHE_TTL_SECONDS):
            return False
        _LIVE_JOBS_IS_SYNCING = True
        worker = threading.Thread(
            target=run_jobs_sync,
            kwargs={"pages": pages, "trigger_alerts": True},
            daemon=True,
            name="JobsSyncWorker"
        )
        worker.start()
        return True


def get_employer_logo(agency: str) -> Optional[str]:
    """Map employer agency name to local high-resolution SVG/PNG logo if available."""
    if not agency:
        return None
    a = agency.lower()
    if "hdc" in a or "housing development" in a:
        return "/static/logos/hdc.svg"
    elif "sto" in a or "state trading" in a:
        return "/static/logos/sto.svg"
    elif "stelco" in a or "state electric" in a:
        return "/static/logos/stelco.svg"
    elif "mwsc" in a or "water and sewerage" in a:
        return "/static/logos/mwsc.svg"
    elif "macl" in a or "airports company" in a or "velana" in a:
        return "/static/logos/macl.svg"
    elif "mira" in a or "revenue authority" in a:
        return "/static/logos/mira.png"
    elif "igmh" in a or "indira gandhi" in a:
        return "/static/logos/igmh.svg"
    elif "male' city council" in a or "malé city council" in a or "city council" in a:
        return "/static/logos/malecity.svg"
    elif "joali" in a:
        return "/static/logos/joali.svg"
    elif "finolhu" in a:
        return "/static/logos/finolhu.svg"
    elif "tree top" in a:
        return "/static/logos/treetop.svg"
    elif any(term in a for term in ("ministry", "school", "court", "council", "commission", "department", "authority", "service")):
        return "/static/logos/gazette.svg"
    return None


def get_employer_initials(agency: str) -> str:
    """Generate 2-letter uppercase monogram fallback for agencies without custom icons."""
    if not agency:
        return "MV"
    clean = re.sub(r"[^A-Za-z0-9 ]+", " ", agency).strip()
    words = [w for w in clean.split() if w.lower() not in ("plc", "ltd", "limited", "the", "and", "of", "in")]
    if not words:
        return "MV"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


def format_deadline(deadline_iso: Optional[str]) -> dict[str, Any]:
    """Format ISO deadline into user-friendly date and status indicator."""
    if not deadline_iso:
        return {
            "formatted": "Open Until Filled",
            "is_urgent": False,
            "badge_color": "text-slate-600 bg-slate-100",
        }

    try:
        dt = datetime.datetime.fromisoformat(deadline_iso.replace("Z", "+00:00"))
        now = datetime.datetime.now(dt.tzinfo) if dt.tzinfo else datetime.datetime.now()
        date_str = dt.strftime("%d %b %Y")
        time_str = dt.strftime("%H:%M")
        display = f"{date_str}" + (f", {time_str}" if time_str != "00:00" else "")

        diff = (dt.date() - now.date()).days
        if diff < 0:
            status = "Closed"
            badge = "text-rose-700 bg-rose-50 border-rose-200"
            urgent = False
        elif diff == 0:
            status = f"Today ({display})"
            badge = "text-amber-700 bg-amber-50 border-amber-200"
            urgent = True
        elif diff <= 3:
            status = f"{diff}d left ({display})"
            badge = "text-amber-700 bg-amber-50 border-amber-200"
            urgent = True
        else:
            status = display
            badge = "text-flag bg-red-50/60 border-red-200/50"
            urgent = False

        return {
            "formatted": status,
            "raw_date": date_str,
            "is_urgent": urgent,
            "badge_class": badge,
        }
    except Exception:
        return {
            "formatted": str(deadline_iso)[:10],
            "raw_date": str(deadline_iso)[:10],
            "is_urgent": False,
            "badge_class": "text-slate-600 bg-slate-100",
        }


def enrich_job(job: dict[str, Any]) -> dict[str, Any]:
    """
    Enrich raw job dictionary with employer branding, formatted deadline,
    requirements summary, and source hierarchy.
    
    Source rules:
    - If job is from HDC: HDC is the ONLY source shown ('HDC Careers' / 'https://hdc.mv/careers/').
    - If job is not from HDC: show available sources (Gazette, Job-Maldives, etc.)
      allowing users to apply through either.
    """
    j = dict(job)

    # Employer naming & branding
    agency_en = j.get("agency_name_en")
    agency_raw = j.get("agency") or ""
    if not agency_en or agency_en in ["Government Authority", "Government Agency", "Maldivian Employer", "from ،", "،"]:
        if agency_raw:
            from scrapers.translator import translate_agency
            agency_en = translate_agency(agency_raw)
    agency = agency_en or agency_raw or "Maldivian Employer"
    j["employer_name"] = agency
    j["employer_logo"] = get_employer_logo(agency)
    j["employer_initials"] = get_employer_initials(agency)

    # Clean designation and Thaana check
    title_en = j.get("title_en")
    title_raw = j.get("title") or ""
    if not title_en or title_en in ["Administrator", "Officer"] and "ކޯޓު" in title_raw:
        from scrapers.jobs import translate_job_title
        title_en = translate_job_title(title_raw)
    j["designation"] = title_en or title_raw or "Position Open"

    # Clean location & Remuneration
    j["location_clean"] = j.get("location") or "Male'"
    salary = j.get("salary_raw")
    if salary == "Civil Service Remuneration Matrix" and j.get("notice_id", "").isdigit():
        try:
            from scrapers.jobs_enricher import enrich_gazette_job_notice
            enr = enrich_gazette_job_notice(j["notice_id"])
            if enr.get("salary_raw") and enr["salary_raw"] != "Pay not listed":
                salary = enr["salary_raw"]
                j["salary_raw"] = salary
            if enr.get("location"):
                j["location_clean"] = enr["location"]
        except Exception:
            pass
    j["has_salary"] = bool(salary and salary.strip() and salary.strip().lower() != "none")
    j["remuneration_clean"] = salary.strip() if j["has_salary"] else None

    # Application Deadline
    j["deadline_info"] = format_deadline(j.get("deadline_iso"))

    # Requirements summary
    req = j.get("requirements")
    j["requirements_clean"] = req.strip() if req and req.strip() and req.strip().lower() != "none" else None

    # Source Prioritization & Multi-Source Application Setup (Strict Hierarchy)
    # Rule 1: Employer Direct Portal (SOEs & direct enterprise portals) -> ONLY show employer portal
    # Rule 2: Government Gazette & other boards -> ONLY show Gazette
    # Rule 3: Neither employer direct nor Gazette -> show all available 3rd party sources
    agency_lower = agency.lower()
    portal_lower = (j.get("source_portal") or "").lower()
    direct_url = j.get("source_url") or ""
    notice_slug = j.get("notice_id", "").replace("job-", "")

    SOE_CONFIGS = [
        {
            "id": "hdc",
            "matches": ("hdc", "housing development"),
            "name": "HDC Careers",
            "portal": "hdc.mv",
            "logo": "/static/logos/hdc.svg",
            "url": "https://jobs.hdc.mv/jobs/591",
            "label": "Apply via HDC Portal →",
        },
        {
            "id": "sto",
            "matches": ("sto", "state trading"),
            "name": "STO Careers",
            "portal": "sto.mv",
            "logo": "/static/logos/sto.svg",
            "url": "https://sto.mv/careers",
            "label": "Apply via STO Careers →",
        },
        {
            "id": "stelco",
            "matches": ("stelco", "state electric"),
            "name": "STELCO Careers",
            "portal": "stelco.com.mv",
            "logo": "/static/logos/stelco.svg",
            "url": "https://stelco.com.mv/careers",
            "label": "Apply via STELCO Careers →",
        },
        {
            "id": "mwsc",
            "matches": ("mwsc", "water and sewerage", "male' water"),
            "name": "MWSC Careers",
            "portal": "mwsc.com.mv",
            "logo": "/static/logos/mwsc.svg",
            "url": "https://mwsc.com.mv/careers",
            "label": "Apply via MWSC Careers →",
        },
        {
            "id": "macl",
            "matches": ("macl", "airports company", "velana"),
            "name": "MACL Careers",
            "portal": "macl.aero",
            "logo": "/static/logos/macl.svg",
            "url": "https://macl.aero/careers",
            "label": "Apply via MACL Careers →",
        },
        {
            "id": "mira",
            "matches": ("mira", "revenue authority"),
            "name": "MIRA Careers",
            "portal": "mira.gov.mv",
            "logo": "/static/logos/mira.png",
            "url": "https://www.mira.gov.mv/jobs",
            "label": "Apply via MIRA Portal →",
        },
    ]

    matched_soe = None
    for soe in SOE_CONFIGS:
        if any(m in agency_lower for m in soe["matches"]) or (soe["portal"] in portal_lower):
            matched_soe = soe
            break

    is_hdc = matched_soe is not None and matched_soe["id"] == "hdc"
    j["is_hdc"] = is_hdc

    application_sources: list[dict[str, Any]] = []

    # Golden Rule: The link MUST come from the actual source holding the job vacancy details,
    # otherwise do NOT list the source.
    # 1. Employer Direct Portal has an actual specific vacancy post
    if matched_soe and (matched_soe["portal"] in direct_url or (matched_soe["id"] == "hdc" and not direct_url)):
        soe_url = direct_url if (direct_url and matched_soe["portal"] in direct_url) else matched_soe["url"]
        application_sources.append({
            "id": matched_soe["id"],
            "name": matched_soe["name"],
            "portal": matched_soe["portal"],
            "logo": matched_soe["logo"],
            "url": soe_url,
            "is_primary": True,
            "button_label": matched_soe["label"],
        })
    # 2. National Careers Service (mycareer.gov.mv) has the actual post
    elif "mycareer.gov.mv" in direct_url or portal_lower == "mycareer.gov.mv":
        application_sources.append({
            "id": "mycareer",
            "name": "MyCareer.mv",
            "portal": "mycareer.gov.mv",
            "logo": "/static/logos/mycareer.svg",
            "url": direct_url,
            "is_primary": True,
            "button_label": "Apply via MyCareer.mv →",
        })
    # 3. Government Gazette (gazette.gov.mv) has the actual post
    elif "gazette.gov.mv" in direct_url or portal_lower == "gazette.gov.mv" or (not direct_url and any(term in agency_lower for term in ("ministry", "school", "court", "council", "commission", "department", "authority", "service"))):
        gazette_url = direct_url if "gazette.gov.mv" in direct_url else f"https://gazette.gov.mv/iulaan/{notice_slug}"
        application_sources.append({
            "id": "gazette",
            "name": "Gazette.mv",
            "portal": "gazette.gov.mv",
            "logo": "/static/logos/gazette.svg",
            "url": gazette_url,
            "is_primary": True,
            "button_label": "Apply via Gazette.mv →",
        })
    # 4. Job-Maldives has the actual post
    elif "job-maldives" in portal_lower or "job-maldives" in direct_url or any(res in agency_lower for res in ("resort", "joali", "finolhu", "soneva", "villa")):
        jm_url = direct_url if ("job-maldives.com" in direct_url and len(direct_url) > 25) else f"https://job-maldives.com/posts/{notice_slug}/"
        application_sources.append({
            "id": "jobmaldives",
            "name": "Job-Maldives",
            "portal": "job-maldives.com",
            "logo": "/static/logos/jobmaldives.svg",
            "url": jm_url,
            "is_primary": True,
            "button_label": "Apply via Job-Maldives →",
        })
    elif direct_url:
        src_name = j.get("source_portal") or agency
        application_sources.append({
            "id": "direct",
            "name": src_name,
            "portal": j.get("source_portal") or "direct",
            "logo": j.get("employer_logo") or "/static/logos/gazette.svg",
            "url": direct_url,
            "is_primary": True,
            "button_label": f"Apply via {src_name} →",
        })

    j["application_sources"] = application_sources
    j["primary_source"] = application_sources[0] if application_sources else None
    j["secondary_source"] = application_sources[1] if len(application_sources) > 1 else None

    return j
