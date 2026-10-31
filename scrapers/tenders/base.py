"""
Shared HTTP, SSL, and BeautifulSoup helpers for Maldivian procurement & tender scrapers.
Delegates to scrapers.common for shared headers, SSL context, and BeautifulSoup fetching.
"""
from __future__ import annotations

from scrapers.common.headers import DEFAULT_BROWSER_HEADERS as HEADERS
from scrapers.common.http_client import SSL_CTX, get_soup

__all__ = ["HEADERS", "SSL_CTX", "get_soup"]
