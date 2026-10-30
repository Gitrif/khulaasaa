from datetime import datetime, timedelta, timezone
import pytest

from scrapers.dedupe import (
    normalize_reference,
    normalize_title,
    _fallback_match,
    _build_merged,
    merge_records,
    aggregate_bids,
    SourceRecord,
    MergedBid,
)
from scrapers.tenders.gazette import BidNotice, classify_discipline


# ---------------------------------------------------------------------
# Normalization tests
# ---------------------------------------------------------------------

def test_normalize_reference():
    assert normalize_reference("HDC (161)-PRO/IU/2021/168") == "HDC(161)-PRO/IU/2021/168"
    assert normalize_reference("  hdc(161)-pro/iu/2021/168  ") == "HDC(161)-PRO/IU/2021/168"
    assert normalize_reference("TES / 2020 / W - 021") == "TES/2020/W-021"

    # Invisible unicode formatting characters often in PDFs
    ref_with_invisible = "HDC\u200B(161)-\u200EPRO/IU/\u200F2021/168"
    assert normalize_reference(ref_with_invisible) == "HDC(161)-PRO/IU/2021/168"


def test_normalize_title():
    assert normalize_title("Hulhumalé Phase I Major Roads – Road Markings & Asphalt Repair") == (
        "hulhumalé phase i major roads road markings and asphalt repair"
    )
    assert normalize_title("  UPGRADING OF   A.DH FENFUSHI HARBOUR!  ") == (
        "upgrading of adh fenfushi harbour"
    )
    assert normalize_title("Supply & Delivery of Computer Systems, Laptops...") == (
        "supply and delivery of computer systems laptops"
    )


# ---------------------------------------------------------------------
# Fallback match tests
# ---------------------------------------------------------------------

def test_fallback_match():
    base = SourceRecord(
        source_name="gazette.gov.mv",
        source_url="https://gazette.gov.mv/iulaan/1",
        reference_number=None,
        agency="Ministry of Tourism",
        title="Space Leasing for Shop",
        published_iso="2026-09-20T10:00:00",
        deadline_iso="2026-10-10T14:00:00",
    )

    # Identical agency & title, same date -> Match
    rec_same_date = SourceRecord(
        source_name="tourism.gov.mv",
        source_url="https://tourism.gov.mv/bids/1",
        reference_number=None,
        agency="  ministry of tourism  ",
        title="Space Leasing for Shop!",
        published_iso="2026-09-20T11:00:00",
        deadline_iso="2026-10-10T14:00:00",
    )
    assert _fallback_match(base, rec_same_date) is True

    # Published 2 days later (within 3-day window) -> Match
    rec_within_3_days = SourceRecord(
        source_name="tourism.gov.mv",
        source_url="https://tourism.gov.mv/bids/1",
        reference_number=None,
        agency="Ministry of Tourism",
        title="Space Leasing for Shop",
        published_iso="2026-09-22T15:00:00",
        deadline_iso=None,
    )
    assert _fallback_match(base, rec_within_3_days) is True

    # Published 5 days later (> 3-day window) -> Reject
    rec_too_late = SourceRecord(
        source_name="tourism.gov.mv",
        source_url="https://tourism.gov.mv/bids/1",
        reference_number=None,
        agency="Ministry of Tourism",
        title="Space Leasing for Shop",
        published_iso="2026-09-26T10:00:00",
        deadline_iso=None,
    )
    assert _fallback_match(base, rec_too_late) is False

    # Different agency -> Reject
    rec_diff_agency = SourceRecord(
        source_name="mira.gov.mv",
        source_url="https://mira.gov.mv/bids/1",
        reference_number=None,
        agency="Maldives Inland Revenue Authority",
        title="Space Leasing for Shop",
        published_iso="2026-09-20T10:00:00",
        deadline_iso=None,
    )
    assert _fallback_match(base, rec_diff_agency) is False

    # Different title -> Reject
    rec_diff_title = SourceRecord(
        source_name="tourism.gov.mv",
        source_url="https://tourism.gov.mv/bids/1",
        reference_number=None,
        agency="Ministry of Tourism",
        title="Audit of Island Resorts",
        published_iso="2026-09-20T10:00:00",
        deadline_iso=None,
    )
    assert _fallback_match(base, rec_diff_title) is False

    # Missing published dates with same agency and title -> Match conservatively
    rec_no_date = SourceRecord(
        source_name="tourism.gov.mv",
        source_url="https://tourism.gov.mv/bids/1",
        reference_number=None,
        agency="Ministry of Tourism",
        title="Space Leasing for Shop",
        published_iso=None,
        deadline_iso=None,
    )
    assert _fallback_match(base, rec_no_date) is True


# ---------------------------------------------------------------------
# Merge records tests
# ---------------------------------------------------------------------

def test_merge_records_by_reference(sample_gazette_notice, sample_hdc_source_record):
    gazette_sr = sample_gazette_notice.to_source_record()
    records = [sample_hdc_source_record, gazette_sr]

    merged = merge_records(records)
    assert len(merged) == 1

    bid = merged[0]
    # Primary reference preserved
    assert bid.reference_number in ("HDC (161)-PWM/IU/2021/520", "HDC(161)-PWM/IU/2021/520")
    # Earliest published date kept (gazette: 2021-10-11, hdc: 2021-10-12)
    assert bid.published_iso == "2021-10-11T21:45:00"
    # Deadline kept
    assert bid.deadline_iso == "2021-11-02T11:00:00"
    # Both sources included
    assert "gazette.gov.mv" in bid.source_names
    assert "hdc.com.mv" in bid.source_names
    # Combined document URLs without duplicates
    assert len(bid.all_document_urls) == 2
    assert "https://hdc.com.mv/announcements/bids/" in bid.all_document_urls
    assert "https://hdc.com.mv/files/tender-docs.zip" in bid.all_document_urls


def test_merge_records_unkeyed_fallback():
    r1 = SourceRecord(
        source_name="gazette.gov.mv",
        source_url="https://gazette.gov.mv/iulaan/101",
        reference_number=None,
        agency="HA. Hoarafushi Council",
        title="Lease, Development and Operation of Tourist Guesthouse",
        published_iso="2026-09-01T10:00:00",
        deadline_iso="2026-09-30T14:00:00",
        document_urls=["https://gazette.gov.mv/doc1.pdf"],
    )
    r2 = SourceRecord(
        source_name="hoarafushi.gov.mv",
        source_url="https://hoarafushi.gov.mv/bids/guesthouse",
        reference_number=None,
        agency="HA. Hoarafushi Council",
        title="Lease, Development & Operation of Tourist Guesthouse!",
        published_iso="2026-09-02T08:30:00",
        deadline_iso=None,
        document_urls=["https://hoarafushi.gov.mv/terms.pdf"],
    )
    r3 = SourceRecord(
        source_name="gazette.gov.mv",
        source_url="https://gazette.gov.mv/iulaan/102",
        reference_number=None,
        agency="Secretariat of V.Fulidhoo Council",
        title="Finishing Work of Police Post",
        published_iso="2026-09-01T12:00:00",
        deadline_iso=None,
    )

    merged = merge_records([r1, r2, r3])
    # r1 and r2 merged, r3 remains distinct
    assert len(merged) == 2

    hoarafushi_bid = next(b for b in merged if "Hoarafushi" in b.agency)
    assert len(hoarafushi_bid.sources) == 2
    assert hoarafushi_bid.published_iso == "2026-09-01T10:00:00"
    assert hoarafushi_bid.deadline_iso == "2026-09-30T14:00:00"
    assert len(hoarafushi_bid.all_document_urls) == 2

    fulidhoo_bid = next(b for b in merged if "Fulidhoo" in b.agency)
    assert len(fulidhoo_bid.sources) == 1


# ---------------------------------------------------------------------
# MergedBid properties and serialization
# ---------------------------------------------------------------------

def test_merged_bid_is_open_and_to_dict():
    future_date = (datetime.now() + timedelta(days=5)).isoformat()
    sr = SourceRecord(
        source_name="gazette.gov.mv",
        source_url="https://gazette.gov.mv/iulaan/1",
        reference_number="TES/2026/W-001",
        agency="Ministry of Finance",
        title="Harbour Development Project",
        published_iso="2026-09-01T10:00:00",
        deadline_iso=future_date,
        document_urls=["https://example.com/doc.pdf"],
    )
    merged_bid = _build_merged([sr])
    merged_bid.discipline = "Construction"

    assert merged_bid.is_open is True
    d = merged_bid.to_dict()
    assert d["ref"] == "TES/2026/W-001"
    assert d["agency"] == "Ministry of Finance"
    assert d["title"] == "Harbour Development Project"
    assert d["discipline"] == "Construction"
    assert d["is_open"] is True
    assert d["source_names"] == ["gazette.gov.mv"]
    assert d["document_urls"] == ["https://example.com/doc.pdf"]
    assert d["source_url"] == "https://gazette.gov.mv/iulaan/1"


# ---------------------------------------------------------------------
# High-level aggregate_bids pipeline test
# ---------------------------------------------------------------------

def test_aggregate_bids_pipeline(sample_gazette_notice, sample_hdc_source_record):
    raw_dict = {
        "ref": "TES/2020/W-021",
        "agency": "Ministry of Finance",
        "title": "Upgrading of A.Dh Fenfushi Harbour",
        "published_iso": "2020-03-01T10:00:00",
        "deadline_iso": None,
        "source_name": "gazette.gov.mv",
        "source_url": "https://gazette.gov.mv/iulaan/view/127322",
    }

    # Pass heterogeneous records: BidNotice, SourceRecord, dict
    records = [sample_gazette_notice, sample_hdc_source_record, raw_dict]

    # Run aggregator with discipline classifier
    aggregated = aggregate_bids(records, classifier=classify_discipline)

    # 3 inputs: notice + hdc merge into 1, raw_dict is 2nd
    assert len(aggregated) == 2

    hdc_bid = next(b for b in aggregated if "HDC" in b.reference_number)
    assert len(hdc_bid.sources) == 2
    assert hdc_bid.discipline == "Construction"

    mof_bid = next(b for b in aggregated if "TES" in b.reference_number)
    assert len(mof_bid.sources) == 1
    assert mof_bid.discipline == "Construction"


def test_aggregate_bids_type_error():
    with pytest.raises(TypeError):
        aggregate_bids([12345])  # type: ignore
