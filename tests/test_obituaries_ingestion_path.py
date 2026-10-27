"""
Obituaries Ingestion and Persistence Path Tests.
Verifies:
1. News and obituary splitting path cleanly separates Janaza notices from regular news.
2. Scraped obituaries are persisted to the database.
3. Persisted obituaries render in the obituaries feed.
Strictly under 500 lines. Zero emojis.
"""
from __future__ import annotations

import sqlite3
from unittest.mock import patch
import pytest
from starlette.testclient import TestClient

from main import app
from data.connection import get_db
from data.database import list_obituaries, upsert_scraped_obituary
from scrapers.news.engine import split_news_and_obituaries
from services.news_service import _run_news_sync


@pytest.fixture
def client():
    return TestClient(app)


def test_split_news_and_obituaries_separates_correctly():
    """Verify Dhivehi and English janaza keywords route notices to obituaries."""
    mixed_items = [
        {
            "id": "news-1",
            "headline": "Cabinet announces new fishery subsidy program",
            "summary": "Financial support allocated to south atoll fishermen.",
            "url": "https://sun.mv/news-1",
        },
        {
            "id": "obit-1",
            "headline": "އަލްމަރުހޫމް މުހައްމަދު ޒާހިރު ނިޔާވެއްޖެ",
            "summary": "ކަށުނަމާދު އޮންނާނީ މިއަދު އަސްރު ނަމާދަށްފަހު އާސަހަރާ މިސްކިތުގައެވެ.",
            "url": "https://sun.mv/obit-1",
        },
        {
            "id": "obit-2",
            "headline": "Janaza announcement for late Ahmed Manik",
            "summary": "Funeral prayer will be held at Hulhumale cemetery mosque after Maghrib.",
            "url": "https://dhauru.com/obit-2",
        },
    ]

    news, obits = split_news_and_obituaries(mixed_items)
    assert len(news) == 1
    assert news[0]["id"] == "news-1"
    assert len(obits) == 2
    assert {o["id"] for o in obits} == {"obit-1", "obit-2"}


def test_obituary_ingestion_persists_and_renders_in_feed(client):
    """Verify _run_news_sync persists obituary notices and they appear in list_obituaries and /obituaries."""
    raw_fixture = [
        {
            "id": "obit-test-unique-99",
            "headline": "މަރްހޫމާ ފާތިމަތު ނިޔާވެއްޖެ",
            "summary": "ކަށުނަމާދު އޮންނާނީ މިއަދު އިޝާ ނަމާދަށްފަހު މަސްޖިދުލް ތަޤުވާ ގައެވެ.",
            "url": "https://sun.mv/obit-unique-99",
            "source_key": "sun",
        }
    ]

    with patch("services.news_service.fetch_raw_news_articles", return_value=raw_fixture), \
         patch("services.news_service.dispatch_news_alerts"):
        _run_news_sync()

    # Verify persisted in database
    with get_db() as conn:
        obits = list_obituaries(conn, limit=50)
        found = any("ފާތިމަތު" in str(o.get("name_dv") or "") for o in obits)
        assert found, "Scraped obituary was not persisted into SQLite obituaries table"

    # Verify rendering on web UI
    res = client.get("/obituaries")
    assert res.status_code == 200
    assert "ފާތިމަތު" in res.text or "މަރްހޫމާ" in res.text
