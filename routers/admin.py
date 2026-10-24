"""
Admin and Editor Console Router.
Handles cluster approvals, broadcast previews, sponsor ads, newsroom sources & logos,
and obituary notices.
"""
from __future__ import annotations

import os
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse

from core.deps import require_editor, templates
from data.database import (
    delete_obituary,
    delete_sponsored_ad,
    extend_sponsored_ad,
    get_db,
    get_sponsored_ad,
    list_obituaries,
    list_sponsored_ads,
    toggle_obituary,
    toggle_sponsored_ad,
    upsert_obituary,
    upsert_sponsored_ad,
)
from data.stories import (
    APPROVAL_LOG,
    PENDING_CLUSTERS,
    SOURCES,
    TIMELINE_TAGS,
    approve_cluster as process_approve_cluster,
)
from alerts.telegram import dispatch_sponsored_broadcast
from alerts.viber import dispatch_viber_sponsored_broadcast, set_viber_webhook

router = APIRouter()


@router.get("/admin", response_class=HTMLResponse)
def admin_console(request: Request, editor: str = Depends(require_editor)):
    clusters = []
    for c in PENDING_CLUSTERS:
        clusters.append(
            {
                **c,
                "source_objs": [SOURCES[s] for s in c["sources"] if s in SOURCES],
                "tag_objs": [TIMELINE_TAGS[t] for t in c["suggested_tags"] if t in TIMELINE_TAGS],
            }
        )
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "editor": editor,
            "clusters": clusters,
            "all_tags": list(TIMELINE_TAGS.values()),
            "approval_log": list(reversed(APPROVAL_LOG)),
        },
    )


@router.post("/admin/approve/{cluster_id}")
def approve_cluster(
    cluster_id: str,
    request: Request,
    tags: list[str] = Form(default=[]),
    editor: str = Depends(require_editor),
):
    match = next((c for c in PENDING_CLUSTERS if c["id"] == cluster_id), None)
    if not match:
        raise HTTPException(status_code=404, detail="Cluster not found or already approved")
    process_approve_cluster(cluster_id, tags)
    return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/admin/broadcast-preview/{cluster_id}", response_class=HTMLResponse)
def broadcast_preview(request: Request, cluster_id: str, editor: str = Depends(require_editor)):
    cluster = next((c for c in PENDING_CLUSTERS if c["id"] == cluster_id), None)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    cluster = {
        **cluster,
        "tag_objs": [TIMELINE_TAGS[t] for t in cluster["suggested_tags"] if t in TIMELINE_TAGS],
    }
    return templates.TemplateResponse(
        "broadcast_preview.html",
        {"request": request, "cluster": cluster},
    )


@router.get("/admin/ads", response_class=HTMLResponse)
def admin_ads(request: Request, msg: Optional[str] = None, editor: str = Depends(require_editor)):
    with get_db() as conn:
        ads = list_sponsored_ads(conn)
    return templates.TemplateResponse(
        "admin_ads.html",
        {
            "request": request,
            "editor": editor,
            "ads": ads,
            "message": msg,
        },
    )


@router.post("/admin/ads/create")
def admin_create_ad(
    sponsor_name: str = Form(...),
    campaign_name: str = Form(...),
    target_category: str = Form("all"),
    link_url: Optional[str] = Form(None),
    text_html: str = Form(...),
    is_active: Optional[int] = Form(0),
    max_impressions: Optional[int] = Form(None),
    duration_days: Optional[int] = Form(None),
    expires_date: Optional[str] = Form(None),
    pricing_tier: Optional[str] = Form("custom"),
    editor: str = Depends(require_editor),
):
    from datetime import datetime, timedelta

    calc_expires_at = None
    if duration_days and duration_days > 0:
        calc_expires_at = (datetime.now() + timedelta(days=duration_days)).strftime("%Y-%m-%d %H:%M:%S")
    elif expires_date and expires_date.strip():
        calc_expires_at = f"{expires_date.strip()} 23:59:59"

    with get_db() as conn:
        upsert_sponsored_ad(
            conn,
            {
                "sponsor_name": sponsor_name.strip(),
                "campaign_name": campaign_name.strip(),
                "target_category": target_category.strip(),
                "link_url": link_url.strip() if link_url else None,
                "text_html": text_html.strip(),
                "is_active": 1 if is_active else 0,
                "max_impressions": max_impressions if (max_impressions and max_impressions > 0) else None,
                "expires_at": calc_expires_at,
                "pricing_tier": pricing_tier or "custom",
            },
        )
    return RedirectResponse(
        url="/admin/ads?msg=" + urllib.parse.quote_plus(f"Campaign '{campaign_name}' saved successfully."),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/admin/ads/{ad_id}/extend")
def admin_extend_ad(
    ad_id: int,
    add_impressions: Optional[int] = Form(None),
    add_days: Optional[int] = Form(None),
    reset_impressions: Optional[int] = Form(0),
    editor: str = Depends(require_editor),
):
    with get_db() as conn:
        ok = extend_sponsored_ad(
            conn,
            ad_id,
            add_impressions=add_impressions if (add_impressions and add_impressions > 0) else None,
            add_days=add_days if (add_days and add_days > 0) else None,
            reset_impressions=bool(reset_impressions),
        )
    msg = "Campaign quota/duration extended successfully." if ok else "Could not extend campaign."
    return RedirectResponse(url="/admin/ads?msg=" + urllib.parse.quote_plus(msg), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/ads/{ad_id}/toggle")
def admin_toggle_ad(ad_id: int, editor: str = Depends(require_editor)):
    with get_db() as conn:
        toggle_sponsored_ad(conn, ad_id)
    return RedirectResponse(url="/admin/ads", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/ads/{ad_id}/broadcast")
def admin_broadcast_ad(ad_id: int, editor: str = Depends(require_editor)):
    with get_db() as conn:
        ad = get_sponsored_ad(conn, ad_id)
        if not ad:
            raise HTTPException(status_code=404, detail="Ad campaign not found")
        stats_tg = dispatch_sponsored_broadcast(
            conn,
            campaign_name=ad["campaign_name"],
            sponsor_name=ad["sponsor_name"],
            html_content=ad["text_html"],
            target_category=ad.get("target_category", "all"),
            link_url=ad.get("link_url"),
        )
        stats_viber = dispatch_viber_sponsored_broadcast(
            conn,
            campaign_name=ad["campaign_name"],
            sponsor_name=ad["sponsor_name"],
            html_content=ad["text_html"],
            target_category=ad.get("target_category", "all"),
            link_url=ad.get("link_url"),
        )
    tg_del = stats_tg.get("delivered", 0)
    vb_del = stats_viber.get("delivered", 0)
    total_del = tg_del + vb_del
    total_fail = stats_tg.get("failed", 0) + stats_viber.get("failed", 0)
    msg = f"Broadcast for '{ad['sponsor_name']}' completed across Telegram ({tg_del}) & Viber ({vb_del}). Total: {total_del} delivered, {total_fail} failed."
    return RedirectResponse(url="/admin/ads?msg=" + urllib.parse.quote_plus(msg), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/ads/{ad_id}/delete")
def admin_delete_ad(ad_id: int, editor: str = Depends(require_editor)):
    with get_db() as conn:
        delete_sponsored_ad(conn, ad_id)
    return RedirectResponse(url="/admin/ads?msg=Campaign+deleted", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/admin/sources", response_class=HTMLResponse)
def admin_sources(request: Request, msg: Optional[str] = None, editor: str = Depends(require_editor)):
    sources_list = []
    active_count = 0
    missing_count = 0
    logos_dir = Path("static/logos")

    for s_id, s_data in SOURCES.items():
        logo_rel = s_data.get("logo", f"/static/logos/{s_id}.png")
        logo_filename = logo_rel.lstrip("/").replace("static/logos/", "")
        logo_path = logos_dir / logo_filename
        has_logo = logo_path.exists() and logo_path.stat().st_size > 0

        if has_logo:
            active_count += 1
        else:
            missing_count += 1

        sources_list.append({
            **s_data,
            "has_logo": has_logo,
            "logo": logo_rel,
        })

    return templates.TemplateResponse(
        "admin_sources.html",
        {
            "request": request,
            "editor": editor,
            "sources": sources_list,
            "active_count": active_count,
            "missing_count": missing_count,
            "message": msg,
        },
    )


@router.post("/admin/sources/{source_id}/upload-logo")
async def admin_upload_source_logo(
    source_id: str,
    logo_file: UploadFile = File(...),
    editor: str = Depends(require_editor),
):
    if source_id not in SOURCES:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found")

    ext = Path(logo_file.filename or "logo.png").suffix.lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico"]:
        ext = ".png"

    logos_dir = Path("static/logos")
    logos_dir.mkdir(parents=True, exist_ok=True)
    target_file = logos_dir / f"{source_id}{ext}"

    content = await logo_file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    target_file.write_bytes(content)
    SOURCES[source_id]["logo"] = f"/static/logos/{source_id}{ext}"

    return RedirectResponse(
        url="/admin/sources?msg=" + urllib.parse.quote_plus(f"Logo for '{SOURCES[source_id]['name']}' updated successfully!"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/admin/sources/create")
async def admin_create_source(
    source_id: str = Form(...),
    name: str = Form(...),
    domain: str = Form(...),
    kind: str = Form("press"),
    logo_file: Optional[UploadFile] = File(None),
    editor: str = Depends(require_editor),
):
    import re
    s_id = re.sub(r"[^a-z0-9_-]", "", source_id.lower().strip())
    if not s_id:
        raise HTTPException(status_code=400, detail="Invalid source ID")

    logo_path = f"/static/logos/{s_id}.png"
    if logo_file and logo_file.filename:
        ext = Path(logo_file.filename).suffix.lower()
        if ext not in [".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico"]:
            ext = ".png"
        content = await logo_file.read()
        if content:
            logos_dir = Path("static/logos")
            logos_dir.mkdir(parents=True, exist_ok=True)
            (logos_dir / f"{s_id}{ext}").write_bytes(content)
            logo_path = f"/static/logos/{s_id}{ext}"

    SOURCES[s_id] = {
        "id": s_id,
        "name": name.strip(),
        "initial": (name.strip()[:1] or "S").upper(),
        "kind": kind.strip(),
        "domain": domain.strip().replace("https://", "").replace("http://", "").rstrip("/"),
        "logo": logo_path,
    }

    return RedirectResponse(
        url="/admin/sources?msg=" + urllib.parse.quote_plus(f"Source '{name}' added successfully!"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/admin/obituaries", response_class=HTMLResponse)
def admin_obituaries(request: Request, msg: Optional[str] = None, editor: str = Depends(require_editor)):
    with get_db() as conn:
        obs = list_obituaries(conn, limit=100, active_only=False)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return templates.TemplateResponse(
        "admin_obituaries.html",
        {
            "request": request,
            "editor": editor,
            "obituaries": obs,
            "message": msg,
            "today_date": today_str,
        },
    )


@router.post("/admin/obituaries/create")
async def admin_create_obituary(
    name_dv: str = Form(...),
    name_en: Optional[str] = Form(None),
    address_dv: Optional[str] = Form(None),
    address_en: Optional[str] = Form(None),
    age: Optional[int] = Form(None),
    funeral_mosque_dv: str = Form(...),
    funeral_mosque_en: Optional[str] = Form(None),
    prayer_time_dv: str = Form(...),
    prayer_time_en: Optional[str] = Form(None),
    funeral_date: Optional[str] = Form(None),
    contact_numbers: Optional[str] = Form(None),
    photo_file: Optional[UploadFile] = File(None),
    editor: str = Depends(require_editor),
):
    import re
    slug_base = re.sub(r"[^\w-]", "", (name_en or name_dv or "obituary").lower().replace(" ", "-"))[:40]
    slug = f"{slug_base}-{abs(hash(name_dv + str(funeral_date))) % 100000}"

    photo_url = None
    if photo_file and photo_file.filename:
        ext = Path(photo_file.filename).suffix.lower()
        if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
            ext = ".png"
        content = await photo_file.read()
        if content:
            ob_dir = Path("static/obituaries")
            ob_dir.mkdir(parents=True, exist_ok=True)
            photo_filename = f"{slug}{ext}"
            (ob_dir / photo_filename).write_bytes(content)
            photo_url = f"/static/obituaries/{photo_filename}"

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ob_data = {
        "slug": slug,
        "name_dv": name_dv.strip(),
        "name_en": name_en.strip() if name_en else None,
        "address_dv": address_dv.strip() if address_dv else None,
        "address_en": address_en.strip() if address_en else None,
        "age": age,
        "funeral_mosque_dv": funeral_mosque_dv.strip(),
        "funeral_mosque_en": funeral_mosque_en.strip() if funeral_mosque_en else None,
        "prayer_time_dv": prayer_time_dv.strip(),
        "prayer_time_en": prayer_time_en.strip() if prayer_time_en else None,
        "funeral_date": funeral_date or today_str,
        "death_date": today_str,
        "photo_url": photo_url,
        "contact_numbers": contact_numbers.strip() if contact_numbers else None,
        "source_channel": "Editorial",
        "announcement_type": "Janaza",
        "is_active": 1,
    }

    with get_db() as conn:
        upsert_obituary(conn, ob_data)

    return RedirectResponse(
        url="/admin/obituaries?msg=" + urllib.parse.quote_plus(f"Obituary notice for '{name_dv}' published successfully!"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/admin/obituaries/{ob_id}/toggle")
def admin_toggle_obituary(ob_id: int, editor: str = Depends(require_editor)):
    with get_db() as conn:
        toggle_obituary(conn, ob_id)
    return RedirectResponse(url="/admin/obituaries?msg=Status+updated", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/obituaries/{ob_id}/delete")
def admin_delete_obituary(ob_id: int, editor: str = Depends(require_editor)):
    with get_db() as conn:
        delete_obituary(conn, ob_id)
    return RedirectResponse(url="/admin/obituaries?msg=Notice+deleted", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/obituaries/quick-import")
async def admin_quick_import_obituary(
    post_text: str = Form(...),
    photo_file: Optional[UploadFile] = File(None),
    editor: str = Depends(require_editor),
):
    from scrapers.facebook import import_kashunamaadhu_text
    photo_url = None
    if photo_file and photo_file.filename:
        ext = Path(photo_file.filename).suffix.lower()
        if ext not in [".png", ".jpg", ".jpeg", ".webp"]:
            ext = ".png"
        content = await photo_file.read()
        if content:
            ob_dir = Path("static/obituaries")
            ob_dir.mkdir(parents=True, exist_ok=True)
            photo_filename = f"fb-{abs(hash(post_text[:60]))}{ext}"
            (ob_dir / photo_filename).write_bytes(content)
            photo_url = f"/static/obituaries/{photo_filename}"

    res = import_kashunamaadhu_text(post_text, photo_url=photo_url)
    name = res.get("data", {}).get("name_dv", "Notice")
    return RedirectResponse(
        url="/admin/obituaries?msg=" + urllib.parse.quote_plus(f"Imported Kashunamaadhu notice for '{name}' successfully!"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/admin/viber/set-webhook")
def admin_set_viber_webhook(
    webhook_url: str = Form(...),
    editor: str = Depends(require_editor),
):
    res = set_viber_webhook(webhook_url)
    msg = (
        "Viber webhook configured successfully!"
        if res.get("status") == 0
        else f"Viber webhook error: {res.get('status_message')}"
    )
    return RedirectResponse(
        url="/admin/sources?msg=" + urllib.parse.quote_plus(msg),
        status_code=status.HTTP_303_SEE_OTHER,
    )
