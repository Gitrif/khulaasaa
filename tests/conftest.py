import os
from pathlib import Path
import pytest
from scrapers.dedupe import SourceRecord
from scrapers.tenders.gazette import BidNotice

FIXTURES_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture(autouse=True)
def isolate_hooks85_gateway_during_tests(monkeypatch, request):
    """Prevent tests from hitting a live local hooks85 Gateway unless testing hooks85_service directly."""
    if "test_hooks85_gateway_integration" in request.node.nodeid:
        return
    monkeypatch.setattr("routers.api_auth.register_via_hooks85", lambda *a, **kw: None)
    monkeypatch.setattr("routers.api_auth.login_via_hooks85", lambda *a, **kw: None)


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR

@pytest.fixture
def en_notice_html() -> str:
    path = FIXTURES_DIR / "gazette_notice_166396_en.html"
    return path.read_text(encoding="utf-8")

@pytest.fixture
def dv_notice_html() -> str:
    path = FIXTURES_DIR / "gazette_notice_417326_dv.html"
    return path.read_text(encoding="utf-8")

@pytest.fixture
def listing_html() -> str:
    path = FIXTURES_DIR / "gazette_listing.html"
    return path.read_text(encoding="utf-8")

@pytest.fixture
def sample_gazette_notice() -> BidNotice:
    return BidNotice(
        notice_id="166396",
        url="https://gazette.gov.mv/iulaan/print/166396",
        gazette_type="Work",
        reference_number="HDC (161)-PWM/IU/2021/520",
        published_iso="2021-10-11T21:45:00",
        deadline_iso="2021-11-02T11:00:00",
        agency="Housing Development Corporation",
        title="Hulhumalé Phase I Major Roads – Road Markings & Asphalt Repair",
        body="Invitation of Tender No: HDC (161)-PWM/IU/2021/520",
        document_urls=["https://hdc.com.mv/announcements/bids/"],
    )

@pytest.fixture
def sample_hdc_source_record() -> SourceRecord:
    return SourceRecord(
        source_name="hdc.com.mv",
        source_url="https://hdc.com.mv/announcements/bids/road-markings",
        reference_number="HDC(161)-PWM/IU/2021/520",
        agency="Housing Development Corporation",
        title="Hulhumale Phase I Major Roads Road Markings and Asphalt Repair",
        published_iso="2021-10-12T09:00:00",
        deadline_iso="2021-11-02T11:00:00",
        document_urls=[
            "https://hdc.com.mv/files/tender-docs.zip",
            "https://hdc.com.mv/announcements/bids/",
        ],
    )
