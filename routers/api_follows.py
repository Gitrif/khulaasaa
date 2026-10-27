"""
API Router for Content Follows (Stories, Topics, Sections, Publishers/Sources).
"""
from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from core.deps import get_current_user
from data.database import (
    add_follow,
    get_db,
    get_user_follow_counts,
    is_following,
    list_user_follows,
    remove_follow,
)

router = APIRouter(prefix="/api/follows", tags=["follows"])


@router.post("")
async def api_create_follow(request: Request):
    """Follow a story, topic, section, or publisher/source."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required to follow content")

    try:
        payload = await request.json()
    except Exception:
        payload = {}

    target_type = payload.get("target_type")
    target_id = payload.get("target_id")
    target_title = payload.get("target_title")

    if not target_type or not target_id:
        raise HTTPException(status_code=400, detail="target_type and target_id are required")

    try:
        with get_db() as conn:
            follow = add_follow(conn, user["id"], target_type, target_id, target_title)
            counts = get_user_follow_counts(conn, user["id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return JSONResponse({"status": "ok", "follow": follow, "counts": counts})


@router.delete("")
async def api_delete_follow(
    request: Request,
    target_type: Optional[str] = Query(None),
    target_id: Optional[str] = Query(None),
):
    """Unfollow a story, topic, section, or publisher/source."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required to unfollow content")

    if not target_type or not target_id:
        try:
            payload = await request.json()
            target_type = target_type or payload.get("target_type")
            target_id = target_id or payload.get("target_id")
        except Exception:
            pass

    if not target_type or not target_id:
        raise HTTPException(status_code=400, detail="target_type and target_id are required")

    with get_db() as conn:
        removed = remove_follow(conn, user["id"], target_type, target_id)
        counts = get_user_follow_counts(conn, user["id"])

    return {"status": "ok", "removed": removed, "counts": counts}


@router.get("")
def api_get_follows(
    request: Request,
    target_type: Optional[str] = Query(None),
):
    """List followed targets for the authenticated user."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    with get_db() as conn:
        items = list_user_follows(conn, user["id"], target_type=target_type)
        counts = get_user_follow_counts(conn, user["id"])

    return {"status": "ok", "follows": items, "counts": counts}


@router.get("/check")
def api_check_follow(
    request: Request,
    target_type: str = Query(...),
    target_id: str = Query(...),
):
    """Check if the current visitor is following a target."""
    user = get_current_user(request)
    if not user:
        return {"following": False}

    with get_db() as conn:
        following = is_following(conn, user["id"], target_type, target_id)

    return {"following": following}
