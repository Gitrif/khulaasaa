"""
Khulaasaa / Dispatch Web Server.

Modular FastAPI Application entrypoint:
- Business & Ingestion Services: services/ (news_service, tenders_service, jobs_service, sync_scheduler, ingestion/)
- Data Repositories: data/repos/ (bids, jobs, stories, obituaries, rentals, ads, users, subscribers)
- Scrapers: scrapers/ (common, news, tenders, jobs, rentals, obituaries)
- Presentation Routers: routers/ (web_ui, web_account, web_rentals, api_*, admin, webhooks)

Run:
    uvicorn main:app --reload --port 8300
"""
from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import os
import threading
import time

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

load_dotenv()

logger = logging.getLogger("khulaasaa.main")

from alerts.telegram import (
    send_telegram_message,
    set_telegram_chat_menu_button,
    start_telegram_bot_polling,
)
from alerts.viber import send_viber_message
from core.deps import get_current_user, require_editor, templates
from data.database import get_db, init_db, purge_expired_bids
from routers.admin import router as admin_router
from routers.api_ads import router as api_ads_router
from routers.api_auth import router as api_auth_router
from routers.api_channels import router as api_channels_router
from routers.api_feedback import router as api_feedback_router
from routers.api_follows import router as api_follows_router
from routers.api_jobs import router as api_jobs_router
from routers.api_news import router as api_news_router
from routers.api_preferences import router as api_preferences_router
from routers.api_rfq import router as api_rfq_router
from routers.web_account import router as web_account_router
from routers.web_rentals import router as web_rentals_router
from routers.web_ui import router as web_ui_router
from routers.webhooks import router as webhooks_router
from services.hooks85_service import register_khulaasaa_manifest
from services.news_service import init_news_cache
from services.sync_scheduler import start_sync_scheduler, stop_sync_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup lifecycle
    init_db(seed_bids=True)
    init_news_cache()
    with get_db() as conn:
        try:
            purge_expired_bids(conn, retention_days=30)
        except Exception:
            pass
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        start_sync_scheduler()
        start_telegram_bot_polling()
        set_telegram_chat_menu_button()
        try:
            from services.alert_delivery_worker import start_outbox_worker
            start_outbox_worker(interval_seconds=30)
        except Exception:
            pass
        try:
            threading.Thread(
                target=register_khulaasaa_manifest,
                daemon=True,
                name="Hooks85ManifestRegister",
            ).start()
        except Exception:
            pass
    yield
    # Shutdown lifecycle
    stop_sync_scheduler()
    try:
        from services.alert_delivery_worker import stop_outbox_worker
        stop_outbox_worker()
    except Exception:
        pass
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

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.middleware("http")
async def request_timing_middleware(request, call_next):
    """Expose server-side request duration and log slow requests for diagnosis."""
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000
    response.headers["Server-Timing"] = f"app;dur={duration_ms:.1f}"
    if duration_ms >= 1000:
        logger.warning(
            "Slow HTTP request: %s %s -> %s in %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
    return response


@app.get("/healthz")
def healthz():
    """Liveness/readiness probe for Docker/orchestrators."""
    return {"status": "ok"}


app.include_router(web_ui_router)
app.include_router(web_account_router)
app.include_router(web_rentals_router)
app.include_router(api_news_router)
app.include_router(api_follows_router)
app.include_router(api_preferences_router)
app.include_router(api_channels_router)
app.include_router(api_rfq_router)
app.include_router(api_jobs_router)
app.include_router(api_ads_router)
app.include_router(api_auth_router)
app.include_router(api_feedback_router)
app.include_router(admin_router)
app.include_router(webhooks_router)

__all__ = [
    "app",
    "get_current_user",
    "require_editor",
    "send_telegram_message",
    "send_viber_message",
    "templates",
]
