"""
Shared HTTP client and BeautifulSoup helpers for Khulaasaa scrapers.
"""
from __future__ import annotations

import logging
import urllib.error
import urllib.request
from typing import Any, Optional

import bs4
import requests

from scrapers.common.headers import DEFAULT_BROWSER_HEADERS, get_unverified_ssl_context

logger = logging.getLogger(__name__)
SSL_CTX = get_unverified_ssl_context()


def fetch_text(
    url: str,
    timeout: int = 12,
    headers: Optional[dict[str, str]] = None,
    session: Optional[requests.Session] = None,
) -> Optional[str]:
    """Fetch raw text/HTML from a URL using requests with standardized headers."""
    req_headers = dict(DEFAULT_BROWSER_HEADERS)
    if headers:
        req_headers.update(headers)
    try:
        client = session or requests
        resp = client.get(url, headers=req_headers, timeout=timeout)
        if resp.status_code >= 400:
            logger.debug("HTTP %s fetching %s", resp.status_code, url)
            return None
        return resp.text
    except Exception as exc:
        logger.debug("Failed to fetch text from %s: %s", url, exc)
        return None


def fetch_json(
    url: str,
    timeout: int = 12,
    headers: Optional[dict[str, str]] = None,
    session: Optional[requests.Session] = None,
) -> Optional[Any]:
    """Fetch JSON payload from a URL using requests with standardized headers."""
    req_headers = dict(DEFAULT_BROWSER_HEADERS)
    req_headers["Accept"] = "application/json, text/plain, */*"
    if headers:
        req_headers.update(headers)
    try:
        client = session or requests
        resp = client.get(url, headers=req_headers, timeout=timeout)
        if resp.status_code >= 400:
            logger.debug("HTTP %s fetching JSON %s", resp.status_code, url)
            return None
        return resp.json()
    except Exception as exc:
        logger.debug("Failed to fetch JSON from %s: %s", url, exc)
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
