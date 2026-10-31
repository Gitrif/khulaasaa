"""
Shared HTTP client and BeautifulSoup helpers for Khulaasaa scrapers.
Standardizes timeout handling, retries, headers, response validation, and error reporting.
"""
from __future__ import annotations

import logging
import time
import urllib.error
import urllib.request
from typing import Any, Optional

import bs4
import requests

from scrapers.common.headers import DEFAULT_BROWSER_HEADERS, get_unverified_ssl_context

logger = logging.getLogger(__name__)
SSL_CTX = get_unverified_ssl_context()


def http_get(
    url: str,
    *,
    timeout: int = 12,
    headers: Optional[dict[str, str]] = None,
    params: Optional[dict[str, Any]] = None,
    session: Optional[requests.Session] = None,
    retries: int = 2,
    backoff_seconds: float = 0.25,
) -> Optional[requests.Response]:
    """
    Perform a standardized HTTP GET with default browser headers, bounded timeout, and retry handling.
    Uses `session.get` when a Session is provided, or `requests.get` otherwise so unit tests that
    monkeypatch `requests.get` remain compatible.
    """
    req_headers = dict(DEFAULT_BROWSER_HEADERS)
    if headers:
        req_headers.update(headers)

    attempts = max(1, int(retries))
    for attempt in range(1, attempts + 1):
        try:
            if session is not None:
                if hasattr(session, "headers") and isinstance(getattr(session, "headers", None), dict):
                    session.headers.update(req_headers)
                kwargs: dict[str, Any] = {"timeout": timeout}
            else:
                kwargs = {"headers": req_headers, "timeout": timeout}
            if params is not None:
                kwargs["params"] = params
            client = session if session is not None else requests
            resp = client.get(url, **kwargs)
            raw_status = getattr(resp, "status_code", 200)
            status_code = raw_status if isinstance(raw_status, int) else 200
            if status_code >= 500 and attempt < attempts:
                time.sleep(backoff_seconds * attempt)
                continue
            return resp
        except Exception as exc:
            if attempt < attempts:
                time.sleep(backoff_seconds * attempt)
                continue
            logger.debug("HTTP GET failed for %s after %d attempt(s): %s", url, attempts, exc)
            return None
    return None


def fetch_text(
    url: str,
    timeout: int = 12,
    headers: Optional[dict[str, str]] = None,
    params: Optional[dict[str, Any]] = None,
    session: Optional[requests.Session] = None,
    retries: int = 2,
    encoding: Optional[str] = None,
) -> Optional[str]:
    """Fetch raw text/HTML from a URL using `http_get` with standardized headers and status validation."""
    resp = http_get(
        url,
        timeout=timeout,
        headers=headers,
        params=params,
        session=session,
        retries=retries,
    )
    if resp is None:
        return None
    raw_status = getattr(resp, "status_code", 200)
    status_code = raw_status if isinstance(raw_status, int) else 200
    if status_code >= 400:
        logger.debug("HTTP %s fetching text %s", status_code, url)
        return None
    if encoding and hasattr(resp, "encoding"):
        resp.encoding = encoding
    return getattr(resp, "text", None)


def fetch_json(
    url: str,
    timeout: int = 12,
    headers: Optional[dict[str, str]] = None,
    params: Optional[dict[str, Any]] = None,
    session: Optional[requests.Session] = None,
    retries: int = 2,
) -> Optional[Any]:
    """Fetch JSON payload from a URL using `http_get` with standardized headers and status validation."""
    req_headers = dict(DEFAULT_BROWSER_HEADERS)
    req_headers["Accept"] = "application/json, text/plain, */*"
    if headers:
        req_headers.update(headers)
    resp = http_get(
        url,
        timeout=timeout,
        headers=req_headers,
        params=params,
        session=session,
        retries=retries,
    )
    if resp is None:
        return None
    raw_status = getattr(resp, "status_code", 200)
    status_code = raw_status if isinstance(raw_status, int) else 200
    if status_code >= 400:
        logger.debug("HTTP %s fetching JSON %s", status_code, url)
        return None
    try:
        return resp.json()
    except Exception as exc:
        logger.debug("Failed to decode JSON from %s: %s", url, exc)
        return None


def get_soup(
    url: str,
    timeout: int = 12,
    headers: Optional[dict[str, str]] = None,
) -> Optional[bs4.BeautifulSoup]:
    """Fetch HTML via urllib (supporting legacy SSL certs) and parse into BeautifulSoup."""
    req_headers = dict(DEFAULT_BROWSER_HEADERS)
    if headers:
        req_headers.update(headers)
    try:
        req = urllib.request.Request(url, headers=req_headers)
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return bs4.BeautifulSoup(raw, "html.parser")
    except urllib.error.HTTPError as e:
        if e.code == 403:
            logger.info("Portal protected by Bot Management (HTTP 403) at %s; skipping gracefully.", url)
        else:
            logger.warning("Failed to fetch portal %s: HTTP Error %s: %s", url, e.code, e.reason)
        return None
    except Exception as exc:
        logger.warning("Failed to fetch portal %s: %s", url, exc)
        return None
