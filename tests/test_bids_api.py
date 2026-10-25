from fastapi.testclient import TestClient
import pytest

from main import app

client = TestClient(app)


def test_bids_page_render_live():
    response = client.get("/bids?source=live")
    assert response.status_code == 200
    assert "Bids &amp; Tenders" in response.text
    # Paywall removed, monetized by ads
    assert "Unlock Premium" not in response.text
    assert "Sponsored" in response.text
    assert "LIVE FEED" in response.text or "MOCK DATA" in response.text


def test_bids_page_unlocked_and_monetized_by_ads():
    response = client.get("/bids?source=mock")
    assert response.status_code == 200
    assert "Unlock Premium" not in response.text
    assert "locked-row" not in response.text
    assert "Sponsored" in response.text


def test_bids_filter_by_agency():
    target_agency = "Housing Development Corporation"
    response = client.get(f"/bids?agency={target_agency}&source=mock")
    assert response.status_code == 200
    assert "(filtered)" in response.text
    assert target_agency in response.text
    assert "Tourist Guesthouse in HA. Hoarafushi" not in response.text


def test_bids_filter_by_discipline():
    response = client.get("/bids?discipline=Construction&source=mock")
    assert response.status_code == 200
    assert "Upgrading of A.Dh Fenfushi Harbour" in response.text
    assert "Computer Systems &amp; Laptops" not in response.text


def test_bids_filter_by_type():
    response = client.get("/bids?type=Bid&source=mock")
    assert response.status_code == 200
    assert "Space Leasing for MGPL Shop Utilization" in response.text
    assert "Asphalt Repair" not in response.text


def test_bids_filter_combined():
    response = client.get(
        "/bids?agency=Housing+Development+Corporation&discipline=IT&type=Work&source=mock"
    )
    assert response.status_code == 200
    assert "Supply and Delivery of Computer Systems &amp; Laptops" in response.text
    assert "Boundary Fence for Telecom Towers" not in response.text


def test_bids_filter_no_match():
    response = client.get("/bids?agency=NonExistentAgency&source=mock")
    assert response.status_code == 200
    assert "No bids match this filter." in response.text


def test_bids_language_modes_and_milestones():
    # 1. English mode (default)
    res_en = client.get("/bids?lang=en&source=mock")
    assert res_en.status_code == 200
    assert "Submission Venue:" in res_en.text
    assert "Info Session:" in res_en.text

    # 2. Bilingual mode
    res_both = client.get("/bids?lang=both&source=mock")
    assert res_both.status_code == 200

    # 3. Dhivehi mode
    res_dv = client.get("/bids?lang=dv&source=mock")
    assert res_dv.status_code == 200


def test_telegram_api_subscribe_and_list(monkeypatch):
    from unittest.mock import MagicMock
    monkeypatch.setattr("routers.webhooks.send_telegram_message", MagicMock(return_value=(True, "ok")))
    payload = {
        "chat_id": "test_chat_888",
        "name": "Procurement Lead",
        "disciplines": ["Construction", "IT"],
        "keywords": ["harbour", "solar"],
    }
    res = client.post("/api/alerts/telegram/subscribe", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert "test_chat_888" in data["message"]

    # Verify via subscriber list endpoint
    sub_res = client.get("/api/alerts/telegram/subscribers")
    assert sub_res.status_code == 200
    subs = sub_res.json()
    chat_ids = [s["chat_id"] for s in subs]
    assert "test_chat_888" in chat_ids


def test_telegram_api_test_alert(monkeypatch):
    from unittest.mock import MagicMock
    mock_send = MagicMock(return_value=(True, "Alert sent successfully"))
    monkeypatch.setattr("main.send_telegram_message", mock_send)

    payload = {
        "chat_id": "test_chat_888",
        "bot_token": "mock_token_123",
    }
    res = client.post("/api/alerts/telegram/test", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    mock_send.assert_called_once()


def test_bids_prepare_redirects_if_no_id():
    res = client.get("/bids/prepare", follow_redirects=False)
    assert res.status_code in [302, 303, 307]
    assert "/bids" in res.headers["location"]


def test_bids_prepare_renders_with_valid_bid():
    # Use seeded notice 127322 (Ministry of Finance Harbour Upgrading)
    res = client.get("/bids/prepare?notice_id=127322")
    assert res.status_code == 200
    assert "Bid Preparation Suite" in res.text
    assert "hooks85" in res.text
    assert "Letters &amp; Correspondence" in res.text
    assert "Company Profile" in res.text
    assert "Proposal &amp; Methodology" in res.text
    assert "Quotation &amp; Pricing" in res.text
    assert "BOQ Spreadsheet" in res.text
    assert "Billing &amp; Invoices" in res.text
    assert "hooks85DownloadModal" in res.text


def test_bids_cards_include_prepare_links():
    res = client.get("/bids")
    assert res.status_code == 200
    assert "/bids/prepare?notice_id=" in res.text
    assert "Prepare Bid Package" in res.text



