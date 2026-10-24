import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from main import app
from scrapers.news import fetch_telegram_posts

client = TestClient(app)
AUTH = ("editor", "changeme")


def test_admin_sources_page():
    resp = client.get("/admin/sources", auth=AUTH)
    assert resp.status_code == 200
    assert "Provider Sources &amp; Logos" in resp.text
    assert "Active Newsrooms" in resp.text
    assert "mihaaru" in resp.text
    assert "sun" in resp.text


def test_admin_sources_unauthenticated():
    resp = client.get("/admin/sources")
    assert resp.status_code == 401


def test_admin_upload_logo(tmp_path):
    # Test uploading a replacement logo for a source
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    files = {"logo_file": ("test_logo.png", fake_png, "image/png")}
    resp = client.post("/admin/sources/sun/upload-logo", files=files, auth=AUTH, follow_redirects=False)
    assert resp.status_code == 303
    assert "/admin/sources?msg=" in resp.headers["location"]


def test_mv_crisis_noise_and_ad_filter(monkeypatch):
    sample_html = """
    <div class="tgme_widget_message">
      <div class="tgme_widget_message_text">Got breaking news? Share it with us safely and instantly! @MessageMvCrisis</div>
    </div>
    <div class="tgme_widget_message">
      <div class="tgme_widget_message_text">Looks like it's gonna rain today in Male'. Vaarey veheyne.</div>
    </div>
    <div class="tgme_widget_message">
      <div class="tgme_widget_message_text">Special mattress discount 50% off! Call for orders now.</div>
    </div>
    <div class="tgme_widget_message">
      <div class="tgme_widget_message_text">🚨 Met office issues White Alert for heavy rain and strong winds across Kaafu Atoll.</div>
      <div class="tgme_widget_message_date"><time datetime="2026-10-16T06:00:00+00:00"></time></div>
    </div>
    """
    class MockResponse:
        status_code = 200
        text = sample_html

    monkeypatch.setattr("requests.get", lambda *args, **kwargs: MockResponse())
    posts = fetch_telegram_posts("mvcrisis", "https://t.me/s/mvcrisis")
    # Only the genuine Met alert should pass through; the tip promo, rain chatter, and mattress ad must be filtered!
    assert len(posts) == 1
    assert "White Alert" in posts[0]["headline"]
