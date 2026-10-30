"""Static and runtime guards for the responsive filter dock, URL helpers, and Janaza icon."""
from pathlib import Path
from fastapi.testclient import TestClient

from core.deps import build_filter_url
from main import app

ROOT = Path(__file__).resolve().parent.parent
MOON_PATH = "M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_filter_toolbar_surface_defined_once():
    css = _read("static/css/components.css")
    assert css.count("\n.filter-toolbar {") == 1


def test_shared_filter_dock_macro_used_across_all_five_pages():
    dock_macro = _read("templates/components/filter_dock.html")
    assert dock_macro.count('id="pageFilterToolbar"') == 1
    assert dock_macro.count('id="filterDrawer"') == 1
    assert 'aria-expanded="false"' in dock_macro

    for tpl in ("index.html", "bids.html", "jobs.html", "rentals.html", "obituaries.html"):
        raw = _read(f"templates/{tpl}")
        assert 'from "components/filter_dock.html" import render_filter_dock' in raw
        assert raw.count("render_filter_dock(") == 1
        assert 'id="pageFilterToolbar"' not in raw


def test_no_duplicate_or_legacy_filter_js_handlers():
    index_js = _read("static/js/index_feed.js")
    assert "function toggleFilterDrawer" not in index_js
    assert "function isMobileDevice" not in index_js

    rentals_js = _read("static/js/rentals_filter.js")
    assert "toggleRentalFilterCollapse" not in rentals_js

    app_shell_js = _read("static/js/app_shell.js")
    assert "function toggleFilterDrawer()" in app_shell_js


def test_janaza_mobile_nav_uses_crescent_not_plus():
    html = _read("templates/base.html")
    start = html.index('href="/obituaries" class="mobile-nav-item')
    block = html[start:start + 600]
    assert MOON_PATH in block
    assert MOON_PATH in _read("static/js/icons.js")
    assert "M12 4v16m-6-10h12" not in block


def test_notices_and_rentals_keep_js_hooks():
    obits = _read("templates/obituaries.html")
    for hook in ("btn-reg-all", "btn-reg-south", "atollSelect", "obituarySearch"):
        assert obits.count(f'id="{hook}"') == 1

    rentals = _read("templates/rentals.html")
    assert rentals.count("rentals/feature_legend.html") == 1
    for hook in ("filterAtoll", "filterIsland", "filterWard", "filterCustomRooms", "budgetRangeSlider"):
        assert rentals.count(f'id="{hook}"') == 1


def test_theme_root_tokens_defined_once():
    base = _read("static/css/base.css")
    assert base.count("\n:root {") + (1 if base.startswith(":root {") else 0) == 1
    for token in ("--color-accent", "--dock-shadow", "--dock-row-tint", "--surface-white"):
        assert token + ":" in base
    css = _read("static/css/components.css")
    dock = css[css.index("Khulaasaa responsive filter dock"):]
    assert "rgba(16, 34, 46" not in dock


def test_build_filter_url_and_query_parameter_preservation():
    assert build_filter_url("/", tag="ras-male", topic=None, sort=None) == "/?tag=ras-male"
    assert build_filter_url("/bids", discipline="IT", q="solar", cross_listed="1") == "/bids?discipline=IT&q=solar&cross_listed=1"

    client = TestClient(app)

    # News query preservation across tag, topic, and sort
    news_res = client.get("/?tag=ras-male&topic=politics&sort=urgent")
    assert news_res.status_code == 200
    assert 'href="/?sort=outlets&amp;tag=ras-male&amp;topic=politics"' in news_res.text
    assert 'value="/?tag=sultan-park&amp;topic=politics&amp;sort=urgent"' in news_res.text

    # Tenders query preservation across discipline, q, portal, cross_listed
    bids_res = client.get("/bids?discipline=IT&q=solar&portal=gazette.gov.mv&cross_listed=1")
    assert bids_res.status_code == 200
    assert 'href="/bids?discipline=Medical&amp;q=solar&amp;portal=gazette.gov.mv&amp;cross_listed=1"' in bids_res.text
    assert 'href="/bids?cross_listed=0&amp;discipline=IT&amp;q=solar&amp;portal=gazette.gov.mv"' in bids_res.text

    # Jobs query preservation across discipline and q
    jobs_res = client.get("/jobs?discipline=IT&q=engineer")
    assert jobs_res.status_code == 200
    assert 'href="/jobs?q=engineer"' in jobs_res.text


def test_all_primary_routes_render_single_filter_dock_and_preserve_shell():
    client = TestClient(app)
    for route in ("/", "/bids", "/jobs", "/rentals", "/obituaries"):
        res = client.get(route)
        assert res.status_code == 200, f"{route} returned {res.status_code}"
        assert res.text.count('id="pageFilterToolbar"') == 1, f"{route} missing single #pageFilterToolbar"
        assert 'id="userAvatarMenuContainer"' in res.text
        assert 'id="headerTelegramBtn"' in res.text
        assert 'id="headerViberBtn"' in res.text
