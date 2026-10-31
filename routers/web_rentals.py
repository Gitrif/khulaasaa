"""
Rentals & Tenancy Contract Web Router for Khulaasaa.
Consolidated Maldivian Apartment Listings & Hooks85 Tenancy Contract Management.
Strictly under 500 lines. Zero emojis.
"""
from __future__ import annotations
import logging
from typing import Optional
from fastapi import APIRouter, Request, status, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from core.deps import get_current_user, templates
from data.database import get_db, list_sponsored_ads
from data.repos.rentals import list_rentals, get_rental_by_id, save_rental_contract
from data.modules import is_service_module_enabled, get_service_module

logger = logging.getLogger(__name__)
router = APIRouter()

RENTAL_LOCATIONS = [
    "All Locations",
    "Male City",
    "Hulhumale Phase 1",
    "Hulhumale Phase 2",
    "Villimale",
]

@router.get("/rentals", response_class=HTMLResponse)
def rentals_directory_view(
    request: Request,
    location: Optional[str] = None,
    bedrooms: Optional[int] = None,
    max_rent: Optional[int] = None,
    furnished: Optional[str] = None,
    has_lift: Optional[int] = None,
    has_ac: Optional[int] = None,
    has_water_heater: Optional[int] = None,
    q: Optional[str] = None,
):
    """Consolidated Apartment & Rental directory across Male, Hulhumale, and atolls."""
    user = get_current_user(request)
    active_ads = []
    with get_db() as conn:
        if not is_service_module_enabled(conn, "rentals"):
            return templates.TemplateResponse(
                "service_suspended.html",
                {"request": request, "module": get_service_module(conn, "rentals"), "current_user": user},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        rentals_list = list_rentals(
            conn,
            location=location,
            bedrooms=bedrooms,
            max_rent=max_rent,
            furnished=furnished,
            has_lift=has_lift,
            has_ac=has_ac,
            has_water_heater=has_water_heater,
            search_q=q,
        )
        try:
            active_ads = [a for a in list_sponsored_ads(conn) if a.get("is_active") == 1]
        except Exception:
            pass

    return templates.TemplateResponse(
        "rentals.html",
        {
            "request": request,
            "rentals": rentals_list,
            "locations": RENTAL_LOCATIONS,
            "active_location": location or "All Locations",
            "active_bedrooms": bedrooms or 0,
            "active_max_rent": max_rent or 0,
            "active_furnished": furnished or "All",
            "active_lift": has_lift or 0,
            "active_ac": has_ac or 0,
            "active_water_heater": has_water_heater or 0,
            "search_query": q or "",
            "current_user": user,
            "active_ads": active_ads,
            "page_title": "Apartments & Rentals Consolidation | Khulaasaa Real Estate",
        },
    )


@router.get("/rentals/contract", response_class=HTMLResponse)
@router.get("/rentals/{rental_id}/contract", response_class=HTMLResponse)
def rental_contract_builder_view(request: Request, rental_id: Optional[int] = None):
    """Interactive Maldivian Tenancy Agreement & Lease Management Suite."""
    target_id = rental_id or request.query_params.get("rental_id")
    rental_item = None
    user = get_current_user(request)

    if target_id:
        try:
            with get_db() as conn:
                rental_item = get_rental_by_id(conn, int(target_id))
        except Exception:
            pass

    return templates.TemplateResponse(
        "rental_contract.html",
        {
            "request": request,
            "rental": rental_item,
            "current_user": user,
            "page_title": "Residential Tenancy Agreement & Rent Manager | Khulaasaa Rentals",
        },
    )


@router.get("/rentals/{rental_id}", response_class=HTMLResponse)
def rental_detail_view(request: Request, rental_id: int):
    """Detailed view of an aggregated rental listing with contact and contract CTA."""
    user = get_current_user(request)
    with get_db() as conn:
        if not is_service_module_enabled(conn, "rentals"):
            return templates.TemplateResponse(
                "service_suspended.html",
                {"request": request, "module": get_service_module(conn, "rentals"), "current_user": user},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        rental_item = get_rental_by_id(conn, rental_id)

    if not rental_item:
        return RedirectResponse(url="/rentals", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        "rental_detail.html",
        {
            "request": request,
            "rental": rental_item,
            "current_user": user,
            "page_title": f"{rental_item.get('title')} | Khulaasaa Rentals",
        },
    )


@router.post("/api/rentals/contract/save")
async def api_save_contract(request: Request):
    """Save tenancy agreement contract draft."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    user = get_current_user(request)
    if user:
        body["user_id"] = user["id"]

    with get_db() as conn:
        contract_id = save_rental_contract(conn, body)

    return {"status": "ok", "contract_id": contract_id, "message": "Contract saved successfully"}
