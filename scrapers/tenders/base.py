"""
Common configurations, SSL context, and HTTP fetching helpers for procurement/bids scrapers.
"""
from __future__ import annotations

import logging
import ssl
from typing import Optional
import bs4
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

# SSL context preserved for backward compatibility
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def get_soup(url: str, timeout: int = 15) -> Optional[bs4.BeautifulSoup]:
    """Fetch URL using modern HTTP client and return BeautifulSoup object, or None on error."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
        if resp.status_code == 200:
            return bs4.BeautifulSoup(resp.text, "html.parser")
        logger.warning("Failed to fetch %s: HTTP %s", url, resp.status_code)
        return None
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None
