"""
Scraper subsystem exceptions.
"""
from __future__ import annotations


class ScraperError(Exception):
    """Base exception for scraper fetch or parse failures."""


class ScraperHTTPError(ScraperError):
    """Raised when an external source returns an HTTP or network error."""

    def __init__(self, url: str, status_code: int | None = None, message: str = "") -> None:
        self.url = url
        self.status_code = status_code
        super().__init__(f"HTTP error fetching {url} (status={status_code}): {message}")


class ScraperParseError(ScraperError):
    """Raised when an external payload cannot be parsed into expected records."""
