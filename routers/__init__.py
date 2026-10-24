"""
FastAPI Routers Package.
Contains presentation layer route controllers for Web UI, APIs, Admin Console, and Bot Webhooks.
"""
from routers.web_ui import router as web_ui_router
from routers.api_news import router as api_news_router
from routers.api_jobs import router as api_jobs_router
from routers.api_ads import router as api_ads_router
from routers.admin import router as admin_router
from routers.webhooks import router as webhooks_router

__all__ = [
    "web_ui_router",
    "api_news_router",
    "api_jobs_router",
    "api_ads_router",
    "admin_router",
    "webhooks_router",
]
