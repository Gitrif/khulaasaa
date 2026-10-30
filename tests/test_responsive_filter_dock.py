"""Static guards for the responsive filter dock and Janaza icon."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MOON_PATH = "M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_filter_toolbar_surface_defined_once():
    css = _read("static/css/components.css")
    assert css.count("\n.filter-toolbar {") == 1


def test_news_filter_markup_appears_once_and_keeps_query_params():
    html = _read("templates/index.html")
    assert html.count('id="pageFilterToolbar"') == 1
    assert html.count('id="filterDrawer"') == 1
    assert "/?tag=" in html and "/?topic=" in html
    assert 'aria-expanded="false"' in html


def test_janaza_mobile_nav_uses_crescent_not_plus():
    html = _read("templates/base.html")
    start = html.index('href="/obituaries" class="mobile-nav-item')
    block = html[start:start + 600]
    assert MOON_PATH in block
    assert MOON_PATH in _read("static/js/icons.js")  # one shared definition
    assert "M12 4v16m-6-10h12" not in block


def test_notices_filters_use_shared_dock_and_keep_js_hooks():
    html = _read("templates/obituaries.html")
    assert html.count('id="pageFilterToolbar"') == 1
    for hook in ("btn-reg-all", "btn-reg-south", "atollSelect", "obituarySearch"):
        assert html.count(f'id="{hook}"') == 1


def test_theme_root_tokens_defined_once():
    base = _read("static/css/base.css")
    assert base.count("\n:root {") + (1 if base.startswith(":root {") else 0) == 1
    for token in ("--color-accent", "--dock-shadow", "--dock-row-tint", "--surface-white"):
        assert token + ":" in base
    css = _read("static/css/components.css")
    dock = css[css.index("Khulaasaa responsive filter dock"):]
    assert "rgba(16, 34, 46" not in dock


def test_bids_jobs_rentals_use_single_shared_filter_dock():
    bids = _read("templates/bids.html")
    assert bids.count('id="pageFilterToolbar"') == 1
    assert "openAdvancedFilterModal()" in bids
    assert "?discipline=" in bids and "cross_listed=" in bids

    jobs = _read("templates/jobs.html")
    assert jobs.count('id="pageFilterToolbar"') == 1
    assert "/jobs?discipline=" in jobs and "/jobs/cv" in jobs

    rentals = _read("templates/rentals.html")
    assert rentals.count('id="pageFilterToolbar"') == 1
    assert rentals.count('id="filterDrawer"') == 1
    assert rentals.count('rentals/feature_legend.html') == 1
    for hook in ("filterAtoll", "filterIsland", "filterWard", "filterCustomRooms", "budgetRangeSlider"):
        assert rentals.count(f'id="{hook}"') == 1


def test_all_primary_routes_render_single_filter_dock():
    from fastapi.testclient import TestClient
    from main import app

    client = TestClient(app)
    for route in ("/", "/bids", "/jobs", "/rentals", "/obituaries"):
        res = client.get(route)
        assert res.status_code == 200, f"{route} returned {res.status_code}"
        assert res.text.count('id="pageFilterToolbar"') == 1, f"{route} missing single #pageFilterToolbar"
