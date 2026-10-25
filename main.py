"""
Khulaasaa / Dispatch Web Server.

Modular FastAPI Application entrypoint:
- Business Logic: services/ (clustering, news_service, tenders_service)
- Data Repositories: data/repos/ (bids, jobs, stories, obituaries, ads, users, subscribers)
- Scrapers: scrapers/news/, scrapers/tenders/
- Presentation Routers: routers/ (web_ui, api_news, api_jobs, api_ads, admin, webhooks)

Run:
    uvicorn main:app --reload --port 8300

Admin console (HTTP Basic):
    user: editor   pass: set via EDITOR_PASSWORD env var (default "changeme")
"""
from __future__ import annotations

import os
import threading
import time
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from core.deps import get_current_user, require_editor, templates
from data.database import (
    get_db,
    init_db,
    purge_expired_bids,
    query_bids,
    upsert_bid,
    query_articles,
    upsert_article,
    register_or_update_telegram_subscriber,
    get_telegram_subscribers,
    get_telegram_subscriber,
    register_or_update_viber_subscriber,
    get_viber_subscribers,
    get_viber_subscriber,
    get_bids_filter_options,
    list_sponsored_ads,
    upsert_sponsored_ad,
    get_sponsored_ad,
    toggle_sponsored_ad,
    delete_sponsored_ad,
    list_obituaries,
    get_obituary,
    get_obituary_by_slug,
    upsert_obituary,
    toggle_obituary,
    delete_obituary,
    create_user,
    authenticate_user,
    get_user_by_id,
    get_user_by_email,
    get_user_by_telegram_id,
    get_user_by_viber_id,
    update_user_plan,
    update_user_job_alerts,
    create_user_session,
    get_user_from_session,
    delete_user_session,
    save_user_cv,
    get_user_cv,
    save_company_profile,
    get_company_profile,
    STANDARD_LANGUAGES,
    EDUCATION_LEVELS,
    STANDARD_INSTITUTIONS,
    LANGUAGE_PROFICIENCIES,
    upsert_job,
    query_jobs,
    get_job_disciplines,
    get_job_by_id,
)
from data.stories import (
    APPROVAL_LOG,
    DEFAULT_EVENTS,
    JOBS,
    PENDING_CLUSTERS,
    SOURCES,
    TIMELINE_TAGS,
    TIMELINES,
    TOPICS,
    TRENDING,
    approve_cluster as process_approve_cluster,
)
from scrapers.news import cluster_articles, fetch_all_live_news
from scrapers.jobs import JOB_DISCIPLINES, sync_jobs
from scrapers.translator import (
    is_dhivehi,
    translate_agency,
    translate_dhivehi_title,
    translate_venue,
)
from services.news_service import enrich_event, get_live_news
from services.hooks85_service import register_khulaasaa_manifest
from services.tenders_service import (
    CACHE_TTL_SECONDS,
    _LIVE_BIDS_IS_SYNCING,
    _LIVE_BIDS_LAST_SYNC,
    _LIVE_BIDS_LOCK,
    get_live_bids,
    trigger_bids_background_sync,
)
from alerts.telegram import (
    dispatch_job_alerts,
    dispatch_news_alerts,
    dispatch_sponsored_broadcast,
    dispatch_tender_alerts,
    format_job_alert_html,
    format_tender_alert_html,
    get_telegram_credentials,
    handle_incoming_telegram_update,
    send_telegram_message,
    set_telegram_chat_menu_button,
    start_telegram_bot_polling,
)
from alerts.viber import (
    dispatch_viber_bid_alerts,
    dispatch_viber_job_alerts,
    dispatch_viber_news_alerts,
    dispatch_viber_obituary_alerts,
    dispatch_viber_sponsored_broadcast,
    format_viber_job,
    get_viber_credentials,
    handle_viber_webhook_event,
    send_viber_message,
    set_viber_webhook,
)

from routers.admin import router as admin_router
from routers.api_ads import router as api_ads_router
from routers.api_jobs import router as api_jobs_router
from routers.api_news import router as api_news_router
from routers.api_rfq import router as api_rfq_router
from routers.web_ui import router as web_ui_router
from routers.web_rentals import router as web_rentals_router
from routers.webhooks import router as webhooks_router



def _periodic_sync_worker():
    """Background worker that periodically syncs news and tenders every 3 minutes."""
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    time.sleep(10)
    while True:
        try:
            get_live_news(force_refresh=True)
        except Exception:
            pass
        time.sleep(180)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup lifecycle
    init_db(seed_bids=True)
    with get_db() as conn:
        purge_expired_bids(conn, retention_days=30)
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        trigger_bids_background_sync(force=False)
        start_telegram_bot_polling()
        set_telegram_chat_menu_button()
        try:
            threading.Thread(target=register_khulaasaa_manifest, daemon=True, name="Hooks85ManifestRegister").start()
        except Exception:
            pass
        threading.Thread(target=_periodic_sync_worker, daemon=True, name="PeriodicNewsSync").start()
    yield
    # Shutdown lifecycle
    try:
        from data.postgres_adapter import close_connection_pool
        close_connection_pool()
    except Exception:
        pass


app = FastAPI(
    title="Khulaasaa / Dispatch",
    description="Verified Maldivian News & Procurement Intelligence Portal",
    lifespan=lifespan,
)

# Static assets mount
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/healthz")
def healthz():
    """Liveness/readiness probe for Docker/orchestrators."""
    return {"status": "ok"}


# Mount domain presentation routers
app.include_router(web_ui_router)
app.include_router(web_rentals_router)
app.include_router(api_news_router)
app.include_router(api_rfq_router)
app.include_router(api_jobs_router)
app.include_router(api_ads_router)
app.include_router(admin_router)
app.include_router(webhooks_router)


__all__ = [
    "app",
    "templates",
    "require_editor",
    "get_current_user",
    "get_live_news",
    "enrich_event",
    "get_live_bids",
    "trigger_bids_background_sync",
    "send_telegram_message",
    "send_viber_message",
    "format_viber_job",
    "format_job_alert_html",
    "format_tender_alert_html",
    "dispatch_tender_alerts",
    "dispatch_news_alerts",
    "dispatch_job_alerts",
    "dispatch_viber_news_alerts",
    "dispatch_viber_obituary_alerts",
    "dispatch_viber_job_alerts",
    "dispatch_viber_bid_alerts",
    "dispatch_sponsored_broadcast",
    "dispatch_viber_sponsored_broadcast",
    "set_viber_webhook",
    "handle_viber_webhook_event",
    "handle_incoming_telegram_update",
    "start_telegram_bot_polling",
    "set_telegram_chat_menu_button",
    "get_telegram_credentials",
    "get_viber_credentials",
    "SOURCES",
    "TIMELINES",
    "TIMELINE_TAGS",
    "TOPICS",
    "TRENDING",
    "DEFAULT_EVENTS",
    "JOBS",
    "PENDING_CLUSTERS",
    "APPROVAL_LOG",
    "process_approve_cluster",
    "sync_jobs",
    "JOB_DISCIPLINES",
    "is_dhivehi",
    "translate_dhivehi_title",
    "translate_agency",
    "translate_venue",
    "_LIVE_BIDS_LOCK",
    "_LIVE_BIDS_LAST_SYNC",
    "_LIVE_BIDS_IS_SYNCING",
    "CACHE_TTL_SECONDS",
]
