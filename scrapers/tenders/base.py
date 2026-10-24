"""
Common configurations, SSL context, and HTTP fetching helpers for procurement/bids scrapers.
"""
from __future__ import annotations

import logging
import ssl
import urllib.request
from typing import Optional
import bs4

logger = logging.getLogger(__name__)

# SSL context that allows connecting to various government and SOE servers
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def get_soup(url: str, timeout: int = 10) -> Optional[bs4.BeautifulSoup]:
    """Fetch URL and return BeautifulSoup object, or None if network/server error."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX).read().decode("utf-8", errors="ignore")
        return bs4.BeautifulSoup(html, "html.parser")
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None
