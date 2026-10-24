"""
Tests for Vanilla JS Partial Loading & Jinja2 Component Reuse (Zero Tailwind Runtime)
"""
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_no_tailwind_cdn_in_base_or_home():
    """Verify Tailwind Play CDN script has been completely eradicated."""
    res = client.get("/")
    assert res.status_code == 200
    assert "cdn.tailwindcss.com" not in res.text
    assert "/static/css/style.css" in res.text
    assert "/static/js/app.js" in res.text


def test_home_partial_stories_rendering():
    """Verify X-Requested-With returns only the stories component fragment, not the full <html> document."""
    res = client.get("/?tag=ras-male", headers={"X-Requested-With": "XMLHttpRequest"})
    assert res.status_code == 200
    assert "<!doctype html>" not in res.text.lower()
    assert "<html" not in res.text.lower()
    assert "<body" not in res.text.lower()
    assert "stories-stream" in res.text or "story-card" in res.text


def test_bids_partial_rendering():
    """Verify bids partial endpoint returns only the bids stream component."""
    res = client.get("/bids?source=mock", headers={"X-Requested-With": "XMLHttpRequest"})
    assert res.status_code == 200
    assert "<!doctype html>" not in res.text.lower()
    assert "<html" not in res.text.lower()
    assert "bids-stream" in res.text
    assert "bid-row" in res.text


def test_jobs_partial_rendering():
    """Verify jobs partial endpoint returns only the jobs stream component."""
    res = client.get("/jobs", headers={"X-Requested-With": "XMLHttpRequest"})
    assert res.status_code == 200
    assert "<!doctype html>" not in res.text.lower()
    assert "<html" not in res.text.lower()
    assert "jobs-stream" in res.text


def test_logo_sizing_and_overflow_protection_in_css():
    """Verify style.css enforces strict logo sizing and overflow prevention."""
    res = client.get("/static/css/style.css")
    assert res.status_code == 200
    assert "object-fit: contain" in res.text
    assert "overflow-wrap: break-word" in res.text
    assert "overflow: hidden" in res.text
    assert "max-width: 100%" in res.text
    assert "img[src*=\"/static/logos/\"]" in res.text or "img[src*=\"logos\"]" in res.text


def test_story_detail_logos_are_explicitly_sized():
    """Verify logos in story detail comparison cards have explicit width and height."""
    # Find a multi-source story id
    res_home = client.get("/")
    assert res_home.status_code == 200
    import re
    m = re.search(r'/story/([a-zA-Z0-9_\-]+)', res_home.text)
    if m:
        story_id = m.group(1)
        res_story = client.get(f"/story/{story_id}")
        assert res_story.status_code == 200
        # Check that logo images have height/width constraints
        assert "style=\"width:24px;height:24px" in res_story.text or "w-6 h-6" in res_story.text
