"""
Core dependencies, authentication providers, and template engine.
"""
from __future__ import annotations

import os
import secrets
import warnings
from typing import Any, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from data.database import get_db, get_user_from_session
from data.utils import format_tender_date, normalize_tender_info

templates = Jinja2Templates(directory="templates")
templates.env.filters["format_tender_date"] = format_tender_date
templates.env.filters["normalize_tender_info"] = normalize_tender_info

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
    """Retrieve logged-in user from session cookie or Bearer header."""
    token = request.cookies.get("session_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
    if not token:
        return None
    try:
        with get_db() as conn:
            return get_user_from_session(conn, token)
    except Exception:
        return None
