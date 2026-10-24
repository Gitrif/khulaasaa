import json
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch
import bs4

from scrapers.dedupe import SourceRecord
from scrapers.agencies import (
    parse_finance_tenders,
    parse_tourism_tenders,
    parse_mwsc_tenders,
    parse_stelco_tenders,
    parse_sto_tenders,
    fetch_all_agency_portals,
)
from data.database import (
    init_db,
    get_db,
    upsert_bid,
    query_bids,
    get_agency_portal_statistics,
)


@pytest.fixture
def temp_db(tmp_path: Path):
    db_file = tmp_path / "test_agencies.db"
    init_db(db_file)
    return db_file


# ---------------------------------------------------------------------
# 1. Ministry of Finance parser
# ---------------------------------------------------------------------
def test_parse_finance_tenders():
    html = """
    <table>
      <thead>
        <tr>
          <th>Project Type</th><th>Invitation Ref No</th><th>Procurement No</th>
          <th>Procurement Name</th><th>Project Sector</th><th>Agency</th>
          <th>Procurement Approach</th><th>Published Date</th><th>Submission Date</th><th>Status</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Works</td>
          <td>(IUL)13-K/13/2026/202</td>
          <td>TES/2026/W-025</td>
          <td>Construction of 30 Bed Hospital at N. Velidhoo</td>
          <td>Health</td>
          <td>Ministry of Health</td>
          <td>National Competitive Bidding</td>
          <td>10/10/2026</td>
          <td>25/10/2026 13:00</td>
          <td>Open</td>
        </tr>
        <tr>
          <td>Goods</td>
          <td>-</td>
          <td>TES/2026/G-012</td>
          <td>Supply of Laboratory Equipment</td>
          <td>Education</td>
          <td>Maldives National University</td>
          <td>National Competitive Bidding</td>
          <td>12/10/2026</td>
          <td>30/10/2026</td>
          <td>Open</td>
        </tr>
      </tbody>
    </table>
    """
    records = parse_finance_tenders(html)
    assert len(records) == 2

    # First record uses invitation ref
    r1 = records[0]
    assert r1.source_name == "finance.gov.mv"
    assert r1.reference_number == "(IUL)13-K/13/2026/202"
    assert r1.agency == "Ministry of Health"
    assert "Velidhoo" in r1.title
    assert r1.published_iso == "2026-10-10"
    assert r1.deadline_iso == "2026-10-25T13:00:00"
    assert "National Tender Board" in r1.submission_location

    # Second record falls back to procurement no TES/2026/G-012 when ref is "-"
    r2 = records[1]
    assert r2.reference_number == "TES/2026/G-012"
    assert r2.agency == "Maldives National University"
    assert r2.published_iso == "2026-10-12"
    assert r2.deadline_iso == "2026-10-30T10:00:00"


def test_parse_finance_empty_table():
    assert parse_finance_tenders("<div>No tables here</div>") == []


# ---------------------------------------------------------------------
# 2. Ministry of Tourism parser
# ---------------------------------------------------------------------
def test_parse_tourism_tenders():
    html = """
    <table>
      <tr><th>Date</th><th>Announcement</th><th>File</th></tr>
      <tr>
        <td>05 Oct 2026</td>
        <td>Development of Eco-Tourism Facility in Haa Alif Atoll - (IUL)88-PS/88/2026/140</td>
        <td><a href="/docs/eco.pdf">Download</a></td>
      </tr>
      <tr>
        <td>02 Oct 2026</td>
        <td>Nothing to view currently</td>
        <td>-</td>
      </tr>
    </table>
    """
    records = parse_tourism_tenders(html)
    assert len(records) == 1
    r = records[0]
    assert r.source_name == "tourism.gov.mv"
    assert r.reference_number == "(IUL)88-PS/88/2026/140"
    assert r.agency == "Ministry of Tourism"
    assert "Development of Eco-Tourism Facility" in r.title
    assert "(IUL)" not in r.title
    assert "Velaanaage" in r.submission_location


# ---------------------------------------------------------------------
# 3. MWSC parser
# ---------------------------------------------------------------------
def test_parse_mwsc_tenders():
    html = """
    <table>
      <tr>
        <th>Name</th><th>Deadline for Registration</th><th>Bid Submission Date</th><th>Info</th><th>Document</th>
      </tr>
      <tr>
        <td>Supply and Delivery of Submersible Pumps MWSC-ENG-2026-089</td>
        <td>15 Oct 2026</td>
        <td>22 Oct 2026</td>
        <td>Online</td>
        <td><a href="https://mwsc.com.mv/docs/pump.pdf">PDF</a></td>
      </tr>
    </table>
    """
    records = parse_mwsc_tenders(html)
    assert len(records) == 1
    r = records[0]
    assert r.source_name == "mwsc.com.mv"
    assert r.reference_number == "MWSC-ENG-2026-089"
    assert r.agency == "Male' Water and Sewerage Company"
    assert "Submersible Pumps" in r.title
    assert r.info_date == "15 Oct 2026"
    assert "https://mwsc.com.mv/docs/pump.pdf" in r.document_urls
    assert "MWSC Customer Building" in r.submission_location


# ---------------------------------------------------------------------
# 4. STELCO parser
# ---------------------------------------------------------------------
def test_parse_stelco_tenders():
    html = """
    <table>
      <tr><th>Title</th><th>Category</th><th>Date</th></tr>
      <tr>
        <td>H/IUL/2026/128A Procurement of 11kV Transformers 1 file(s) 37 downloads</td>
        <td>Procurement</td>
        <td>10 Oct 2026</td>
      </tr>
    </table>
    """
    records = parse_stelco_tenders(html)
    assert len(records) == 1
    r = records[0]
    assert r.source_name == "stelco.com.mv"
    assert r.reference_number == "H/IUL/2026/128A"
    assert r.agency == "State Electric Company"
    assert "Procurement of 11kV Transformers" in r.title
    assert "downloads" not in r.title
    assert "STELCO Head Office" in r.submission_location


# ---------------------------------------------------------------------
# 5. STO parser
# ---------------------------------------------------------------------
def test_parse_sto_tenders():
    html = """
    <div>
      <a href="/newsroom/tenders/405/fuel-barges">
        60-PRO/2026/265 Supply of High Capacity Fuel Barges Oct 10, 2026
      </a>
      <a href="/newsroom/tenders/archive">Archive link to ignore</a>
    </div>
    """
    records = parse_sto_tenders(html)
    assert len(records) == 1
    r = records[0]
    assert r.source_name == "sto.mv"
    assert r.reference_number == "60-PRO/2026/265"
    assert r.agency == "State Trading Organization"
    assert "Supply of High Capacity Fuel Barges" in r.title
    assert "https://www.sto.mv/newsroom/tenders/405/fuel-barges" == r.source_url


# ---------------------------------------------------------------------
# 6. fetch_all_agency_portals aggregation
# ---------------------------------------------------------------------
def test_fetch_all_agency_portals_mocked():
    with patch("scrapers.agencies._get_soup") as mock_soup:
        def side_effect(url, timeout=10):
            if "finance" in url:
                return bs4.BeautifulSoup("<table><tr><th>Project Type</th><th>Invitation Ref No</th><th>Procurement No</th><th>Procurement Name</th><th>Sector</th><th>Agency</th><th>Appr</th><th>Pub</th><th>Sub</th></tr><tr><td>W</td><td>(IUL)13-K/2026/1</td><td>T1</td><td>Hospital</td><td>H</td><td>Ministry of Health</td><td>A</td><td>01/10/2026</td><td>20/10/2026</td></tr></table>", "html.parser")
            elif "tourism" in url:
                return bs4.BeautifulSoup("<table><tr><td>01 Oct</td><td>Eco Tourism Resort - (IUL)88-PS/2026/50</td></tr></table>", "html.parser")
            return None

        mock_soup.side_effect = side_effect
        records = fetch_all_agency_portals()
        assert len(records) == 2
        sources = {r.source_name for r in records}
        assert "finance.gov.mv" in sources
        assert "tourism.gov.mv" in sources


# ---------------------------------------------------------------------
# 7. Cross-source repetition matching & SQLite merging
# ---------------------------------------------------------------------
def test_cross_source_deduplication_and_merging(temp_db):
    with get_db(temp_db) as conn:
        # 1. Ingest bid from Gazette
        gazette_bid = {
            "notice_id": "180201",
            "agency": "Ministry of Health",
            "title": "ނ. ވެލިދޫ ހޮސްޕިޓަލް އިމާރާތްކުރުމުގެ މަސައްކަތް",
            "title_en": "Construction of Velidhoo Hospital",
            "reference_number": "(IUL)13-K/13/2026/202",
            "gazette_type": "Work",
            "discipline": "Construction",
            "published_date": "2026-10-10T10:00:00",
            "submission_date": "2026-10-25T13:00:00",
            "source_url": "https://gazette.gov.mv/iulaan/180201",
            "sources": ["gazette.gov.mv"],
        }
        bid_id_1 = upsert_bid(conn, gazette_bid)
        assert bid_id_1 > 0

        # Verify initial single source
        initial_bids = query_bids(conn)
        assert len(initial_bids) == 1
        assert initial_bids[0]["sources"] == ["gazette.gov.mv"]
        assert initial_bids[0]["is_cross_listed"] is False

        # 2. Ingest duplicate notice from Ministry of Finance portal with same ref
        finance_bid = {
            "notice_id": "finance_tes_2026_w025",
            "agency": "Ministry of Health",
            "title": "Construction of 30 Bed Hospital at N. Velidhoo",
            "title_en": "Construction of 30 Bed Hospital at N. Velidhoo",
            "reference_number": "(IUL)13-K/13/2026/202",
            "submission_location": "National Tender Board, Ministry of Finance, Male'",
            "info_location": "National Tender Board",
            "source_url": "https://www.finance.gov.mv/tenders",
            "sources": ["finance.gov.mv"],
            "document_urls": ["https://finance.gov.mv/docs/velidhoo_specs.pdf"],
        }
        bid_id_2 = upsert_bid(conn, finance_bid)
        # Should return the same record ID
        assert bid_id_2 == bid_id_1

        # Verify only 1 canonical record exists, with merged sources & populated locations
        merged_bids = query_bids(conn)
        assert len(merged_bids) == 1
        canonical = merged_bids[0]
        assert sorted(canonical["sources"]) == ["finance.gov.mv", "gazette.gov.mv"]
        assert canonical["is_cross_listed"] is True
        assert canonical["submission_location"] == "National Tender Board, Ministry of Finance, Male'"
        assert "https://finance.gov.mv/docs/velidhoo_specs.pdf" in canonical["document_urls"]


def test_agency_portal_statistics_and_filtering(temp_db):
    with get_db(temp_db) as conn:
        # Ingest 1 Gazette-only bid
        upsert_bid(
            conn,
            {
                "notice_id": "g_1",
                "agency": "State Trading Organization",
                "title": "Supply of Marine Fuel",
                "reference_number": "60-PRO/2026/101",
                "sources": ["gazette.gov.mv"],
            },
        )
        # Ingest 1 cross-listed bid (Gazette + STO)
        bid_id = upsert_bid(
            conn,
            {
                "notice_id": "g_2",
                "agency": "State Trading Organization",
                "title": "Supply of Rice & Sugar",
                "reference_number": "60-PRO/2026/102",
                "sources": ["gazette.gov.mv"],
            },
        )
        upsert_bid(
            conn,
            {
                "notice_id": "sto_102",
                "agency": "State Trading Organization",
                "title": "Supply of Rice & Sugar",
                "reference_number": "60-PRO/2026/102",
                "sources": ["sto.mv"],
            },
        )

        stats = get_agency_portal_statistics(conn)
        assert stats["total_bids"] == 2
        assert stats["cross_listed_count"] == 1
        assert stats["portal_counts"]["gazette.gov.mv"] == 2
        assert stats["portal_counts"]["sto.mv"] == 1
        assert "State Trading Organization Plc" in stats["by_agency"]
        assert stats["by_agency"]["State Trading Organization Plc"]["total"] == 2
        assert stats["by_agency"]["State Trading Organization Plc"]["cross_listed"] == 1

        # Test portal filter
        sto_bids = query_bids(conn, portal="sto.mv")
        assert len(sto_bids) == 1
        assert sto_bids[0]["reference_number"] == "60-PRO/2026/102"

        # Test cross_listed_only filter
        cross_bids = query_bids(conn, cross_listed_only=True)
        assert len(cross_bids) == 1
        assert cross_bids[0]["reference_number"] == "60-PRO/2026/102"


def test_cross_source_deduplication_by_title_fallback(temp_db):
    with get_db(temp_db) as conn:
        # Gazette notice without reference number
        upsert_bid(
            conn,
            {
                "notice_id": "g_no_ref_99",
                "agency": "Male' Water and Sewerage Company",
                "title": "Supply and Delivery of Submersible Waste Water Pumps",
                "title_en": "Supply and Delivery of Submersible Waste Water Pumps",
                "reference_number": None,
                "sources": ["gazette.gov.mv"],
            },
        )
        # Agency notice with reference number and matching title
        upsert_bid(
            conn,
            {
                "notice_id": "mwsc_portal_pump_1",
                "agency": "Male' Water and Sewerage Company",
                "title": "Supply and Delivery of Submersible Waste Water Pumps",
                "reference_number": "MWSC-ENG-2026-99",
                "submission_location": "MWSC Customer Building 3rd Floor",
                "sources": ["mwsc.com.mv"],
            },
        )
        bids = query_bids(conn)
        assert len(bids) == 1
        b = bids[0]
        assert b["is_cross_listed"] is True
        assert sorted(b["sources"]) == ["gazette.gov.mv", "mwsc.com.mv"]
        assert b["reference_number"] == "MWSC-ENG-2026-99"
        assert b["submission_location"] == "MWSC Customer Building 3rd Floor"


# ---------------------------------------------------------------------
# 8. Verify No Emojis in templates/bids.html
# ---------------------------------------------------------------------
def test_bids_template_has_no_emojis():
    template_path = Path("templates/bids.html")
    assert template_path.exists(), "bids.html template not found"
    content = template_path.read_text(encoding="utf-8")

    # Unicode emoji code point ranges
    emoji_chars = [
        c for c in content
        if (0x1F300 <= ord(c) <= 0x1F9FF)
        or (0x2600 <= ord(c) <= 0x27BF)
        or (0x1FA70 <= ord(c) <= 0x1FAFF)
    ]
    assert emoji_chars == [], f"Found unexpected emoji characters in bids.html: {emoji_chars}"


def test_all_ui_templates_have_no_emojis():
    """Enforce strict design policy: zero emojis in the entire web UI."""
    templates_dir = Path("templates")
    assert templates_dir.is_dir()
    for html_file in templates_dir.glob("*.html"):
        content = html_file.read_text(encoding="utf-8")
        emoji_chars = [
            c for c in content
            if (0x1F300 <= ord(c) <= 0x1F9FF)
            or (0x2600 <= ord(c) <= 0x27BF)
            or (0x1FA70 <= ord(c) <= 0x1FAFF)
        ]
        assert emoji_chars == [], f"Found unexpected emoji characters in {html_file.name}: {emoji_chars}"
