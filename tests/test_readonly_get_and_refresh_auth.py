"""
Read-Only GET and Refresh Authorization Tests for Khulaasaa.
Validates:
1. Normal GET requests do not schedule scrapers or ingestion triggers (including cache-empty & cache-stale).
2. Unauthenticated visitors cannot force ingestion using ?refresh=1.
3. Authenticated editors/admins are permitted to force manual background sync.
Strictly under 500 lines. Zero emojis.
"""
from __future__ import annotations

import base64
from unittest.mock import patch
import pytest
from starlette.testclient import TestClient

from main import app
from core.deps import EDITOR_USER, EDITOR_PASS
import services.news_service as ns
import services.tenders_service as ts


@pytest.fixture
def client():
    return TestClient(app)


def test_normal_get_news_never_triggers_background_sync(client):
    """Verify normal GET / renders from persistence/cache without calling ingestion triggers."""
    with patch("services.news_service.trigger_news_background_sync") as mock_sync:
        # 1. Cache empty scenario
        ns._LIVE_NEWS_CACHE["data"] = []
        ns._LIVE_NEWS_CACHE["timestamp"] = 0.0

        res = client.get("/")
        assert res.status_code == 200
        assert mock_sync.call_count == 0

        # 2. Cache stale scenario
        ns._LIVE_NEWS_CACHE["data"] = [{"id": "stale-1", "headline": "Old News", "published_iso": "2026-01-01T00:00:00"}]
        ns._LIVE_NEWS_CACHE["timestamp"] = 1.0  # Very stale

        res_stale = client.get("/")
        assert res_stale.status_code == 200
        assert mock_sync.call_count == 0


def test_normal_get_bids_never_triggers_background_sync(client):
    """Verify normal GET /bids renders from persistence without calling ingestion triggers."""
    with patch("services.tenders_service.trigger_bids_background_sync") as mock_sync:
        res = client.get("/bids")
        assert res.status_code == 200
        assert mock_sync.call_count == 0


def test_get_live_bids_helper_is_strictly_readonly():
    """Verify tenders_service.get_live_bids() read helper does not trigger background sync."""
    with patch("services.tenders_service.trigger_bids_background_sync") as mock_sync:
        ts.get_live_bids(force_refresh=False)
        assert mock_sync.call_count == 0


def test_unauthenticated_refresh_param_ignored_on_bids(client):
    """Verify public visitor cannot force scraper sync via /bids?refresh=1."""
    with patch("routers.web_bids.trigger_bids_background_sync") as mock_sync:
        res = client.get("/bids?refresh=1")
        assert res.status_code == 200
        assert mock_sync.call_count == 0


def test_unauthenticated_refresh_param_ignored_on_news(client):
    """Verify public visitor cannot force scraper sync via /?refresh=1."""
    with patch("services.news_service.trigger_news_background_sync") as mock_sync:
        res = client.get("/?refresh=1")
        assert res.status_code == 200
        assert mock_sync.call_count == 0


def test_authenticated_editor_refresh_bids_triggers_sync(client):
    """Verify authenticated editor supplying HTTP Basic credentials can trigger /bids?refresh=1."""
    creds = base64.b64encode(f"{EDITOR_USER}:{EDITOR_PASS}".encode()).decode()
    headers = {"Authorization": f"Basic {creds}"}

    with patch("routers.web_bids.trigger_bids_background_sync") as mock_sync:
        res = client.get("/bids?refresh=1", headers=headers)
        assert res.status_code == 200
        mock_sync.assert_called_once_with(force=True)


def test_authenticated_editor_refresh_news_triggers_sync(client):
    """Verify authenticated editor supplying HTTP Basic credentials can trigger /?refresh=1."""
    creds = base64.b64encode(f"{EDITOR_USER}:{EDITOR_PASS}".encode()).decode()
    headers = {"Authorization": f"Basic {creds}"}

    with patch("services.news_service.trigger_news_background_sync") as mock_sync:
        res = client.get("/?refresh=1", headers=headers)
        assert res.status_code == 200
        mock_sync.assert_called_once_with(force=True)
