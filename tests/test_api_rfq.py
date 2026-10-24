"""
Tests for ERP & RFQ API Gateway.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from main import app
from data.database import init_db, get_db, upsert_bid


@pytest.fixture
def rfq_client(tmp_path: Path, monkeypatch):
    from datetime import datetime, timezone, timedelta
    future_date_1 = (datetime.now(timezone.utc) + timedelta(days=15)).strftime("%Y-%m-%dT14:00:00")
    future_date_2 = (datetime.now(timezone.utc) + timedelta(days=20)).strftime("%Y-%m-%dT14:00:00")

    test_db = tmp_path / "test_rfq.db"
    init_db(test_db, seed_bids=False)
    monkeypatch.setenv("KHULAASAA_DB_PATH", str(test_db))

    with get_db(test_db) as conn:
        upsert_bid(conn, {
            "notice_id": "417569",
            "reference_number": "MWSC-L/3/ADV/2026/95",
            "agency": "Male' Water and Sewerage Company Pvt Ltd",
            "title": "Supply and Delivery of HDPE Pipes and Electrofusion Fittings",
            "discipline": "Construction",
            "procurement_nature": "Supply",
            "gazette_type": "Bid",
            "published_date": "2026-10-15T10:00:00",
            "submission_date": future_date_1,
            "source_url": "https://gazette.gov.mv/iulaan/417569",
            "submission_location": "MWSC Customer Building 3rd Floor / Procurement Dept",
            "info_date": "2026-10-20T11:00:00",
            "info_location": "MWSC Online Vendor Portal",
            "document_urls": ["https://mwsc.com.mv/docs/specs.pdf"],
        })
        upsert_bid(conn, {
            "notice_id": "417560",
            "reference_number": "(IUL)503-FS/1/2026/33",
            "agency": "Maldives Police Service",
            "title": "Provision of Patrol Boat Engine Overhaul Services",
            "discipline": "Logistics & Transport",
            "procurement_nature": "Service",
            "gazette_type": "Tender",
            "published_date": "2026-10-15T09:30:00",
            "submission_date": future_date_2,
            "source_url": "https://gazette.gov.mv/iulaan/417560",
            "submission_location": "Police HQ Reception, Male'",
            "info_date": None,
            "info_location": None,
            "document_urls": [],
        })

    return TestClient(app)


def test_list_rfqs_standard(rfq_client):
    resp = rfq_client.get("/api/v1/erp/rfqs")
    assert resp.status_code == 200
    data = resp.json()

    assert "meta" in data
    assert "data" in data
    assert data["meta"]["count"] >= 2

    first = data["data"][0]
    assert "rfq_id" in first
    assert "reference_number" in first
    assert "opportunity_type" in first
    assert "buyer" in first
    assert "dates" in first
    assert "logistics" in first


def test_list_rfqs_filter_by_discipline_and_nature(rfq_client):
    # Filter by Supply nature
    resp = rfq_client.get("/api/v1/erp/rfqs?nature=Supply")
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) == 1
    assert items[0]["opportunity_type"] == "Supply"
    assert items[0]["trade_category"] == "Construction"

    # Filter by Service nature
    resp = rfq_client.get("/api/v1/erp/rfqs?nature=Service")
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) == 1
    assert items[0]["opportunity_type"] == "Service"
    assert items[0]["trade_category"] == "Logistics & Transport"


def test_list_rfqs_odoo_format(rfq_client):
    resp = rfq_client.get("/api/v1/erp/rfqs?format=odoo")
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) >= 2

    odoo_rfq = items[0]
    assert "name" in odoo_rfq
    assert "partner_id" in odoo_rfq
    assert "date_order" in odoo_rfq
    assert "date_planned" in odoo_rfq
    assert "notes" in odoo_rfq


def test_list_rfqs_erpnext_format(rfq_client):
    resp = rfq_client.get("/api/v1/erp/rfqs?format=erpnext")
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) >= 2

    erpnext_rfq = items[0]
    assert erpnext_rfq["doctype"] == "Request for Quotation"
    assert "supplier" in erpnext_rfq
    assert "valid_till" in erpnext_rfq
    assert "status" in erpnext_rfq


def test_get_rfq_detail_found(rfq_client):
    resp = rfq_client.get("/api/v1/erp/rfqs/417569")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    data = body["data"]
    assert data["rfq_id"] == "RFQ-417569"
    assert data["reference_number"] == "MWSC-L/3/ADV/2026/95"
    assert data["buyer"]["name"] == "Male' Water and Sewerage Company Pvt Ltd"
    assert len(data["documents"]) == 1
    assert "specs.pdf" in data["documents"][0]["url"]


def test_get_rfq_detail_not_found(rfq_client):
    resp = rfq_client.get("/api/v1/erp/rfqs/nonexistent-999999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_simulate_webhook_dispatch(rfq_client, monkeypatch):
    # Mock httpx.post
    class MockResponse:
        status_code = 200

    def mock_post(url, *args, **kwargs):
        return MockResponse()

    import httpx
    monkeypatch.setattr(httpx, "post", mock_post)


    payload = {
        "webhook_url": "https://erp.mycompany.mv/api/v1/webhooks/rfq",
        "event_type": "rfq.published",
        "notice_id": "417569",
    }
    resp = rfq_client.post("/api/v1/erp/webhooks/simulate", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["webhook_status_code"] == 200
    assert "dispatched_payload" in body
    assert body["dispatched_payload"]["event"] == "rfq.published"
    assert body["dispatched_payload"]["rfq"]["rfq_id"] == "RFQ-417569"
