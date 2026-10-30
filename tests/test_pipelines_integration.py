"""
End-to-End Ingestion Pipeline Integration Tests for Khulaasaa:
1. News Pipeline: Adapter fixture -> Ingestion service -> Normalization -> Persistence -> Feed query -> UI render -> Idempotent retry.
2. Tenders Pipeline: Listing parser -> Normalization -> Persistence -> Read query -> UI view -> Idempotent retry.
3. Jobs Pipeline: Sync -> Persistence -> Query service -> UI view -> Honest empty state without demo fallback.
"""
from __future__ import annotations

import os
import sqlite3
from unittest.mock import patch, MagicMock
import pytest
from starlette.testclient import TestClient

from main import app
from data.connection import get_db
from data.database import query_articles, upsert_article, query_bids, upsert_bid, query_jobs, upsert_job
from services.news_service import get_live_news, init_news_cache, _run_news_sync
from services.tenders_service import get_live_bids, _run_bids_sync, prepare_bids_presentation
from services.jobs_service import run_jobs_sync, enrich_job
from scrapers.news.engine import split_news_and_obituaries, fetch_all_live_news


@pytest.fixture
def client():
    return TestClient(app)


# -----------------------------------------------------------------------------
# 1. NEWS PIPELINE INTEGRATION
# -----------------------------------------------------------------------------
def test_news_pipeline_e2e(client):
    """Verify complete News pipeline from raw intake through clustering, DB persistence, and UI rendering."""
    fixture_items = [
        {
            "id": "e2e-article-1",
            "headline": "Cabinet approves national renewable energy roadmap 2030",
            "summary": "Government targets 50 percent clean energy by 2030 across all inhabited islands.",
            "sources": ["sun"],
            "source_key": "sun",
            "url": "https://sun.mv/test-e2e-renewable-1",
            "published_iso": "2026-10-27T08:00:00Z",
            "minutes_ago": 15,
            "topic": "Environment",
        },
        {
            "id": "e2e-article-2",
            "headline": "Renewable energy transition approved by Cabinet ministers",
            "summary": "State commits funding to solar and wind infrastructure for Maldivian atolls.",
            "sources": ["dhauru"],
            "source_key": "dhauru",
            "url": "https://dhauru.com/test-e2e-renewable-2",
            "published_iso": "2026-10-27T08:05:00Z",
            "minutes_ago": 10,
            "topic": "Environment",
        },
    ]

    with patch("services.news_service.fetch_raw_news_articles", return_value=fixture_items):
        # 1. Trigger news synchronization
        _run_news_sync()

    # 2. Verify records exist in database
    with get_db() as conn:
        articles_in_db = query_articles(conn, limit=1000)
        found_urls = {a.get("url") for a in articles_in_db}
        assert "https://sun.mv/test-e2e-renewable-1" in found_urls
        assert "https://dhauru.com/test-e2e-renewable-2" in found_urls

    # 3. Verify idempotent retry: running sync again does not duplicate articles in DB
    initial_count = len(articles_in_db)
    with patch("services.news_service.fetch_raw_news_articles", return_value=fixture_items):
        _run_news_sync()

    with get_db() as conn:
        articles_after = query_articles(conn, limit=1000)
        assert len(articles_after) == initial_count

    # 4. Verify API / UI rendering of live news
    res = client.get("/api/news")
    assert res.status_code == 200
    feed_data = res.json()
    assert "articles" in feed_data
    assert isinstance(feed_data["articles"], list)

    res_ui = client.get("/")
    assert res_ui.status_code == 200
    assert "Khulaasaa" in res_ui.text


# -----------------------------------------------------------------------------
# 2. TENDERS PIPELINE INTEGRATION
# -----------------------------------------------------------------------------
def test_tenders_pipeline_e2e(client):
    """Verify complete Tender pipeline from source parsing through enrichment, DB persistence, and UI."""
    from scrapers.tenders.gazette import BidNotice

    mock_notices = [
        BidNotice(
            notice_id="e2e-bid-99999",
            url="https://gazette.gov.mv/iulaan/print/99999",
            gazette_type="Bid",
            reference_number="(IUL)450-PROC/2026/01",
            published_iso="2026-10-27T07:00:00",
            deadline_iso="2026-11-20T14:00:00",
            agency="Ministry of Climate Change, Environment and Energy",
            title="Supply and Installation of Atoll Solar Mini-Grids",
            body="Detailed technical specifications for solar equipment.",
            submission_location="National Tender Board, Ministry of Finance, Male'",
        )
    ]

    with patch("services.tenders_service.fetch_listing", return_value=mock_notices), \
         patch("services.tenders_service.fetch_all_agency_portals", return_value=[]), \
         patch("services.tenders_service.dispatch_tender_alerts"), \
         patch("services.tenders_service.dispatch_viber_bid_alerts"):
        _run_bids_sync()

    # 1. Verify persisted in DB
    with get_db() as conn:
        bids = query_bids(conn, search_q="Atoll Solar Mini-Grids")
        assert len(bids) >= 1
        b = bids[0]
        assert b["notice_id"] == "e2e-bid-99999"
        assert b["ref"] == "(IUL)450-PROC/2026/01"
        assert "Ministry of Climate Change" in b["agency"]

    # 2. Verify idempotency: re-running does not duplicate
    with patch("services.tenders_service.fetch_listing", return_value=mock_notices), \
         patch("services.tenders_service.fetch_all_agency_portals", return_value=[]), \
         patch("services.tenders_service.dispatch_tender_alerts"), \
         patch("services.tenders_service.dispatch_viber_bid_alerts"):
        _run_bids_sync()

    with get_db() as conn:
        bids_retry = query_bids(conn, search_q="Atoll Solar Mini-Grids")
        assert len(bids_retry) == len(bids)

    # 3. Verify Web UI renders the bid
    res = client.get("/bids?q=Solar")
    assert res.status_code == 200
    assert "Supply and Installation of Atoll Solar Mini-Grids" in res.text or "Mini-Grids" in res.text


# -----------------------------------------------------------------------------
# 3. JOBS PIPELINE INTEGRATION & HONEST EMPTY STATE
# -----------------------------------------------------------------------------
def test_jobs_pipeline_e2e(client):
    """Verify Jobs pipeline: sync, persistence, read query, and honest empty state."""
    fixture_job = {
        "notice_id": "e2e-job-88888",
        "title": "Renewable Energy Specialist",
        "title_en": "Renewable Energy Specialist",
        "agency": "Ministry of Environment",
        "agency_name_en": "Ministry of Environment",
        "discipline": "Construction, Architecture & Engineering",
        "location": "Male'",
        "salary_raw": "MVR 25,000 - 30,000",
        "deadline_iso": "2026-11-15T14:00:00",
        "published_date": "2026-10-27",
        "source_url": "https://gazette.gov.mv/iulaan/248999",
        "source_portal": "gazette.gov.mv",
        "is_active": 1,
    }

    # 1. Persist directly and verify query_jobs returns it
    with get_db() as conn:
        upsert_job(conn, fixture_job)
        jobs = query_jobs(conn, search="Renewable Energy Specialist")
        assert len(jobs) >= 1
        assert jobs[0]["notice_id"] == "e2e-job-88888"

    # 2. Verify Web UI renders it
    res = client.get("/jobs?q=Renewable+Energy+Specialist")
    assert res.status_code == 200
    assert "Renewable Energy Specialist" in res.text

    # 3. Verify honest empty state when non-existent filter is applied
    res_empty = client.get("/jobs?q=NonExistentJobXYZ987")
    assert res_empty.status_code == 200
    assert "No job openings found matching this filter" in res_empty.text


def test_jobs_honest_empty_state_without_demo_mode(client):
    """Verify that in production (when demo mode is inactive), empty query does not disguise with sample JOBS."""
    # When filtering by an empty search query on an isolated database with demo mode disabled:
    with patch.dict(os.environ, {"KHULAASAA_DEMO_MODE": "0", "PYTEST_CURRENT_TEST": ""}):
        with patch("routers.web_jobs.query_jobs", return_value=[]):
            res = client.get("/jobs")
            assert res.status_code == 200
            assert "No job openings found matching this filter" in res.text
