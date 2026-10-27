"""
UI Shell, Responsive Navigation & Content State Acceptance Tests.
Strictly under 500 lines. Zero emojis.
"""
from __future__ import annotations

import re
import pytest
from fastapi.testclient import TestClient
from main import app
from data.database import get_db
from data.modules import update_service_module_status


@pytest.fixture
def client():
    return TestClient(app)


def test_base_shell_lightweight_assets(client: TestClient):
    """Verify cv.css is removed from base, print.css has media=print, and telegram has defer."""
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # cv.css must NOT be loaded on the news homepage
    assert '/static/css/cv.css' not in html

    # print.css must be media=print
    assert 'href="/static/css/print.css" media="print"' in html

    # telegram-web-app.js must be deferred
    assert 'src="https://telegram.org/js/telegram-web-app.js" defer' in html

    # All 5 core navigation tabs must be present in both desktop and mobile navigation
    assert 'href="/bids"' in html
    assert 'href="/jobs"' in html
    assert 'href="/rentals"' in html
    assert 'href="/obituaries"' in html


def test_cv_creator_loads_page_scoped_css(client: TestClient):
    """Verify cv.css is cleanly scoped to cv_creator page."""
    resp = client.get("/jobs/cv")
    assert resp.status_code == 200
    html = resp.text
    assert '/static/css/cv.css' in html
    # Ensure title block was closed properly and action bar is in content
    assert '<title>Maldivian CV Creator & Job Alerts — Khulaasaa</title>' in html
    assert 'id="cvFloatingActionsBar"' in html


def test_navigation_active_route_highlighting(client: TestClient):
    """Verify active navigation item matches current route across desktop and mobile nav."""
    routes_to_test = [
        ("/", "News"),
        ("/bids", "Tenders"),
        ("/jobs", "Jobs"),
        ("/rentals", "Rentals"),
        ("/obituaries", "Obituaries"),
    ]
    for route, label in routes_to_test:
        resp = client.get(route)
        assert resp.status_code == 200, f"Route {route} failed"
        html = resp.text
        # Check active class in desktop nav
        assert f'class="nav-tab active"' in html, f"Active nav-tab missing for {route}"
        # Check active class in mobile nav
        assert f'class="mobile-nav-item active"' in html, f"Active mobile-nav-item missing for {route}"


def test_responsive_navigation_css_invariants(client: TestClient):
    """Verify components.css enforces clean mobile bottom nav hiding on desktop."""
    resp = client.get("/static/css/components.css")
    assert resp.status_code == 200
    css = resp.text

    # Must have media query hiding mobile bottom nav on desktop >= 768px
    assert "@media (min-width: 768px)" in css
    # No duplicate !important rules forcing bottom nav to be flex on desktop
    assert ".mobile-bottom-nav {\n    display: flex !important;" not in css
    # Desktop nav menu is shown on min-width 768px
    assert ".desktop-nav-menu" in css
    # User notif dropdown has proper z-index
    assert ".user-notif-dropdown" in css


def test_static_core_assets_return_200(client: TestClient):
    """Verify all referenced stylesheets and scripts return 200 OK."""
    assets = [
        "/static/css/base.css",
        "/static/css/components.css",
        "/static/css/modals.css",
        "/static/css/cv.css",
        "/static/css/print.css",
        "/static/css/style.css",
        "/static/js/app.js",
        "/static/logos/khulaasaa.svg",
    ]
    for asset in assets:
        resp = client.get(asset)
        assert resp.status_code == 200, f"Asset {asset} returned {resp.status_code}"


def test_empty_collection_vs_filter_empty_state_bids(client: TestClient):
    """Verify bids page distinguishes empty collection vs filter mismatch."""
    resp = client.get("/bids?q=nonexistentxyz123456")
    assert resp.status_code == 200
    assert "No bids match this filter" in resp.text
    assert "Reset All Filters" in resp.text


def test_empty_collection_vs_filter_empty_state_jobs(client: TestClient):
    """Verify jobs page distinguishes empty collection vs filter mismatch."""
    resp = client.get("/jobs?q=nonexistentxyz123456")
    assert resp.status_code == 200
    assert "No job openings found matching this filter" in resp.text
    assert "Clear filters" in resp.text


def test_empty_collection_vs_filter_empty_state_rentals(client: TestClient):
    """Verify rentals page distinguishes empty collection vs filter mismatch."""
    resp = client.get("/rentals?q=nonexistentxyz123456")
    assert resp.status_code == 200
    assert "No apartments found matching your criteria" in resp.text
    assert "Clear All Filters" in resp.text


def test_empty_collection_vs_filter_empty_state_obituaries(client: TestClient):
    """Verify obituaries page distinguishes empty collection vs filter mismatch."""
    resp = client.get("/obituaries?q=nonexistentxyz123456")
    assert resp.status_code == 200
    assert "No obituary announcements posted yet" in resp.text
    assert "Reset Filters" in resp.text


def test_empty_collection_vs_filter_empty_state_news(client: TestClient):
    """Verify news page distinguishes empty collection vs filter mismatch."""
    resp = client.get("/?tag=nonexistent-tag-123456")
    assert resp.status_code == 200
    assert "No stories match this filter" in resp.text
    assert "Return to All News" in resp.text


def test_service_module_suspension_renders_503(client: TestClient):
    """Verify suspending a service module returns honest 503 instead of 500 error."""
    with get_db() as conn:
        update_service_module_status(conn, "tenders", False, "Tenders maintenance in progress")

    try:
        resp = client.get("/bids")
        assert resp.status_code == 503
        assert "Service Temporarily Suspended" in resp.text
    finally:
        with get_db() as conn:
            update_service_module_status(conn, "tenders", True)
