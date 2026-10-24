"""
Telegram & Viber Bot Webhooks and Alert Subscriptions Router.
"""
from __future__ import annotations

import html
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from data.database import (
    get_db,
    get_telegram_subscribers,
    get_viber_subscribers,
    query_bids,
    register_or_update_telegram_subscriber,
    register_or_update_viber_subscriber,
)
from alerts.telegram import (
    format_tender_alert_html,
    handle_incoming_telegram_update,
    send_telegram_message,
)
from alerts.viber import (
    handle_viber_webhook_event,
    send_viber_message,
)

router = APIRouter()


@router.post("/api/alerts/telegram/test")
async def telegram_test_alert(request: Request):
    """Send a test tender alert to the specified Telegram chat ID."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    chat_id = body.get("chat_id")
    bot_token = body.get("bot_token")
    notice_id = body.get("notice_id")

    with get_db() as conn:
        if notice_id:
            res = query_bids(conn, search_q=notice_id)
            sample_bid = res[0] if res else None
        else:
            sample_bid = None

        if not sample_bid:
            bids_list = query_bids(conn, limit=1)
            sample_bid = bids_list[0] if bids_list else {
                "title": "އއ. އުކުޅަހު ޞިއްޙީ މަރުކަޒުގެ ލެބޯޓްރީ ޢިމާރާތުގެ މަސައްކަތް ކޮށްދޭނެ ފަރާތެއް ހޯދުމަށް",
                "title_en": "Seeking contractor for AA. Ukulhas Health Centre Laboratory Building works",
                "agency": "Ministry of Health",
                "entity_type": "Ministry",
                "discipline": "Construction",
                "gazette_type": "Work",
                "ref": "(IUL)23-L/23/2026/45",
                "submission_date": "2026-11-15T11:00:00",
                "submission_location": "AA. Ukulhas Health Centre Secretariat",
                "info_date": "2026-10-25 10:00",
                "info_location": "Online via Zoom",
                "source_url": "https://gazette.gov.mv/iulaan/166396",
            }

    import main
    msg_html = format_tender_alert_html(sample_bid)
    send_fn = getattr(main, "send_telegram_message", send_telegram_message)
    ok, err = send_fn(msg_html, chat_id=chat_id, bot_token=bot_token)
    if not ok:
        return {"ok": False, "error": err}
    return {"ok": True, "message": "Test alert successfully sent to Telegram!"}


@router.post("/api/alerts/telegram/subscribe")
async def telegram_subscribe(request: Request):
    """Register or update Telegram alert preferences."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    chat_id = body.get("chat_id")
    if not chat_id:
        raise HTTPException(status_code=400, detail="Telegram chat_id is required")

    name = body.get("name") or "Khulaasaa User"
    disciplines = body.get("disciplines") or []
    keywords = body.get("keywords") or []
    bot_token = body.get("bot_token")

    with get_db() as conn:
        sub_id = register_or_update_telegram_subscriber(
            conn,
            chat_id=str(chat_id),
            name=name,
            disciplines=disciplines,
            keywords=keywords,
            is_active=1,
        )

    conf_msg = (
        f"✅ <b>Khulaasaa Tender Alerts Activated!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>Subscriber:</b> {html.escape(name)}\n"
        f"🏷 <b>Tracked Disciplines:</b> {html.escape(', '.join(disciplines) if disciplines else 'All Disciplines')}\n"
        f"🔍 <b>Keywords:</b> {html.escape(', '.join(keywords) if keywords else 'All Notices')}\n\n"
        f"You will receive immediate alerts whenever a matching government tender is published on gazette.gov.mv."
    )
    send_telegram_message(conf_msg, chat_id=str(chat_id), bot_token=bot_token)

    return {
        "ok": True,
        "subscriber_id": sub_id,
        "message": f"Subscribed successfully for chat ID {chat_id}",
    }


@router.post("/api/alerts/telegram/webhook")
async def telegram_webhook(request: Request):
    """Webhook endpoint to process incoming Telegram messages, commands, and callback queries."""
    try:
        update = await request.json()
        handle_incoming_telegram_update(update)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get("/api/alerts/telegram/subscribers")
def telegram_list_subscribers():
    """List active Telegram subscribers."""
    with get_db() as conn:
        return get_telegram_subscribers(conn)


@router.post("/api/alerts/viber/subscribe")
async def viber_subscribe(request: Request):
    """Register or update Viber alert preferences."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    viber_user_id = body.get("viber_user_id") or body.get("chat_id")
    if not viber_user_id:
        raise HTTPException(status_code=400, detail="Viber user ID is required")

    name = body.get("name") or "Khulaasaa User"
    categories = body.get("categories") or ["all", "news", "janaza", "bids", "jobs"]

    with get_db() as conn:
        sub_id = register_or_update_viber_subscriber(
            conn,
            viber_user_id=str(viber_user_id).strip(),
            name=name,
            categories=categories,
            is_active=1,
        )

    conf_msg = (
        f"✅ Khulaasaa Live Alerts Activated!\n"
        f"👤 Subscriber: {name}\n"
        f"🔔 Categories: {', '.join(categories)}\n\n"
        f"You will now receive breaking alerts on Viber."
    )
    send_viber_message(str(viber_user_id).strip(), conf_msg)

    return {
        "ok": True,
        "subscriber_id": sub_id,
        "message": f"Subscribed successfully for Viber user {viber_user_id}",
    }


@router.post("/api/alerts/viber/test")
async def viber_test_alert(request: Request):
    """Send a test alert to the specified Viber user ID."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    viber_user_id = body.get("viber_user_id")
    if not viber_user_id:
        raise HTTPException(status_code=400, detail="Viber user ID is required")

    msg = (
        "📢 *Khulaasaa Test Alert*\n\n"
        "This is a test notification confirming that your Viber connection is active and operational."
    )
    import main
    viber_send_fn = getattr(main, "send_viber_message", send_viber_message)
    res = viber_send_fn(str(viber_user_id).strip(), msg)
    if res.get("status") == 0:
        return {"ok": True, "message": "Test alert sent to Viber!"}
    return {"ok": False, "error": res.get("status_message", "Failed to send to Viber")}


@router.get("/api/alerts/viber/subscribers")
def viber_list_subscribers():
    """List active Viber subscribers."""
    with get_db() as conn:
        return get_viber_subscribers(conn)


@router.post("/webhook/viber")
async def viber_webhook(request: Request):
    """Public webhook endpoint for Viber Bot API events."""
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"status": 1, "message": "Invalid JSON"}, status_code=400)

    base_url = str(request.base_url).rstrip("/")
    result = handle_viber_webhook_event(payload, base_url=base_url)
    return JSONResponse(result)
