"""Static and runtime guards for the responsive filter dock, URL helpers, SVG dictionary, and estimator service."""
import re
from pathlib import Path
from fastapi.testclient import TestClient

from core.deps import build_filter_url
from core.icons import ICON_PATHS, svg_icon
from services.estimator_service import calculate_full_boq
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
    assert "function showConnectedState" not in index_js
    assert "function handleFeedSort" not in index_js
    assert "localStorage" not in index_js

    rentals_js = _read("static/js/rentals_filter.js")
    assert "toggleRentalFilterCollapse" not in rentals_js

    bids_js = _read("static/js/bids_filter.js")
    assert "sendSpecificTenderAlert" not in bids_js
    assert "localStorage" not in bids_js

    app_shell_js = _read("static/js/app_shell.js")
    assert "function toggleFilterDrawer()" in app_shell_js
    assert "function handleGlobalSearch(query)" in app_shell_js
    assert "localStorage.setItem" not in app_shell_js

    assert not (ROOT / "templates" / "subscription.html").exists()
    assert not (ROOT / "templates" / "_ad_rectangle.html").exists()


def test_ad_management_endpoints_require_editor_auth():
    client = TestClient(app)
    res_create = client.post("/api/ads", json={"campaign_name": "unauth-test", "sponsor_name": "Test", "text_html": "Hi"})
    assert res_create.status_code == 401
    res_bcast = client.post("/api/alerts/telegram/broadcast-ad", json={"text_html": "Hi"})
    assert res_bcast.status_code == 401


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


def test_zero_executable_inline_scripts_or_style_tags_in_templates():
    for tpl_path in (ROOT / "templates").rglob("*.html"):
        raw = tpl_path.read_text(encoding="utf-8")
        rel = tpl_path.relative_to(ROOT).as_posix()
        assert not re.search(r"<style\b", raw, re.I), f"{rel} contains an inline <style> tag"
        for match in re.finditer(r"<script\b([^>]*)>", raw, re.I):
            attrs = match.group(1) or ""
            is_external = bool(re.search(r"\bsrc\s*=", attrs, re.I))
            is_json_ld = bool(re.search(r'type\s*=\s*["\']application/(ld\+)?json["\']', attrs, re.I))
            assert is_external or is_json_ld, f"{rel} contains an inline executable <script> tag: <script{attrs}>"


def test_svg_icon_dictionary_synchronized_between_python_and_js():
    icons_js = _read("static/js/icons.js")
    for icon_name, svg_body in ICON_PATHS.items():
        assert svg_body in icons_js, f"Icon '{icon_name}' path missing from static/js/icons.js"
    rendered = str(svg_icon("chevron-down", "filter-chevron", 15, 15, 2))
    assert 'class="filter-chevron"' in rendered
    assert 'width="15"' in rendered
    assert ICON_PATHS["chevron-down"] in rendered


def test_estimator_business_service_and_api_endpoint():
    boq = calculate_full_boq({
        "conc_length": 20,
        "conc_width": 15,
        "conc_thick": 6,
        "conc_mix": "1:2:4",
        "block_length": 30,
        "block_height": 10,
        "block_size": "6in",
        "plaster_area": 600,
        "plaster_thick": 12,
        "paint_area": 800,
        "paint_type": "interior",
    })
    assert boq["concrete"]["cement_bags"] == 27
    assert boq["blocks"]["total_blocks"] == 355
    assert boq["paint"]["total_paint_litres"] == 24
    assert boq["summary"]["total_cement_bags"] > 30
    assert boq["summary"]["est_min_mvr"] > 0

    client = TestClient(app)
    res = client.post("/api/bids/estimate-boq", json={"conc_length": 10, "conc_width": 10, "conc_thick": 6})
    assert res.status_code == 200
    data = res.json()
    assert "concrete" in data and "summary" in data
    assert data["concrete"]["wet_volume_cuft"] == 50.0


def test_telegram_webapp_sdk_not_unconditionally_loaded_or_initialized_in_chrome():
    base_html = _read("templates/base.html")
    assert '<script src="https://telegram.org/js/telegram-web-app.js"' not in base_html

    app_shell_js = _read("static/js/app_shell.js")
    assert "typeof tg.initData !== 'string' || !tg.initData.trim()" in app_shell_js
    assert "function isLikelyTelegramWebView()" in app_shell_js
    assert "function initTelegramMiniApp(tg)" in app_shell_js
    assert "catch(e) {}" not in app_shell_js
    assert "catch (err) {}" not in app_shell_js

