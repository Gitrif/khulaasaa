"""
Web presentation router for User Account, Profile, and Follows Dashboard.
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from core.deps import get_current_user, templates
from data.database import (
    get_db,
    get_user_by_id,
    get_user_follow_counts,
    get_user_preferences,
    list_user_follows,
)
from services.channel_linking_service import get_channel_connection_status

router = APIRouter(tags=["web_account"])


@router.get("/account", response_class=HTMLResponse)
def page_user_account(request: Request):
    """User account management page."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/?auth=login&next=/account", status_code=302)

    with get_db() as conn:
        full_user = get_user_by_id(conn, user["id"])
        counts = get_user_follow_counts(conn, user["id"])

    return templates.TemplateResponse(
        request,
        "account.html",
        {
            "user": full_user,
            "follow_counts": counts,
        },
    )


@router.get("/following", response_class=HTMLResponse)
def page_user_following(request: Request):
    """Following dashboard: view and manage followed stories, topics, sections, and sources."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/?auth=login&next=/following", status_code=302)

    with get_db() as conn:
        all_follows = list_user_follows(conn, user["id"])
        counts = get_user_follow_counts(conn, user["id"])

    follows_by_type = {
        "story": [f for f in all_follows if f["target_type"] == "story"],
        "topic": [f for f in all_follows if f["target_type"] == "topic"],
        "section": [f for f in all_follows if f["target_type"] == "section"],
        "source": [f for f in all_follows if f["target_type"] == "source"],
    }

    return templates.TemplateResponse(
        request,
        "following.html",
        {
            "user": user,
            "follows": all_follows,
            "follows_by_type": follows_by_type,
            "counts": counts,
        },
    )


@router.get("/account/alerts", response_class=HTMLResponse)
def page_account_alerts(request: Request):
    """User notification preferences page."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/?auth=login&next=/account/alerts", status_code=302)

    with get_db() as conn:
        prefs = get_user_preferences(conn, user["id"])
        channels = get_channel_connection_status(conn, user["id"])
        counts = get_user_follow_counts(conn, user["id"])

    return templates.TemplateResponse(
        request,
        "account_alerts.html",
        {
            "user": user,
            "preferences": prefs,
            "channels": channels,
            "follow_counts": counts,
        },
    )


@router.get("/account/channels", response_class=HTMLResponse)
def page_account_channels(request: Request):
    """User connected channels management page."""
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/?auth=login&next=/account/channels", status_code=302)

    with get_db() as conn:
        channels = get_channel_connection_status(conn, user["id"])
        prefs = get_user_preferences(conn, user["id"])

    return templates.TemplateResponse(
        request,
        "account_channels.html",
        {
            "user": user,
            "channels": channels,
            "preferences": prefs,
        },
    )
