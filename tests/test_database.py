import sqlite3
import pytest
from pathlib import Path

from data.database import (
    init_db,
    get_db,
    slugify,
    detect_entity_type,
    resolve_or_create_entity,
    list_entities,
    upsert_bid,
    query_bids,
    extract_milestones_and_venues,
    purge_expired_bids,
    upsert_article,
    query_articles,
)


@pytest.fixture
def temp_db(tmp_path: Path):
    db_file = tmp_path / "test_khulaasaa.db"
    init_db(db_file)
    return db_file


def test_init_db_and_entity_seeding(temp_db):
    with get_db(temp_db) as conn:
        entities = list_entities(conn)
        assert len(entities) >= 20
        # Check canonical SOEs and ministries
        slugs = {e["slug"] for e in entities}
        assert "housing-development-corporation" in slugs
        assert "state-trading-organization" in slugs
        assert "male-water-and-sewerage-company" in slugs
        assert "ministry-of-finance" in slugs
        assert "council-uligan" in slugs


def test_detect_entity_type():
    assert detect_entity_type("Addu City Council") == "Council"
    assert detect_entity_type("އުލިގަމު ކައުންސިލްގެ އިދާރާ") == "Council"
    assert detect_entity_type("Ministry of Finance and Planning") == "Ministry"
    assert detect_entity_type("މިނިސްޓްރީ އޮފް ޓޫރިޒަމް") == "Ministry"
    assert detect_entity_type("Indira Gandhi Memorial Hospital") == "Healthcare"
    assert detect_entity_type("ކުޅިވަރު ޞިއްޙީ މަރުކަޒު") == "Healthcare"
    assert detect_entity_type("Maldives Polytechnic") == "Education"
    assert detect_entity_type("Fenaka Corporation Limited") == "SOE"
    assert detect_entity_type("State Electric Company Ltd") == "SOE"
    assert detect_entity_type("Maldives Customs Service") == "Independent"


def test_resolve_or_create_entity(temp_db):
    with get_db(temp_db) as conn:
        # Existing entity alias resolution
        hdc_id = resolve_or_create_entity(conn, "Housing Development Corporation Ltd.")
        assert hdc_id is not None

        sto_id = resolve_or_create_entity(conn, "STO Plc")
        assert sto_id is not None

        mwsc_id = resolve_or_create_entity(conn, "Male' Water and Sewerage Company Pvt Ltd.")
        assert mwsc_id is not None

        # Auto-create new entity with auto-detected category
        new_id = resolve_or_create_entity(conn, "K. Maafushi Health Center")
        row = conn.execute("SELECT slug, entity_type FROM entities WHERE id = ?", (new_id,)).fetchone()
        assert row["slug"] == "k-maafushi-health-center"
        assert row["entity_type"] == "Healthcare"


def test_upsert_and_query_bids(temp_db):
    with get_db(temp_db) as conn:
        bid_data = {
            "notice_id": "166396",
            "agency": "Housing Development Corporation",
            "title": "Hulhumalé Phase I Major Roads – Road Markings & Asphalt Repair",
            "reference_number": "HDC (161)-PWM/IU/2021/520",
            "gazette_type": "Work",
            "discipline": "Construction",
            "published_date": "2021-10-11T21:45:00",
            "submission_date": "2021-11-02T11:00:00",
            "submission_location": "HDC Building Ground Floor Reception",
            "info_date": "17 Oct 2021 11:00",
            "info_location": "Zoom Meeting Online",
            "source_url": "https://gazette.gov.mv/iulaan/print/166396",
            "document_urls": ["https://hdc.com.mv/announcements/bids/"],
        }
        bid_id = upsert_bid(conn, bid_data)
        assert bid_id > 0

        # Query all
        results = query_bids(conn)
        assert len(results) == 1
        b = results[0]
        assert b["notice_id"] == "166396"
        assert b["agency_name_en"] == "Housing Development Corporation"
        assert b["entity_type"] == "SOE"
        assert b["submission_location"] == "HDC Building Ground Floor Reception"
        assert b["info_date"] == "17 Oct 2021 11:00"
        assert b["info_location"] == "Zoom Meeting Online"
        assert "https://hdc.com.mv/announcements/bids/" in b["document_urls"]

        # Filter by entity_type SOE
        soe_bids = query_bids(conn, entity_type="SOE")
        assert len(soe_bids) == 1

        # Filter by discipline Construction
        const_bids = query_bids(conn, discipline="Construction")
        assert len(const_bids) == 1

        # Filter by search keyword
        search_res = query_bids(conn, search_q="Asphalt")
        assert len(search_res) == 1

        no_res = query_bids(conn, search_q="NonexistentWord")
        assert len(no_res) == 0


def test_extract_milestones_and_venues(en_notice_html, dv_notice_html):
    en_res = extract_milestones_and_venues(en_notice_html)
    assert "Reception, Ground Floor, HDC Building" in en_res["submission_location"]
    assert "17 th October 2021" in en_res["info_date"]
    assert "Zoom Meeting" in en_res["info_location"]

    dv_res = extract_milestones_and_venues(dv_notice_html)
    assert "މިއިދާރާއަށް ވަޑައިގެން" in dv_res["info_date"]
    assert "މިއިދާރާއަށް ވަޑައިގެން" in dv_res["info_location"] or "އޮންލައިން" in dv_res["info_location"]


def test_mwsc_table_and_contextual_prose_extraction():
    # 4-column table like MWSC Notice 417266
    mwsc_html = """
    <table>
      <tr><th>Step</th><th>Process</th><th>Date & Time</th><th>Venue / Method</th></tr>
      <tr><td>1.</td><td>Pre Bid Meeting</td><td>19 th October 2026, 02:00 PM.</td><td>Microsoft Teams Meeting</td></tr>
      <tr><td>2.</td><td>Clarification Deadline</td><td>20 th October 2026, 02:00 PM.</td><td>Email to: procurement@mwsc.com.mv</td></tr>
      <tr><td>3.</td><td>Submission of Proposal & Proposal Opening</td><td>22 nd October 2026, 02:00 PM.</td><td>MWSC CS Building, 6 th Floor Ameenee Magu, Male', Maldives.</td></tr>
    </table>
    """
    res = extract_milestones_and_venues(mwsc_html)
    assert res["info_date"] == "19 th October 2026, 02:00 PM."
    assert res["info_location"] == "Microsoft Teams Meeting"
    assert res["submission_date"] == "22 nd October 2026, 02:00 PM."
    assert "MWSC CS Building" in res["submission_location"]

    # Dhivehi prose with contextual venue and date (like Addu Notice 417258)
    addu_prose_html = """
    <div>
      <p>ބީލަންތައް ބަލައިގަތުމާއި، އަދި ބީލަން ހުޅުވުން އޮންނާނީ 2026 ނޮވެންބަރު 02 ވާ ހޯމަ ދުވަހުގެ 09:30 ގައި އައްޑޫ ސިޓީ ކައުންސިލް އިދާރާގައެވެ.</p>
    </div>
    """
    addu_res = extract_milestones_and_venues(addu_prose_html)
    assert "2026" in addu_res["submission_date"]
    assert "09:30" in addu_res["submission_date"]
    assert "އައްޑޫ ސިޓީ ކައުންސިލް އިދާރާ" in addu_res["submission_location"]


def test_entity_creation_guarantees_no_thaana_in_name_en(tmp_path):
    db_path = tmp_path / "test_thaana.db"
    init_db(db_path=db_path, seed_bids=False)
    with get_db(db_path) as conn:
        eid = resolve_or_create_entity(conn, "މާޅޮސްމަޑުލު އުތުރުބުރީ ހުޅުދުއްފާރު ކައުންސިލްގެ އިދާރާ")
        row = conn.execute("SELECT slug, name_en, name_dv, entity_type FROM entities WHERE id = ?", (eid,)).fetchone()
        assert not any(0x0780 <= ord(c) <= 0x07BF for c in row["name_en"])
        assert row["name_en"] == "Secretariat of the R. Hulhudhuffaaru Council"
        assert row["entity_type"] == "Council"
        assert "hulhudhuffaaru" in row["slug"]


def test_purge_expired_bids_removes_old_and_preserves_articles(temp_db):
    with get_db(temp_db) as conn:
        # Insert an expired bid (from 2020)
        upsert_bid(conn, {
            "notice_id": "old-expired-2020",
            "agency": "Ministry of Finance",
            "title": "Expired Ancient Harbour Project",
            "published_date": "2020-01-01T00:00:00",
            "submission_date": "2020-02-01T10:00:00",
            "source_url": "https://gazette.gov.mv/iulaan/123",
        })

        # Insert a current active bid (2026)
        upsert_bid(conn, {
            "notice_id": "active-future-2026",
            "agency": "State Electric Company Ltd",
            "title": "Active Transformer Procurement 2026",
            "published_date": "2026-10-15T00:00:00",
            "submission_date": "2026-11-15T10:00:00",
            "source_url": "https://gazette.gov.mv/iulaan/417999",
        })

        # Insert an article (should NEVER be purged)
        upsert_article(conn, {
            "id": "persisted-news-art-1",
            "headline": "Historic Followed Story Article",
            "summary": "This news article must remain preserved permanently in DB.",
            "sources": ["atolltimes"],
            "url": "https://atolltimes.mv/followed-story",
            "published_iso": "2024-05-01T10:00:00Z",
            "section": "major",
        })

        # Purge bids expired > 30 days
        deleted = purge_expired_bids(conn, retention_days=30)
        assert deleted >= 1

        # Check that expired bid was deleted
        active_bids = query_bids(conn)
        notice_ids = {b["notice_id"] for b in active_bids}
        assert "old-expired-2020" not in notice_ids
        assert "active-future-2026" in notice_ids

        # Check that news article was completely preserved
        articles = query_articles(conn)
        art_ids = {a["id"] for a in articles}
        assert "persisted-news-art-1" in art_ids

