"""
Enterprise Resource Planning (ERP) & RFQ Gateway API.

Treats government and SOE procurement notices as enterprise Requests For Quotation (RFQs).
Enables seamless ingestion into systems like Odoo, ERPNext, SAP, and custom procurement pipelines.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from data.database import get_db, query_bids

router = APIRouter(prefix="/api/v1/erp", tags=["ERP / RFQ Integration"])


# --- ERP Data Transformers ----------------------------------------------------

def _parse_iso_or_none(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        # Normalize simple formats
        clean = date_str.replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except Exception:
        return None


def _calculate_rfq_status(deadline_str: Optional[str], is_active: int) -> str:
    if not is_active:
        return "CLOSED"
    if not deadline_str:
        return "OPEN"
    
    dt = _parse_iso_or_none(deadline_str)
    if not dt:
        return "OPEN"
    
    # Ensure timezone aware comparison
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    diff = (dt - now).total_seconds()
    if diff < 0:
        return "CLOSED"
    elif diff <= 172800:  # 48 hours
        return "CLOSING_SOON"
    return "OPEN"


def transform_bid_to_rfq(bid: Any, erp_format: str = "standard") -> dict[str, Any]:
    """Transform an internal tender bid into an Enterprise RFQ representation."""
    b = dict(bid) if hasattr(bid, "keys") else (bid or {})
    doc_urls = b.get("document_urls") or []
    if isinstance(doc_urls, str):
        try:
            doc_urls = json.loads(doc_urls)
        except Exception:
            doc_urls = []

    portals = b.get("sources") or ["gazette.gov.mv"]
    if isinstance(portals, str):
        try:
            portals = json.loads(portals)
        except Exception:
            portals = ["gazette.gov.mv"]

    notice_id = str(b.get("notice_id") or b.get("id"))
    status = _calculate_rfq_status(b.get("submission_date"), b.get("is_active", 1))

    # Standard Procurement Model (OCDS / OpenAPI compatible)
    rfq = {
        "rfq_id": f"RFQ-{notice_id}",
        "external_id": notice_id,
        "reference_number": b.get("reference_number"),
        "title": b.get("title_en") or b.get("title"),
        "title_dv": b.get("title"),
        "opportunity_type": b.get("procurement_nature") or "Supply",
        "trade_category": b.get("discipline") or "Other",
        "status": status,
        "buyer": {
            "name": b.get("agency_name_en") or "Government of Maldives",
            "name_dv": b.get("agency_name_dv"),
            "category": b.get("entity_type") or "Other",
            "slug": b.get("entity_slug"),
            "location": b.get("entity_location") or "Male'",
            "portal_url": b.get("entity_website"),
        },
        "dates": {
            "published_at": b.get("published_date"),
            "closing_deadline": b.get("submission_date"),
            "clarification_deadline": b.get("info_date"),
        },
        "logistics": {
            "submission_venue": b.get("submission_location") or "Agency Office / National Tender Portal",
            "pre_bid_conference": b.get("info_location"),
            "publishing_portals": portals,
        },
        "documents": [
            {
                "url": url,
                "name": url.split("/")[-1] if "/" in url else "Tender Document",
            }
            for url in doc_urls
        ],
        "source_url": b.get("source_url"),
    }

    # Format specialized for Odoo Purchase / Sourcing modules
    if erp_format == "odoo":
        return {
            "name": f"RFQ/{b.get('reference_number') or notice_id}",
            "partner_id": {"name": b.get("agency_name_en"), "ref": b.get("entity_slug")},
            "date_order": b.get("published_date"),
            "date_planned": b.get("submission_date"),
            "origin": f"Khulaasaa Tender #{notice_id}",
            "state": "draft" if status in ["OPEN", "CLOSING_SOON"] else "cancel",
            "notes": f"Procurement Nature: {b.get('procurement_nature')}\nSubmission Venue: {b.get('submission_location')}\nInfo Session: {b.get('info_date')} at {b.get('info_location')}\nSource: {b.get('source_url')}",
            "opportunity_title": rfq["title"],
            "trade_category": rfq["trade_category"],
        }

    # Format specialized for ERPNext 'Request for Quotation' DocType
    if erp_format == "erpnext":
        return {
            "doctype": "Request for Quotation",
            "transaction_date": (b.get("published_date") or "")[:10],
            "valid_till": (b.get("submission_date") or "")[:10],
            "supplier": b.get("agency_name_en"),
            "naming_series": "RFQ-.YYYY.-",
            "status": "Submitted" if status == "OPEN" else "Closed",
            "instructions": f"Ref: {b.get('reference_number')}\nSubmission: {b.get('submission_location')}\nDocuments: {', '.join(doc_urls)}",
            "custom_source_url": b.get("source_url"),
            "custom_discipline": b.get("discipline"),
            "title": rfq["title"],
        }

    return rfq



# --- API Routes ---------------------------------------------------------------

@router.get("/rfqs", summary="List enterprise RFQs with multi-criteria filtering")
def list_rfqs(
    discipline: Optional[str] = Query(None, description="Trade category (e.g. Construction, IT & Telecommunications, Power & Electrical)"),
    nature: Optional[str] = Query(None, description="Procurement nature: Supply, Service, Works"),
    buyer_slug: Optional[str] = Query(None, description="Buyer entity slug (e.g. housing-development-corporation)"),
    status: Optional[str] = Query("open", description="Status filter: 'open' (active future deadline), 'closing_soon' (within 48h), or 'all'"),
    q: Optional[str] = Query(None, description="Search keyword in title, reference, or agency"),
    format: str = Query("standard", description="Payload structure: 'standard', 'odoo', or 'erpnext'"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
) -> dict[str, Any]:
    """
    Search and retrieve public procurement notices formatted as Enterprise RFQs.
    Enables ERP automated quotation pipelines and supplier notifications.
    """
    offset = (page - 1) * limit
    
    # Query database
    open_only = status in ["open", "closing_soon"]
    with get_db() as conn:
        all_matches = query_bids(
            conn,
            discipline=discipline,
            procurement_nature=nature,
            entity_slug=buyer_slug,
            search_q=q,
            open_only=open_only,
            limit=limit * 3,
        )

    # In-memory refinement for nature and computed status
    filtered = []
    for b in all_matches:
        computed_status = _calculate_rfq_status(b.get("submission_date"), b.get("is_active", 1))

        # Filter by calculated RFQ status
        if status == "closing_soon":
            if computed_status != "CLOSING_SOON":
                continue
        elif status == "open":
            if computed_status not in ["OPEN", "CLOSING_SOON"]:
                continue

        rfq = transform_bid_to_rfq(b, erp_format=format)
        filtered.append(rfq)
        if len(filtered) >= limit:
            break

    return {
        "meta": {
            "page": page,
            "limit": limit,
            "count": len(filtered),
            "format": format,
            "filters": {
                "discipline": discipline,
                "nature": nature,
                "buyer_slug": buyer_slug,
                "status": status,
                "query": q,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "data": filtered,
    }


@router.get("/rfqs/{notice_id}", summary="Get detailed RFQ specification by notice ID")
def get_rfq_detail(
    notice_id: str,
    format: str = Query("standard", description="Payload structure: 'standard', 'odoo', or 'erpnext'"),
) -> dict[str, Any]:
    """Retrieve full procurement specifications and attachments for an individual RFQ."""
    clean_id = notice_id.replace("RFQ-", "").strip()
    with get_db() as conn:
        cur = conn.execute(
            "SELECT * FROM v_bids_enriched WHERE notice_id = ? OR reference_number = ? LIMIT 1;",
            (clean_id, clean_id),
        )
        matched = cur.fetchone()
        if not matched:
            bids = query_bids(conn, search_q=clean_id, limit=5)
            matched = next(
                (b for b in bids if str(b.get("notice_id")) == clean_id or b.get("reference_number") == clean_id),
                None,
            )

    if not matched:
        raise HTTPException(status_code=404, detail=f"RFQ notice '{notice_id}' not found.")

    return {
        "status": "success",
        "data": transform_bid_to_rfq(matched, erp_format=format),
    }


class WebhookTestRequest(BaseModel):
    webhook_url: str = Field(..., description="Target ERP webhook URL to receive simulated RFQ payload")
    event_type: str = Field("rfq.published", description="Event name: 'rfq.published', 'rfq.deadline_approaching'")
    notice_id: Optional[str] = Field(None, description="Specific notice ID to simulate payload for")


@router.post("/webhooks/simulate", summary="Test dispatching a simulated RFQ event payload to an ERP webhook")
def simulate_webhook_dispatch(req: WebhookTestRequest) -> dict[str, Any]:
    """
    Simulates sending an event payload to an external ERP endpoint.
    Useful for testing Odoo, ERPNext, Make.com, or Zapier webhooks.
    """
    import httpx

    sample = None
    with get_db() as conn:
        if req.notice_id:
            clean_id = req.notice_id.replace("RFQ-", "").strip()
            cur = conn.execute(
                "SELECT * FROM v_bids_enriched WHERE notice_id = ? OR reference_number = ? LIMIT 1;",
                (clean_id, clean_id),
            )
            sample = cur.fetchone()
        if not sample:
            cur = conn.execute("SELECT * FROM v_bids_enriched WHERE is_active = 1 LIMIT 1;")
            sample = cur.fetchone()



    if not sample:
        # Fallback dummy sample
        rfq_payload = {
            "rfq_id": "RFQ-SIMULATED-417569",
            "reference_number": "MWSC-L/3/ADV/2026/95",
            "title": "Supply and Delivery of High-Density Polyethylene Fittings",
            "opportunity_type": "Supply",
            "trade_category": "Construction",
            "status": "OPEN",
            "buyer": {"name": "Male' Water and Sewerage Company Pvt Ltd"},
            "dates": {
                "published_at": "2026-10-15T10:00:00",
                "closing_deadline": "2026-10-25T14:00:00",
            },
        }
    else:
        rfq_payload = transform_bid_to_rfq(sample, erp_format="standard")

    event_payload = {
        "event": req.event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "Khulaasaa Procurement Intelligence Gateway",
        "rfq": rfq_payload,
    }

    # Attempt test HTTP POST
    try:
        resp = httpx.post(req.webhook_url, json=event_payload, timeout=10.0)
        return {
            "status": "success",
            "webhook_status_code": resp.status_code,
            "message": f"Successfully dispatched simulated event to {req.webhook_url}",
            "dispatched_payload": event_payload,
        }

    except Exception as exc:
        return {
            "status": "error",
            "message": f"Failed to deliver payload to {req.webhook_url}: {str(exc)}",
            "dispatched_payload": event_payload,
        }
