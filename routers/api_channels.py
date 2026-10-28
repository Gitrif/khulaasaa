"""
API Router for Verified Telegram and Viber Channel Linking.
Handles single-use token generation, deep links, verification callbacks, and disconnects.
"""
from __future__ import annotations

import os
from typing import Any
from fastapi import APIRouter, HTTPException, Request

from core.deps import get_current_user
from data.database import get_db
from services.channel_linking_service import (
    create_channel_link_token,
    disconnect_channel,
    get_channel_connection_status,
    get_telegram_deep_link,
)

router = APIRouter(prefix="/api/channels", tags=["channels"])


@router.get("/status")
def api_get_channels_status(request: Request):
    """Retrieve truthful connection and verification status for all alert channels."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    with get_db() as conn:
        status = get_channel_connection_status(conn, user["id"])

    return {"status": "ok", "channels": status}


@router.post("/telegram/token")
def api_create_telegram_token(request: Request):
    """Generate a 15-minute single-use deep-linking token for Telegram."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    with get_db() as conn:
        token = create_channel_link_token(conn, user["id"], "telegram", ttl_minutes=15)
        deep_link = get_telegram_deep_link(token)

    return {
        "status": "ok",
        "token": token,
        "deep_link": deep_link,
        "expires_in_minutes": 15,
    }


@router.post("/telegram/disconnect")
def api_disconnect_telegram(request: Request):
    """Disconnect and unverify Telegram for the authenticated user."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    with get_db() as conn:
        disconnect_channel(conn, user["id"], "telegram")
        status = get_channel_connection_status(conn, user["id"])

    return {
        "status": "ok",
        "message": "Telegram channel disconnected successfully",
        "channels": status,
    }


@router.post("/viber/token")
def api_create_viber_token(request: Request):
    """Generate a 15-minute single-use verification PIN for Viber."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    with get_db() as conn:
        pin = create_channel_link_token(conn, user["id"], "viber", ttl_minutes=15)

    bot_uri = os.environ.get("VIBER_BOT_URI", "khulaasaa")
    return {
        "status": "ok",
        "token": pin,
        "bot_uri": f"viber://pa?chatURI={bot_uri}",
        "expires_in_minutes": 15,
        "instructions": "Open the Khulaasaa Viber bot and send this 6-digit PIN code to verify your channel.",
    }


@router.post("/viber/verify")
async def api_verify_viber_token(request: Request):
    """Reject client-supplied Viber IDs; verification must come from a signed bot webhook."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    raise HTTPException(
        status_code=410,
        detail=(
            "For secure verification, send the generated PIN to the Khulaasaa Viber bot. "
            "The bot will verify your Viber identity directly."
        ),
    )


@router.post("/viber/disconnect")
def api_disconnect_viber(request: Request):
    """Disconnect and unverify Viber for the authenticated user."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    with get_db() as conn:
        disconnect_channel(conn, user["id"], "viber")
        status = get_channel_connection_status(conn, user["id"])

    return {
        "status": "ok",
        "message": "Viber channel disconnected successfully",
        "channels": status,
    }
