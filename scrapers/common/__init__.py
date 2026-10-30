"""
Shared scraper utilities, HTTP clients, headers, exceptions, and result contracts.
"""
from __future__ import annotations

from scrapers.common.exceptions import ScraperError, ScraperHTTPError, ScraperParseError
from scrapers.common.headers import (
    DEFAULT_BOT_HEADERS,
    DEFAULT_BROWSER_HEADERS,
    get_unverified_ssl_context,
)
from scrapers.common.http_client import SSL_CTX, fetch_json, fetch_text, get_soup
from scrapers.common.source_result import SourceResult

__all__ = [
    "DEFAULT_BOT_HEADERS",
    "DEFAULT_BROWSER_HEADERS",
    "SSL_CTX",
    "ScraperError",
    "ScraperHTTPError",
    "ScraperParseError",
    "SourceResult",
    "fetch_json",
    "fetch_text",
    "get_soup",
    "get_unverified_ssl_context",
]
