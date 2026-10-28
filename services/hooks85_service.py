"""
hooks85 Gateway, Auth, and Subscription Integration Service.
Implements the essentials-v1 contract for unified Single Sign-On (SSO),
session verification, and subscription entitlement resolution.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any, Optional

logger = logging.getLogger(__name__)

HOOKS85_GATEWAY_URL = os.environ.get("HOOKS85_GATEWAY_URL", "http://localhost:8101").rstrip("/")
HOOKS85_PAYMENT_URL = os.environ.get("HOOKS85_PAYMENT_URL", "http://localhost:8105").rstrip("/")
HOOKS85_INTERNAL_TOKEN = os.environ.get(
    "HOOKS85_INTERNAL_TOKEN",
    "LqS1F9T3UHxHMr82Eu5cvXnSGYWKgQAQYIW2omSYGNc",
)

# 30-second TTL session cache per essentials-v1 contract
_SESSION_CACHE: dict[str, dict[str, Any]] = {}
SESSION_CACHE_TTL = 30.0
SESSION_FAILURE_CACHE_TTL = 15.0


def verify_hooks85_session(session_cookie_or_token: str) -> Optional[dict[str, Any]]:
    """Verify session against hooks85 Gateway (essentials/v1 contract)."""
    if not session_cookie_or_token:
        return None

    now = time.time()
    cached = _SESSION_CACHE.get(session_cookie_or_token)
    if cached:
        ttl = cached.get("ttl", SESSION_CACHE_TTL)
        if now - cached["cached_at"] < ttl:
            return cached["user"]
        _SESSION_CACHE.pop(session_cookie_or_token, None)

    url = f"{HOOKS85_GATEWAY_URL}/api/v1/auth/session"
    headers = {"Accept": "application/json"}
    if session_cookie_or_token.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {session_cookie_or_token}"
    else:
        headers["Cookie"] = f"hooks85_session={session_cookie_or_token}"

    req = urllib.request.Request(url, headers=headers)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "authenticated":
                billing = data.get("billing") or data.get("personal_billing") or {}
                b_status = billing.get("status", "")
                is_paid = 1 if b_status in ("active", "trial") or billing.get("can_write") else 0

                user_info = {
                    "id": data.get("user_id"),
                    "email": data.get("email"),
                    "full_name": data.get("display_name") or data.get("email", ""),
                    "is_paid": is_paid,
                    "tenant_id": data.get("tenant_id"),
                    "tenant_plan": data.get("tenant_plan") or billing.get("plan"),
                    "hooks85_session_id": data.get("session_id"),
                }
                _SESSION_CACHE[session_cookie_or_token] = {
                    "cached_at": now,
                    "user": user_info,
                }
                return user_info
    except urllib.error.HTTPError as e:
        # Do not cache an explicit invalid/expired session; other Gateway errors may be transient.
        if e.code not in (401, 403):
            _SESSION_CACHE[session_cookie_or_token] = {
                "cached_at": now,
                "user": None,
                "ttl": SESSION_FAILURE_CACHE_TTL,
            }
        logger.debug("hooks85 Gateway session check returned HTTP %s", e.code)
    except Exception as e:
        # Avoid repeating a slow timeout for every page/API request when Gateway is offline.
        _SESSION_CACHE[session_cookie_or_token] = {
            "cached_at": now,
            "user": None,
            "ttl": SESSION_FAILURE_CACHE_TTL,
        }
        logger.debug("hooks85 Gateway session check skipped or offline: %s", e)
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000
        if elapsed_ms >= 1000:
            logger.warning("Slow hooks85 session verification: %.1fms", elapsed_ms)

    return None


def login_via_hooks85(identifier: str, password: str) -> Optional[dict[str, Any]]:
    """Authenticate credentials against hooks85 Gateway."""
    url = f"{HOOKS85_GATEWAY_URL}/api/v1/auth/password/login"
    payload = json.dumps({"identifier": identifier, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            cookie_header = resp.headers.get("Set-Cookie") or ""
            cookie_val = ""
            for part in cookie_header.split(";"):
                if part.strip().startswith("hooks85_session="):
                    cookie_val = part.strip().split("=", 1)[1]
                    break

            session_obj = data.get("session") or {}
            billing = session_obj.get("billing") or session_obj.get("personal_billing") or {}
            b_status = billing.get("status", "")
            is_paid = 1 if b_status in ("active", "trial") or billing.get("can_write") else 0

            user_dict = {
                "id": session_obj.get("user_id") or data.get("user_id"),
                "email": session_obj.get("email") or identifier,
                "full_name": session_obj.get("display_name") or identifier.split("@")[0],
                "is_paid": is_paid,
            }
            return {
                "status": "ok",
                "user": user_dict,
                "token": data.get("token") or cookie_val,
                "cookie_val": cookie_val,
            }
    except urllib.error.HTTPError as e:
        err_msg = "Invalid email or password"
        try:
            err_data = json.loads(e.read().decode("utf-8"))
            err_msg = err_data.get("detail", err_msg)
        except Exception:
            pass
        return {"status": "error", "code": e.code, "detail": err_msg}
    except Exception as e:
        logger.warning("hooks85 login connection failed: %s", e)
        return None


def register_via_hooks85(email: str, password: str, display_name: str) -> Optional[dict[str, Any]]:
    """Register a new user account through hooks85 Gateway."""
    url = f"{HOOKS85_GATEWAY_URL}/api/v1/auth/register"
    payload = json.dumps({
        "email": email,
        "password": password,
        "display_name": display_name,
    }).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            cookie_header = resp.headers.get("Set-Cookie") or ""
            cookie_val = ""
            for part in cookie_header.split(";"):
                if part.strip().startswith("hooks85_session="):
                    cookie_val = part.strip().split("=", 1)[1]
                    break

            session_obj = data.get("session") or {}
            user_dict = {
                "id": session_obj.get("user_id") or data.get("user_id"),
                "email": session_obj.get("email") or email,
                "full_name": session_obj.get("display_name") or display_name,
                "is_paid": 0,
            }
            return {
                "status": "ok",
                "user": user_dict,
                "token": data.get("token") or cookie_val,
                "cookie_val": cookie_val,
            }
    except urllib.error.HTTPError as e:
        err_msg = "Registration failed"
        try:
            err_data = json.loads(e.read().decode("utf-8"))
            err_msg = err_data.get("detail", err_msg)
        except Exception:
            pass
        return {"status": "error", "code": e.code, "detail": err_msg}
    except Exception as e:
        logger.warning("hooks85 registration connection failed: %s", e)
        return None


def register_khulaasaa_manifest() -> bool:
    """Send Khulaasaa app manifest to hooks85 Gateway (essentials/v1 contract)."""
    url = f"{HOOKS85_GATEWAY_URL}/internal/v1/apps/app_khulaasaa/manifest"
    manifest = {
        "name": "Khulaasaa Intelligence",
        "contract": "essentials/v1",
        "owner_types": ["business", "person"],
        "roles": ["OWNER", "EDITOR", "SUBSCRIBER"],
        "features": ["khulaasaa", "khulaasaa.bids", "khulaasaa.jobs", "khulaasaa.cv"],
        "size_units": [],
        "meters": [],
        "events": ["billing.changed"],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(manifest).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Hooks85-Source-Service": "khulaasaa-app",
            "Authorization": f"Bearer {HOOKS85_INTERNAL_TOKEN}",
        },
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            return resp.status in (200, 201)
    except Exception as e:
        logger.debug("Could not register Khulaasaa manifest with hooks85 Gateway: %s", e)
        return False
