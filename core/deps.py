"""
Core dependencies, authentication providers, and template engine.
"""
from __future__ import annotations

import os
import secrets
import warnings
from typing import Any, Optional
from urllib.parse import urlencode

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from data.database import (
    create_user,
    get_db,
    get_user_by_email,
    get_user_by_id,
    get_user_from_session,
)
from data.utils import format_tender_date, normalize_tender_info
from services.hooks85_service import verify_hooks85_session

def build_filter_url(base_path: str, **params: Any) -> str:
    """Build a canonical filter URL preserving non-empty query parameters."""
    clean = {k: str(v) for k, v in params.items() if v not in (None, "", False)}
    if not clean:
        return base_path
    return f"{base_path}?{urlencode(clean)}"


templates = Jinja2Templates(directory="templates")
templates.env.filters["format_tender_date"] = format_tender_date
templates.env.filters["normalize_tender_info"] = normalize_tender_info
templates.env.globals["build_filter_url"] = build_filter_url

security = HTTPBasic()
EDITOR_USER = os.environ.get("EDITOR_USERNAME", "editor")
EDITOR_PASS = os.environ.get("EDITOR_PASSWORD", "changeme")

if EDITOR_PASS == "changeme":
    warnings.warn(
        "EDITOR_PASSWORD is still the default 'changeme'. Fine for local "
        "dev, NOT fine for anything reachable outside your own machine -- "
        "set a real value via the environment (see .env.example) before "
        "deploying anywhere.",
        stacklevel=2,
    )


def require_editor(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Validate HTTP Basic credentials for admin / editor access."""
    correct_user = secrets.compare_digest(credentials.username, EDITOR_USER)
    correct_pass = secrets.compare_digest(credentials.password, EDITOR_PASS)
    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid editor credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def get_current_user(request: Request) -> Optional[dict[str, Any]]:
    """Retrieve logged-in user from hooks85 Gateway or local session."""
    h85_cookie = request.cookies.get("hooks85_session")
    if h85_cookie:
        h85_user = verify_hooks85_session(h85_cookie)
        if h85_user and h85_user.get("email"):
            try:
                with get_db() as conn:
                    local_user = get_user_by_email(conn, h85_user["email"])
                    if not local_user:
                        uid = create_user(
                            conn,
                            email=h85_user["email"],
                            password=secrets.token_urlsafe(32),
                            full_name=h85_user.get("full_name") or h85_user["email"].split("@")[0],
                            is_paid=h85_user.get("is_paid", 0),
                        )
                        local_user = get_user_by_id(conn, uid)
                    if local_user:
                        local_user["hooks85"] = h85_user
                        return local_user
            except Exception:
                return h85_user

    token = request.cookies.get("session_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
    if not token:
        return None

    # Check if token is a hooks85 JWT
    if token.startswith("eyJ"):
        h85_user = verify_hooks85_session(token)
        if h85_user and h85_user.get("email"):
            try:
                with get_db() as conn:
                    local_user = get_user_by_email(conn, h85_user["email"])
                    if local_user:
                        return local_user
            except Exception:
                pass

    try:
        with get_db() as conn:
            return get_user_from_session(conn, token)
    except Exception:
        return None


def is_authorized_editor(request: Request) -> bool:
    """Non-blocking check whether the request possesses editor/admin authorization."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Basic "):
        import base64
        try:
            raw = base64.b64decode(auth_header[6:].strip()).decode("utf-8")
            u, p = raw.split(":", 1)
            if secrets.compare_digest(u, EDITOR_USER) and secrets.compare_digest(p, EDITOR_PASS):
                return True
        except Exception:
            pass

    user = get_current_user(request)
    if user and (user.get("role") in ("admin", "editor") or user.get("is_admin")):
        return True
    return False
