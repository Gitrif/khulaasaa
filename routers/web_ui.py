"""
Public Web UI Router.
Renders Jinja2 HTML templates for the home feed, story detail, timelines,
collections, tenders/bids, jobs, obituaries, and CV creator.
"""
from __future__ import annotations

import html
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from core.deps import get_current_user, templates
from data.database import (
    ATOLL_TAXONOMY,
    get_agency_portal_statistics,
    get_bids_filter_options,
    get_company_profile,
    get_db,
    get_job_disciplines,
    get_telegram_subscriber,
    get_user_cv,
    list_obituaries,
    list_sponsored_ads,
    save_hooks85_subscription,
    query_bids,
    query_jobs,
)
from data.stories import (
    DEFAULT_EVENTS,
    JOBS,
    SOURCES,
    TIMELINE_TAGS,
    TIMELINES,
    TOPICS,
    TRENDING,
)
from scrapers.jobs import JOB_DISCIPLINES
from scrapers.translator import is_dhivehi, translate_dhivehi_title
from services.news_service import enrich_event, get_live_news
from services.jobs_service import enrich_job
from services.tenders_service import trigger_bids_background_sync
from alerts.telegram import get_telegram_credentials

from routers.web_bids import router as web_bids_router
from routers.web_jobs import router as web_jobs_router

router = APIRouter()
router.include_router(web_bids_router)
router.include_router(web_jobs_router)


@router.get("/", response_class=HTMLResponse)
@router.get("/app", response_class=HTMLResponse)
def public_feed(
    request: Request,
    tag: Optional[str] = None,
    topic: Optional[str] = None,
    source: Optional[str] = "live",
    refresh: Optional[str] = None,
    sort: Optional[str] = "latest",
):
    """Aggregate public news feed."""
    use_live = (source != "mock")
    raw_events = [enrich_event(e) for e in get_live_news(force_refresh=(refresh == "1"))] if use_live else [enrich_event(e) for e in DEFAULT_EVENTS]
    if not raw_events and use_live:
        raw_events = [enrich_event(e) for e in DEFAULT_EVENTS]
    events = raw_events

    # Collect tags that actually have matching stories or milestones
    active_tag_ids = set()
    for e in (raw_events if not topic else [x for x in raw_events if x.get("topic") == topic]):
        for t in e.get("tags", []):
            active_tag_ids.add(t)
    for tl in TIMELINES.values():
        if tl.get("tag") and tl.get("milestones"):
            active_tag_ids.add(tl["tag"])
    if tag:
        active_tag_ids.add(tag)

    visible_tags = [t for t in TIMELINE_TAGS.values() if t["id"] in active_tag_ids]

    # Filter by topic and tag if selected
    if topic:
        events = [e for e in events if e.get("topic") == topic]
    if tag:
        tag_filtered = [e for e in events if tag in e.get("tags", [])]
        if not tag_filtered:
            # Fallback to timeline milestones matching this tag so users never see an empty screen
            for tl in TIMELINES.values():
                if tl.get("tag") == tag:
                    for m in tl.get("milestones", []):
                        tag_filtered.append(enrich_event({
                            **m,
                            "tags": [tag],
                            "section": "general",
                            "topic": "infrastructure",
                            "published_raw": m.get("date_raw"),
                            "published_iso": m.get("date_iso"),
                            "summary": m.get("detail", ""),
                        }))
        events = tag_filtered

    # Sort if requested
    if sort == "outlets":
        events.sort(key=lambda x: len(x.get("source_objs", [])), reverse=True)
    elif sort == "urgent":
        events.sort(key=lambda x: 0 if x.get("section") == "breaking" else 1)

    breaking_list = [e for e in events if e.get("section") == "breaking"]
    major_list = [e for e in events if e.get("section") == "major"]
    general_list = [e for e in events if e.get("section") not in ("breaking", "major")]

    sections = {
        "breaking": breaking_list,
        "major": major_list,
        "general": general_list,
    }

    active_ads = []
    latest_obituaries = []
    try:
        with get_db() as conn:
            active_ads = [a for a in list_sponsored_ads(conn) if a.get("is_active") == 1]
            latest_obituaries = list_obituaries(conn, limit=3, active_only=True)
    except Exception:
        pass

    if request.headers.get("x-requested-with") == "XMLHttpRequest" or request.query_params.get("partial") == "1":
        return templates.TemplateResponse(
            "components/stories_stream.html",
            {
                "request": request,
                "events": events,
            },
        )

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "sections": sections,
            "trending": TRENDING,
            "all_tags": visible_tags if visible_tags else list(TIMELINE_TAGS.values()),
            "all_topics": list(TOPICS.values()),
            "active_tag": tag,
            "active_topic": topic,
            "active_tag_obj": TIMELINE_TAGS.get(tag) if tag else None,
            "active_topic_obj": TOPICS.get(topic) if topic else None,
            "source": source or "live",
            "active_sort": sort or "latest",
            "active_ads": active_ads,
            "latest_obituaries": latest_obituaries,
        },
    )


@router.get("/timeline/{story_id}", response_class=HTMLResponse)
def timeline(request: Request, story_id: str):
    story = TIMELINES.get(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Timeline not found")

    milestones = []
    for m in story["milestones"]:
        m_enriched = enrich_event(m)
        milestones.append(m_enriched)

    active_ads = []
    try:
        with get_db() as conn:
            active_ads = [a for a in list_sponsored_ads(conn) if a.get("is_active") == 1]
    except Exception:
        pass

    milestones_sorted = sorted(milestones, key=lambda m: m.get("date_iso") or "", reverse=True)

    return templates.TemplateResponse(
        "timeline.html",
        {
            "request": request,
            "story": story,
            "tag": TIMELINE_TAGS.get(story.get("tag")),
            "milestones": milestones_sorted,
            "active_ads": active_ads,
        },
    )


@router.get("/story/{story_id}", response_class=HTMLResponse)
def story_detail(request: Request, story_id: str):
    """Multi-source story comparison detail view."""
    raw_events = get_live_news()
    found_evt = next((e for e in raw_events if str(e.get("id")) == str(story_id)), None)

    if not found_evt:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM articles WHERE id = ? LIMIT 1;", (story_id,)).fetchone()
            if row:
                found_evt = dict(row)

    if not found_evt:
        found_evt = next((e for e in DEFAULT_EVENTS if str(e.get("id")) == str(story_id)), None)

    if not found_evt:
        raise HTTPException(status_code=404, detail="Story not found")

    story = enrich_event(found_evt)

    articles_list = []
    raw_sub_articles = story.get("articles") or []
    if not raw_sub_articles:
        raw_sub_articles = [found_evt]

    seen_sources = set()
    for art in raw_sub_articles:
        s_keys = art.get("sources") or []
        s_key = s_keys[0] if s_keys else "press"
        source_obj = SOURCES.get(s_key, {"id": s_key, "name": s_key.title(), "initial": s_key[:1].upper(), "kind": "press", "logo": None})
        headline = art.get("headline", story.get("headline", ""))
        art_url = art.get("url") or (story.get("source_links", {}).get(s_key) if story.get("source_links") else story.get("url", ""))
        time_display = art.get("time_ago") or art.get("published_raw") or story.get("time_ago") or "Recent"
        summary = art.get("summary", "")
        is_dv = is_dhivehi(headline) or art.get("is_dhivehi", False)

        articles_list.append({
            "id": art.get("id"),
            "headline": headline,
            "summary": summary,
            "url": art_url,
            "source_key": s_key,
            "source_obj": source_obj,
            "time_ago": time_display,
            "published_raw": art.get("published_raw"),
            "is_dhivehi": is_dv,
        })
        seen_sources.add(s_key)

    for s_key in story.get("sources", []):
        if s_key not in seen_sources and story.get("source_links", {}).get(s_key):
            source_obj = SOURCES.get(s_key, {"id": s_key, "name": s_key.title(), "initial": s_key[:1].upper(), "kind": "press", "logo": None})
            articles_list.append({
                "id": f"{s_key}-{story.get('id')}",
                "headline": story.get("headline", ""),
                "summary": story.get("summary", ""),
                "url": story.get("source_links", {}).get(s_key),
                "source_key": s_key,
                "source_obj": source_obj,
                "time_ago": story.get("time_ago") or "Recent",
                "published_raw": story.get("published_raw"),
                "is_dhivehi": story.get("is_dhivehi", False),
            })

    active_ads = []
    try:
        with get_db() as conn:
            active_ads = [a for a in list_sponsored_ads(conn) if a.get("is_active") == 1]
    except Exception:
        pass

    return templates.TemplateResponse(
        "story_detail.html",
        {
            "request": request,
            "story": story,
            "articles": articles_list,
            "active_ads": active_ads,
        },
    )


@router.get("/alerts", response_class=HTMLResponse)
def alerts_page(request: Request, chat_id: Optional[str] = None):
    """Web portal for fine-tuning Telegram alert categories and keywords."""
    user = get_current_user(request)
    if not chat_id and user and user.get("telegram_chat_id"):
        chat_id = user["telegram_chat_id"]
    subscriber = None
    disciplines = (user.get("tender_alert_disciplines") if user else None) or ["All"]
    keywords = ["all_news", "breaking", "janaza"]
    if chat_id:
        try:
            with get_db() as conn:
                sub_data = get_telegram_subscriber(conn, chat_id)
                if sub_data:
                    subscriber = sub_data
                    disciplines = sub_data.get("disciplines") or disciplines
                    keywords = sub_data.get("keywords") or keywords
        except Exception:
            pass

    bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", "khulaasaa_bot").replace("@", "")

    return templates.TemplateResponse(
        "alerts.html",
        {
            "request": request,
            "current_user": user,
            "chat_id": chat_id,
            "subscriber": subscriber,
            "disciplines": disciplines,
            "keywords": keywords,
            "bot_username": bot_username,
        },
    )


@router.get("/collections/{slug}", response_class=HTMLResponse)
def collection_view(request: Request, slug: str):
    """Deep-link to narrative timeline collection or filtered story track."""
    if slug in TIMELINES:
        return timeline(request, slug)

    for s_id, s_obj in TIMELINES.items():
        if s_obj.get("tag") == slug:
            return timeline(request, s_id)

    if slug in TIMELINE_TAGS:
        return RedirectResponse(url=f"/?tag={slug}")

    raise HTTPException(status_code=404, detail="Collection not found")


@router.get("/about", response_class=HTMLResponse)
def about_page(request: Request):
    """About Khulaasaa, editorial mission, platform pillars, and contact."""
    return templates.TemplateResponse("about.html", {"request": request})


@router.get("/compliance", response_class=HTMLResponse)
@router.get("/legality", response_class=HTMLResponse)
def compliance_page(request: Request):
    """Legal fair dealing basis, copyright compliance, and publisher removal SLA."""
    return templates.TemplateResponse("compliance.html", {"request": request})


@router.get("/feed.xml", response_class=Response)
@router.get("/rss", response_class=Response)
def rss_feed():
    """World News Aggregator Standard RSS 2.0 syndication feed."""
    events = [enrich_event(e) for e in get_live_news()]
    items_xml = []
    for e in events[:35]:
        h = html.escape(e.get("headline", ""))
        desc = html.escape(e.get("summary", ""))
        link = html.escape(e.get("url") or "https://khulaasaa.tech/")
        pub = e.get("published_raw", "")
        guid = html.escape(e.get("id", ""))
        items_xml.append(f"""    <item>
      <title>{h}</title>
      <description>{desc}</description>
      <link>{link}</link>
      <pubDate>{pub}</pubDate>
      <guid isPermaLink="false">{guid}</guid>
    </item>""")
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Khulaasaa — Verified Maldivian News &amp; Procurement Aggregator</title>
    <description>Chronological narrative tracking and multi-outlet verified news intelligence for the Maldives.</description>
    <link>https://khulaasaa.tech/</link>
    <language>dv,en</language>
{chr(10).join(items_xml)}
  </channel>
</rss>"""
    return Response(content=xml_content.encode("utf-8"), media_type="application/xml; charset=utf-8")


@router.get("/obituaries", response_class=HTMLResponse)
@router.get("/janaza", response_class=HTMLResponse)
def obituaries_page(
    request: Request,
    q: Optional[str] = None,
    atoll: Optional[str] = None,
    region: Optional[str] = None,
):
    with get_db() as conn:
        obs = list_obituaries(conn, search_q=q, atoll_code=atoll, region_group=region, limit=100, active_only=True)
        active_ads = [a for a in list_sponsored_ads(conn) if a.get("is_active") == 1]
    return templates.TemplateResponse(
        "obituaries.html",
        {
            "request": request,
            "obituaries": obs,
            "search_q": q,
            "active_atoll": atoll,
            "active_region": region,
            "atolls": ATOLL_TAXONOMY,
            "active_ads": active_ads,
        },
    )


@router.get("/hooks85", response_class=HTMLResponse)
def hooks85_page(request: Request):
    """Hooks85 official business software landing page."""
    return templates.TemplateResponse("hooks85.html", {"request": request})


@router.get("/subscription", response_class=HTMLResponse)
def subscription_page(
    request: Request,
    plan: Optional[str] = "tender_erp",
    notice_id: Optional[str] = None,
    msg: Optional[str] = None,
):
    bid_data = None
    if notice_id:
        with get_db() as conn:
            cur = conn.execute(
                """
                SELECT * FROM v_bids_enriched 
                WHERE notice_id = ? OR CAST(id AS TEXT) = ? OR reference_number = ? 
                LIMIT 1;
                """,
                (str(notice_id), str(notice_id), str(notice_id)),
            )
            row = cur.fetchone()
            if row:
                bid_data = dict(row)

    active_ads = []
    try:
        with get_db() as conn:
            active_ads = [a for a in list_sponsored_ads(conn) if a.get("is_active") == 1]
    except Exception:
        pass

    hooks85_url = os.environ.get("HOOKS85_URL", "https://app.hooks85.com").rstrip("/")

    return templates.TemplateResponse(
        "subscription.html",
        {
            "request": request,
            "bid": bid_data,
            "plan_preset": plan or "tender_erp",
            "active_ads": active_ads,
            "success_msg": msg,
            "hooks85_url": hooks85_url,
        },
    )


@router.post("/subscription/inquire")
async def subscription_inquire(request: Request):
    from fastapi import status
    import urllib.parse

    form = await request.form()
    company_name = str(form.get("company_name", "")).strip()
    contact_name = str(form.get("contact_name", "")).strip()
    phone = str(form.get("phone", "")).strip()
    email = str(form.get("email", "")).strip()
    island_atoll = str(form.get("island_atoll", "")).strip()
    plan_tier = str(form.get("plan_tier", "tender_erp")).strip()
    modules_list = form.getlist("modules")
    interested_modules = ", ".join(str(m) for m in modules_list) if modules_list else ""
    notice_id = str(form.get("notice_id", "")).strip()
    notes = str(form.get("notes", "")).strip()

    with get_db() as conn:
        save_hooks85_subscription(
            conn,
            {
                "company_name": company_name,
                "contact_name": contact_name,
                "phone": phone,
                "email": email,
                "island_atoll": island_atoll,
                "plan_tier": plan_tier,
                "interested_modules": interested_modules,
                "notice_id": notice_id,
                "notes": notes,
            },
        )

    redirect_url = f"/subscription?msg={urllib.parse.quote_plus('Thank you! Your hooks85 inquiry has been registered. Our onboarding specialist will contact you directly via Phone/WhatsApp.')}"
    if notice_id:
        redirect_url += f"&notice_id={urllib.parse.quote_plus(str(notice_id))}"

    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
