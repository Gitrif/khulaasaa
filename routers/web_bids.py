"""
Tenders, Procurement Workspace, Company Profile, and Construction Estimator Web UI Router.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from core.deps import get_current_user, is_authorized_editor, templates
from data.database import (
    get_agency_portal_statistics,
    get_bids_filter_options,
    get_company_profile,
    get_db,
    list_sponsored_ads,
    query_bids,
)
from alerts.telegram import get_telegram_credentials
from services.estimator_service import calculate_full_boq
from services.tenders_service import trigger_bids_background_sync, prepare_bids_presentation
from data.modules import is_service_module_enabled, get_service_module

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/bids", response_class=HTMLResponse)
def bids(
    request: Request,
    agency: Optional[str] = None,
    discipline: Optional[str] = None,
    nature: Optional[str] = None,
    type: Optional[str] = None,
    entity_type: Optional[str] = None,
    q: Optional[str] = None,
    lang: Optional[str] = "en",
    portal: Optional[str] = None,
    cross_listed: Optional[str] = None,
    unlocked: Optional[str] = None,
    source: Optional[str] = "live",
    refresh: Optional[str] = None,
):
    use_live = (source != 'mock')
    if refresh == '1':
        if is_authorized_editor(request):
            trigger_bids_background_sync(force=True)
        else:
            logger.info('Ignoring unauthorized manual refresh on /bids')

    # Multi-select query parameter parsing
    qp = request.query_params
    selected_agencies = qp.getlist("agency") if hasattr(qp, "getlist") else []
    if not selected_agencies and agency:
        selected_agencies = [agency]
    selected_disciplines = qp.getlist("discipline") if hasattr(qp, "getlist") else []
    if not selected_disciplines and discipline:
        selected_disciplines = [discipline]
    selected_natures = qp.getlist("nature") if hasattr(qp, "getlist") else []
    if not selected_natures and nature:
        selected_natures = [nature]
    selected_types = qp.getlist("type") if hasattr(qp, "getlist") else []
    if not selected_types and type:
        selected_types = [type]
    selected_entity_types = qp.getlist("entity_type") if hasattr(qp, "getlist") else []
    if not selected_entity_types and entity_type:
        selected_entity_types = [entity_type]
    selected_portals = qp.getlist("portal") if hasattr(qp, "getlist") else []
    if not selected_portals and portal:
        selected_portals = [portal]

    with get_db() as conn:
        if not is_service_module_enabled(conn, 'tenders'):
            return templates.TemplateResponse(
                'service_suspended.html',
                {'request': request, 'module': get_service_module(conn, 'tenders'), 'current_user': get_current_user(request)},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    import json
    bids_cache_key = f"bids:feed:{sorted(selected_agencies)}:{sorted(selected_entity_types)}:{sorted(selected_disciplines)}:{sorted(selected_natures)}:{sorted(selected_types)}:{sorted(selected_portals)}:{cross_listed}:{q or ''}"
    cached_bids_payload = None
    try:
        from services.cache_service import cache_get
        cached_bids_payload = cache_get(bids_cache_key)
    except Exception:
        pass

    if cached_bids_payload is not None:
        rows = cached_bids_payload["rows"]
        filter_options = cached_bids_payload["filter_options"]
        stats = cached_bids_payload["stats"]
        active_ads = cached_bids_payload["active_ads"]
    else:
        with get_db() as conn:
            rows = query_bids(
                conn,
                agency_name=selected_agencies if selected_agencies else None,
                entity_type=selected_entity_types if selected_entity_types else None,
                discipline=selected_disciplines if selected_disciplines else None,
                procurement_nature=selected_natures if selected_natures else None,
                gazette_type=selected_types if selected_types else None,
                portal=selected_portals if selected_portals else None,
                cross_listed_only=(cross_listed == "1"),
                search_q=q,
            )
            filter_options = get_bids_filter_options(conn)
            stats = get_agency_portal_statistics(conn)
            active_ads = [a for a in list_sponsored_ads(conn) if a.get("is_active") == 1]
        try:
            from services.cache_service import cache_set
            cache_set(bids_cache_key, {
                "rows": rows,
                "filter_options": filter_options,
                "stats": stats,
                "active_ads": active_ads,
            }, ttl_seconds=60)
        except Exception:
            pass

    rows = prepare_bids_presentation(rows)

    default_token, default_chat = get_telegram_credentials()

    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.query_params.get("partial") == "1":
        return templates.TemplateResponse(
            "components/bids_stream.html",
            {
                "request": request,
                "bids": rows,
                "lang_mode": lang or "en",
            },
        )

    all_agencies = filter_options["agencies"]
    top_agencies = [a for a in [
        "Ministry of Tourism",
        "Male' Water and Sewerage Company Pvt Ltd",
        "Housing Development Corporation",
        "State Trading Organization Plc",
        "Secretariat of the Sh. Goidhoo Council",
        "Ministry of Islamic Affairs and Endowments",
        "Ministry of Education",
    ] if a in all_agencies]
    if not top_agencies:
        top_agencies = all_agencies[:7]

    active_ag = selected_agencies[0] if len(selected_agencies) == 1 else None
    active_disc = selected_disciplines[0] if len(selected_disciplines) == 1 else None
    active_nat = selected_natures[0] if len(selected_natures) == 1 else None
    active_tp = selected_types[0] if len(selected_types) == 1 else None
    active_et = selected_entity_types[0] if len(selected_entity_types) == 1 else None
    active_pt = selected_portals[0] if len(selected_portals) == 1 else None

    return templates.TemplateResponse(
        "bids.html",
        {
            "request": request,
            "bids": rows,
            "is_unlocked": True,
            "active_ads": active_ads,
            "is_live": use_live,
            "agencies": all_agencies,
            "top_agencies": top_agencies,
            "disciplines": filter_options["disciplines"],
            "quick_disciplines": ["Construction", "IT", "Medical", "Real Estate & Leasing", "Other"],
            "natures": ["Supply", "Service", "Lease"],
            "types": filter_options["types"],
            "entity_types": ["SOE", "Ministry", "Council", "Healthcare", "Education", "Independent", "Other"],
            "portals": ["gazette.gov.mv", "finance.gov.mv", "tourism.gov.mv", "mwsc.com.mv", "stelco.com.mv", "sto.mv"],
            "active_agency": active_ag,
            "active_discipline": active_disc,
            "active_nature": active_nat,
            "active_type": active_tp,
            "active_entity_type": active_et,
            "active_portal": active_pt,
            "selected_agencies": selected_agencies,
            "selected_disciplines": selected_disciplines,
            "selected_natures": selected_natures,
            "selected_types": selected_types,
            "selected_entity_types": selected_entity_types,
            "selected_portals": selected_portals,
            "cross_listed": cross_listed == "1",
            "agency_stats": stats,
            "search_q": q or "",
            "lang_mode": lang or "en",
            "source": source or "live",
            "has_telegram_creds": bool(default_token and default_chat),
            "default_chat_id": default_chat,
        },
    )


@router.get("/bids/company-profile", response_class=HTMLResponse)
@router.get("/company-profile", response_class=HTMLResponse)
def company_profile_view(request: Request):
    """Corporate Company Profile Builder."""
    user = get_current_user(request)
    profile = None
    with get_db() as conn:
        if user:
            profile = get_company_profile(conn, user_id=user["id"])
        if not profile:
            profile = get_company_profile(conn)

    return templates.TemplateResponse(
        "company_profile.html",
        {
            "request": request,
            "current_user": user,
            "profile": profile,
            "page_title": "Corporate Company Profile Builder | Khulaasaa Bids",
        },
    )


@router.get("/bids/prepare", response_class=HTMLResponse)
@router.get("/bids/{notice_id}/prepare", response_class=HTMLResponse)
def bid_prepare_workspace(request: Request, notice_id: Optional[str] = None):
    """Bidder Correspondence, Profile, Proposal & Business Suite for a selected bid."""
    target_id = notice_id or request.query_params.get("notice_id") or request.query_params.get("id")
    if not target_id:
        return RedirectResponse(url="/bids", status_code=status.HTTP_303_SEE_OTHER)

    user = get_current_user(request)
    with get_db() as conn:
        cur = conn.execute(
            """
            SELECT * FROM v_bids_enriched 
            WHERE notice_id = ? OR CAST(id AS TEXT) = ? OR reference_number = ? 
            LIMIT 1;
            """,
            (str(target_id), str(target_id), str(target_id)),
        )
        row = cur.fetchone()
        if not row:
            matches = query_bids(conn, search_q=str(target_id), limit=1)
            row = matches[0] if matches else None

        profile = None
        if user:
            profile = get_company_profile(conn, user_id=user["id"])
        if not profile:
            profile = get_company_profile(conn)

    if not row:
        raise HTTPException(status_code=404, detail="Selected tender notice not found.")

    bid_data = dict(row)
    try:
        bid_data["document_urls"] = json.loads(bid_data["document_urls"]) if bid_data.get("document_urls") else []
    except Exception:
        bid_data["document_urls"] = []
    try:
        bid_data["sources"] = json.loads(bid_data["sources"]) if bid_data.get("sources") else ["gazette.gov.mv"]
    except Exception:
        bid_data["sources"] = ["gazette.gov.mv"]

    agency_email = None
    if bid_data.get("info_location"):
        m_email = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", str(bid_data["info_location"]))
        if m_email:
            agency_email = m_email.group(0)

    return templates.TemplateResponse(
        "bid_workspace.html",
        {
            "request": request,
            "bid": bid_data,
            "agency_email": agency_email,
            "current_user": user,
            "profile": profile,
            "page_title": f"Bid Package — {bid_data.get('reference_number') or bid_data.get('title')}",
        },
    )


@router.get("/calculator", response_class=HTMLResponse)
@router.get("/tools/construction-estimator", response_class=HTMLResponse)
def construction_estimator_view(request: Request):
    """Free Tier Construction Cost & Material Estimator."""
    user = get_current_user(request)
    profile = None
    active_ads = []
    with get_db() as conn:
        if user:
            profile = get_company_profile(conn, user_id=user["id"])
        if not profile:
            profile = get_company_profile(conn)
        try:
            active_ads = [a for a in list_sponsored_ads(conn) if a.get("is_active") == 1]
        except Exception:
            pass

    return templates.TemplateResponse(
        "construction_estimator.html",
        {
            "request": request,
            "current_user": user,
            "profile": profile,
            "active_ads": active_ads,
            "initial_boq": calculate_full_boq({}),
            "page_title": "Construction Cost Estimator & Material Calculator | Khulaasaa",
        },
    )


@router.post("/api/bids/estimate-boq", response_class=JSONResponse)
@router.post("/api/tools/construction-estimator", response_class=JSONResponse)
async def api_calculate_construction_boq(request: Request):
    """Calculate Maldivian construction material quantities and MVR BOQ cost."""
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    return JSONResponse(calculate_full_boq(payload))
