"""
Sponsored Ads and Commercial Broadcasts API Router.
"""
from __future__ import annotations

import time
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from core.deps import require_editor, templates
from data.database import get_db, list_sponsored_ads, upsert_sponsored_ad
from alerts.telegram import dispatch_sponsored_broadcast
from alerts.viber import dispatch_viber_sponsored_broadcast

router = APIRouter()


@router.get("/advertise", response_class=HTMLResponse)
def advertise_page(request: Request):
    """Advertise with Khulaasaa - Media kit, ad formats, and booking."""
    return templates.TemplateResponse("advertise.html", {"request": request})


@router.get("/api/ads")
def api_list_ads():
    """List configured sponsor ad campaigns and delivered impression stats."""
    with get_db() as conn:
        return list_sponsored_ads(conn)


@router.post("/api/ads")
async def api_create_ad(request: Request, _: str = Depends(require_editor)):
    """Register or update a sponsor campaign (authenticated editor only)."""
    payload = await request.json()
    with get_db() as conn:
        ad_id = upsert_sponsored_ad(conn, payload)
    return {"ok": True, "ad_id": ad_id}


@router.post("/api/alerts/telegram/broadcast-ad")
async def api_broadcast_sponsored_ad(request: Request, _: str = Depends(require_editor)):
    """Broadcast a dedicated sponsored message or partner offer to subscribers (authenticated editor only)."""
    payload = await request.json()
    campaign_name = payload.get("campaign_name") or f"broadcast-{int(time.time())}"
    sponsor_name = payload.get("sponsor_name", "Khulaasaa Commercial Partner")
    text_html = payload.get("text_html")
    target_category = payload.get("target_category", "all")
    link_url = payload.get("link_url")

    if not text_html:
        raise HTTPException(status_code=400, detail="Missing text_html content for sponsored broadcast")

    with get_db() as conn:
        stats_tg = dispatch_sponsored_broadcast(
            conn,
            campaign_name=campaign_name,
            sponsor_name=sponsor_name,
            html_content=text_html,
            target_category=target_category,
            link_url=link_url,
        )
        stats_viber = dispatch_viber_sponsored_broadcast(
            conn,
            campaign_name=campaign_name,
            sponsor_name=sponsor_name,
            html_content=text_html,
            target_category=target_category,
            link_url=link_url,
        )
    combined = {
        "telegram": stats_tg,
        "viber": stats_viber,
        "delivered": stats_tg.get("delivered", 0) + stats_viber.get("delivered", 0),
        "failed": stats_tg.get("failed", 0) + stats_viber.get("failed", 0),
    }
    return {"ok": True, "stats": combined}
