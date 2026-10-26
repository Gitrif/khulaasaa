"""
User Feedback, Suggestions, and Bug Reporting API Router.
Accepts user feedback in alpha/beta and alerts team via Telegram and logs.
"""
from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from data.database import get_db
from data.repos.feedback import save_user_feedback
from alerts.telegram_feedback import dispatch_feedback_alert

logger = logging.getLogger("khulaasaa.feedback_api")
router = APIRouter()


class FeedbackPayload(BaseModel):
    feedback_type: str = Field(default="feedback", description="suggestion, issue, or feedback")
    message: str = Field(..., min_length=3, max_length=5000)
    contact_info: Optional[str] = Field(default=None, max_length=255)
    page_url: Optional[str] = Field(default=None, max_length=500)


@router.post("/api/feedback")
async def submit_user_feedback(payload: FeedbackPayload, request: Request):
    """Submit user feedback or bug report."""
    user_agent = request.headers.get("user-agent", "")
    data = {
        "feedback_type": payload.feedback_type,
        "message": payload.message,
        "contact_info": payload.contact_info or "hooks.connect@gmail.com",
        "page_url": payload.page_url or request.headers.get("referer", "/"),
        "user_agent": user_agent[:255],
        "status": "new",
    }

    try:
        with get_db() as conn:
            feedback_id = save_user_feedback(conn, data)
        data["id"] = feedback_id
    except Exception as e:
        logger.error("Failed to save feedback to DB: %s", e)

    # Dispatch immediate real-time push to Telegram admin
    try:
        dispatch_feedback_alert(data)
    except Exception as e:
        logger.warning("Failed to dispatch Telegram feedback alert: %s", e)

    return {
        "status": "ok",
        "message": "Thank you! Your feedback has been received and forwarded to hooks.connect@gmail.com & engineering.",
    }
