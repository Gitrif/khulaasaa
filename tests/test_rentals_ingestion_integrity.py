"""
Rental Ingestion Integrity and Non-Destructive Synchronization Tests.
Validates:
1. Failed or empty sources cannot erase existing listings.
2. Direct user-submitted listings (is_direct = 1) are never mutated or deleted.
3. Idempotent upsert prevents duplicate multiplication.
4. Updates correctly modify the matching canonical record.
Strictly under 500 lines. Zero emojis.
"""
from __future__ import annotations

import sqlite3
import pytest
from unittest.mock import patch

from data.connection import get_db
from data.rentals import init_rentals_schema, list_rentals
from data.scrapers.rentals_scraper import (
    _item,
    upsert_rental_listing,
    rescrape_and_sync_all_rentals,
    scrape_ibay_rentals,
    get_rentals_sync_status,
)


@pytest.fixture
def clean_rentals_db():
    """Create a temporary in-memory SQLite database initialized with rentals schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_rentals_schema(conn)
    yield conn
    conn.close()


def test_failed_source_does_not_delete_existing_listings(clean_rentals_db):
    """Verify that if an external source scraper raises an exception, existing records are preserved."""
    conn = clean_rentals_db

    # Seed an existing scraped listing and a direct listing
    listing1 = _item(
        title="Existing 2BHK Apartment", loc="Male City", dist="Henveiru",
        road="Sosun Magu", bld="M. Amber", total_f=5, f_num=2, f_str="2nd Floor",
        unit="2A", beds=2, att=2, tot=2, sqft=700, lift=1, kitchen="Open",
        living="Lounge", ac="Installed", heaters=2, furn="Fully Furnished",
        items=[], rent=21000, sec_rent=None, sec_src=None, dep=42000,
        src="iBay Maldives", url="https://ibay.com.mv/existing-apt-1.html",
        sec_urls=[], img="", parking="Street", contact="Lister A", phone="+960 7711111",
        desc="Pre-existing listing", ams=[], facs=[]
    )
    upsert_rental_listing(conn, listing1)

    # Insert a direct submission (is_direct = 1)
    conn.execute(
        """
        INSERT INTO rentals (
            title, location, district, bedrooms, attached_toilets, total_toilets,
            rent_mvr, deposit_mvr, source_name, source_url, is_direct, is_active
        ) VALUES (
            'Direct Landlord Listing', 'Hulhumale Phase 1', 'Neighborhood 1',
            3, 3, 3, 25000, 25000, 'Direct Owner', 'https://khulaasaa.tech/rentals/direct-1', 1, 1
        );
        """
    )
    conn.commit()

    initial_count = conn.execute("SELECT count(*) FROM rentals;").fetchone()[0]
    assert initial_count == 2

    # Run sync with a scraper that fails with an exception
    def failing_scraper():
        raise ConnectionResetError("Remote server closed connection")

    mock_sources = [("FailingPortal", failing_scraper)]
    rescrape_and_sync_all_rentals(conn, sources=mock_sources)

    # Verify no records were deleted
    count_after = conn.execute("SELECT count(*) FROM rentals;").fetchone()[0]
    assert count_after == initial_count

    remaining_titles = [r[0] for r in conn.execute("SELECT title FROM rentals;").fetchall()]
    assert "Existing 2BHK Apartment" in remaining_titles
    assert "Direct Landlord Listing" in remaining_titles

    status = get_rentals_sync_status()
    assert "Remote server closed connection" in str(status.get("last_error"))


def test_empty_source_does_not_delete_existing_listings(clean_rentals_db):
    """Verify that an empty response from a scraper does not delete current inventory."""
    conn = clean_rentals_db

    listing = _item(
        title="Hiyaa Flat Phase 2", loc="Hulhumale Phase 2", dist="Hiyaa Flat Area",
        road="Hiyaa Avenue", bld="Tower 7", total_f=25, f_num=10, f_str="10th Floor",
        unit="Flat 10-02", beds=2, att=2, tot=2, sqft=750, lift=1, kitchen="Open",
        living="Lounge", ac="Installed", heaters=2, furn="Semi-Furnished",
        items=[], rent=18000, sec_rent=None, sec_src=None, dep=36000,
        src="Hiyaa.mv", url="https://hiyaa.mv/flat-10-02.html",
        sec_urls=[], img="", parking="Street", contact="Owner", phone="+960 7722222",
        desc="Tower 7 listing", ams=[], facs=[]
    )
    upsert_rental_listing(conn, listing)
    conn.commit()

    # Run sync with an empty returning scraper
    def empty_scraper():
        return []

    mock_sources = [("EmptySource", empty_scraper)]
    rescrape_and_sync_all_rentals(conn, sources=mock_sources)

    count_after = conn.execute("SELECT count(*) FROM rentals;").fetchone()[0]
    assert count_after == 1


def test_idempotent_sync_does_not_multiply_duplicates(clean_rentals_db):
    """Verify multiple synchronization runs with identical records update rather than duplicate."""
    conn = clean_rentals_db

    sample_items = [
        _item(
            title="Modern Henveiru Apt", loc="Male City", dist="Henveiru",
            road="Roashanee Magu", bld="H. Sun", total_f=6, f_num=3, f_str="3rd Floor",
            unit="3B", beds=2, att=2, tot=2, sqft=800, lift=1, kitchen="Open",
            living="Lounge", ac="Yes", heaters=2, furn="Furnished",
            items=[], rent=23000, sec_rent=None, sec_src=None, dep=46000,
            src="iBay Maldives", url="https://ibay.com.mv/listing-unique-101.html",
            sec_urls=[], img="", parking="Street", contact="Agent", phone="+960 7733333",
            desc="Nice flat", ams=[], facs=[]
        ),
        _item(
            title="Phase 1 Studio Flat", loc="Hulhumale Phase 1", dist="Neighborhood 2",
            road="Nirolhu Magu", bld="Lot 10200", total_f=4, f_num=1, f_str="1st Floor",
            unit="101", beds=1, att=1, tot=1, sqft=450, lift=0, kitchen="Open",
            living="Compact", ac="Yes", heaters=1, furn="Semi-Furnished",
            items=[], rent=12000, sec_rent=None, sec_src=None, dep=12000,
            src="iBay Maldives", url="https://ibay.com.mv/listing-unique-102.html",
            sec_urls=[], img="", parking="Street", contact="Agent", phone="+960 7744444",
            desc="Studio flat", ams=[], facs=[]
        ),
    ]

    mock_sources = [("TestPortal", lambda: sample_items)]

    # First run: inserts 2 records
    rescrape_and_sync_all_rentals(conn, sources=mock_sources)
    count_1 = conn.execute("SELECT count(*) FROM rentals;").fetchone()[0]
    assert count_1 == 2

    # Second run: must update in-place, NOT multiply records
    rescrape_and_sync_all_rentals(conn, sources=mock_sources)
    count_2 = conn.execute("SELECT count(*) FROM rentals;").fetchone()[0]
    assert count_2 == 2


def test_successful_update_changes_correct_record(clean_rentals_db):
    """Verify that updating a listing changes price and title on the specific canonical record."""
    conn = clean_rentals_db

    initial_item = _item(
        title="Galolhu 2BR Original", loc="Male City", dist="Galolhu",
        road="Majeedhee Magu", bld="G. Star", total_f=7, f_num=4, f_str="4th Floor",
        unit="401", beds=2, att=2, tot=2, sqft=750, lift=1, kitchen="Open",
        living="Lounge", ac="Yes", heaters=2, furn="Semi-Furnished",
        items=[], rent=20000, sec_rent=None, sec_src=None, dep=40000,
        src="iBay Maldives", url="https://ibay.com.mv/galolhu-2br-401.html",
        sec_urls=[], img="", parking="Street", contact="Agent", phone="+960 7755555",
        desc="Initial description", ams=[], facs=[]
    )
    upsert_rental_listing(conn, initial_item)
    conn.commit()

    r1 = conn.execute("SELECT id, rent_mvr, title FROM rentals WHERE source_url = ?", (initial_item["source_url"],)).fetchone()
    original_id = r1["id"]
    assert r1["rent_mvr"] == 20000
    assert r1["title"] == "Galolhu 2BR Original"

    # Updated listing from source with rent reduction and new title
    updated_item = dict(initial_item)
    updated_item["title"] = "Galolhu 2BR Reduced Price"
    updated_item["rent_mvr"] = 18500
    updated_item["deposit_mvr"] = 37000

    upsert_rental_listing(conn, updated_item)
    conn.commit()

    r2 = conn.execute("SELECT id, rent_mvr, title FROM rentals WHERE source_url = ?", (initial_item["source_url"],)).fetchone()
    assert r2["id"] == original_id  # Stable ID preserved
    assert r2["rent_mvr"] == 18500  # Updated price
    assert r2["title"] == "Galolhu 2BR Reduced Price"


def test_scrape_ibay_parses_real_html_structure():
    """Verify scrape_ibay_rentals parses HTML cards, prices, and attached bathroom counts."""
    fixture_html = """
    <html><body>
        <div class="row">
            <div class="col m7 s8">
                <a href="modern-3-room-apartment-hulhumale-phase-2-o6689999.html?ref=latest">
                    Modern 3 Room apartment with attached toilets in Hulhumale Phase 2
                </a>
            </div>
            <div>
                Rooms : 3 Rooms | Furnishing : Fully Furnished | MVR | 24,000.00
                Call 7912345 for inspection. Lift available.
            </div>
        </div>
    </body></html>
    """
    items = scrape_ibay_rentals(raw_html=fixture_html)
    assert len(items) == 1
    it = items[0]
    assert it["bedrooms"] == 3
    assert it["attached_toilets"] == 3
    assert it["rent_mvr"] == 24000
    assert it["location"] == "Hulhumale Phase 2"
    assert it["contact_phone"] == "+960 7912345"
    assert "ibay.com.mv/modern-3-room-apartment" in it["source_url"]
