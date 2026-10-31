from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest

from scrapers.tenders.gazette import (
    BASE_URL,
    TYPE_SLUGS,
    TYPES,
    BID_ADJACENT_TYPES,
    BID_TITLE_PATTERNS,
    print_url,
    notice_id_from_url,
    parse_published,
    parse_deadline,
    classify_discipline,
    classify_notices,
    parse_notice_html,
    parse_listing_html,
    fetch_notice,
    fetch_listing,
    BidNotice,
)


# ---------------------------------------------------------------------
# URL parsing tests
# ---------------------------------------------------------------------

def test_print_url():
    assert print_url("166396") == "https://gazette.gov.mv/iulaan/print/166396"
    assert print_url("417326") == "https://gazette.gov.mv/iulaan/print/417326"


@pytest.mark.parametrize(
    "url, expected_id",
    [
        ("https://gazette.gov.mv/iulaan/166396", "166396"),
        ("https://gazette.gov.mv/iulaan/print/166396", "166396"),
        ("https://www.gazette.gov.mv/iulaan/view/127322", "127322"),
        ("https://gazette.gov.mv/iulaan/417326?lang=en", "417326"),
        ("/iulaan/print/9999", "9999"),
        ("/iulaan/view/8888", "8888"),
        ("/iulaan/7777", "7777"),
        ("https://gazette.gov.mv/about", None),
        ("https://example.com/other/12345", None),
    ],
)
def test_notice_id_from_url(url, expected_id):
    assert notice_id_from_url(url) == expected_id


# ---------------------------------------------------------------------
# Date and deadline parsing tests
# ---------------------------------------------------------------------

def test_parse_published_english():
    # Date + time
    assert parse_published("11 Oct 2021", "21:45") == "2021-10-11T21:45:00"
    # Combined with prefix
    assert parse_published("Published Date: 23 Jul 2023", "10:17") == "2023-07-23T10:17:00"
    # Date only defaults to 00:00
    assert parse_published("05 Jan 2024") == "2024-01-05T00:00:00"
    # Single digit day
    assert parse_published("1 Feb 2022", "08:30") == "2022-02-01T08:30:00"
    # Invalid / empty
    assert parse_published("") is None
    assert parse_published("invalid date") is None


def test_parse_published_dhivehi():
    # Thaana date + time
    assert parse_published("14 އޮކްޓޫބަރު 2026", "23:02") == "2026-10-14T23:02:00"
    # With Dhivehi prefix
    assert parse_published("ޕަބްލިޝްކުރި ތާރީޚް: 14 އޮކްޓޯބަރ 2026", "23:02") == "2026-10-14T23:02:00"
    # Another Thaana month (September)
    assert parse_published("25 ސެޕްޓެމްބަރ 2026", "14:20") == "2026-09-25T14:20:00"
    # Thaana month with u-sukunu
    assert parse_published("08 ނޮވެމްބަރު 2026", "11:00") == "2026-11-08T11:00:00"


def test_parse_deadline_english():
    assert parse_deadline("02 Nov 2021 11:00") == "2021-11-02T11:00:00"
    assert parse_deadline("Deadline: 31 Jul 2023 14:00") == "2023-07-31T14:00:00"
    assert parse_deadline("") is None
    assert parse_deadline("Not specified") is None


def test_parse_deadline_dhivehi():
    assert parse_deadline("29 އޮކްޓޫބަރު 2026 13:00") == "2026-10-29T13:00:00"
    assert parse_deadline("ސުންގަޑި: 08 ނޮވެމްބަރު 2026 11:00") == "2026-11-08T11:00:00"


# ---------------------------------------------------------------------
# BidNotice Dataclass tests
# ---------------------------------------------------------------------

def test_bid_notice_is_open():
    now = datetime.now()
    future = (now + timedelta(days=10)).isoformat()
    past = (now - timedelta(days=10)).isoformat()

    notice_no_deadline = BidNotice(
        notice_id="1", url="https://gazette.gov.mv/iulaan/1", gazette_type="Bid",
        reference_number="REF-1", published_iso=None, deadline_iso=None,
        agency="Agency", title="Title"
    )
    assert notice_no_deadline.is_open is True

    notice_future = BidNotice(
        notice_id="2", url="https://gazette.gov.mv/iulaan/2", gazette_type="Bid",
        reference_number="REF-2", published_iso=None, deadline_iso=future,
        agency="Agency", title="Title"
    )
    assert notice_future.is_open is True

    notice_past = BidNotice(
        notice_id="3", url="https://gazette.gov.mv/iulaan/3", gazette_type="Bid",
        reference_number="REF-3", published_iso=None, deadline_iso=past,
        agency="Agency", title="Title"
    )
    assert notice_past.is_open is False

    # Timezone-aware deadline
    future_tz = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    notice_tz = BidNotice(
        notice_id="4", url="https://gazette.gov.mv/iulaan/4", gazette_type="Bid",
        reference_number="REF-4", published_iso=None, deadline_iso=future_tz,
        agency="Agency", title="Title"
    )
    assert notice_tz.is_open is True


def test_bid_notice_to_source_record(sample_gazette_notice):
    sr = sample_gazette_notice.to_source_record()
    assert sr.source_name == "gazette.gov.mv"
    assert sr.source_url == sample_gazette_notice.url
    assert sr.reference_number == sample_gazette_notice.reference_number
    assert sr.agency == sample_gazette_notice.agency
    assert sr.title == sample_gazette_notice.title
    assert sr.published_iso == sample_gazette_notice.published_iso
    assert sr.deadline_iso == sample_gazette_notice.deadline_iso
    assert sr.document_urls == sample_gazette_notice.document_urls


# ---------------------------------------------------------------------
# HTML Parsing tests with fixtures
# ---------------------------------------------------------------------

def test_parse_notice_html_english(en_notice_html):
    notice = parse_notice_html(en_notice_html, "166396")
    assert notice.notice_id == "166396"
    assert notice.url == "https://gazette.gov.mv/iulaan/print/166396"
    assert notice.gazette_type == "Work"
    assert notice.reference_number == "HDC (161)-PWM/IU/2021/520"
    assert notice.agency == "Housing Development Corporation"
    assert notice.title == "Hulhumalé Phase I Major Roads – Road Markings & Asphalt Repair"
    assert notice.published_iso == "2021-10-11T21:45:00"
    assert notice.deadline_iso == "2021-11-02T11:00:00"
    assert notice.body is not None
    assert "Invitation of Tender No: HDC (161)-PWM/IU/2021/520" in notice.body
    assert "https://hdc.com.mv/announcements/bids/" in notice.document_urls
    # Milestones & Venues
    assert "Reception, Ground Floor, HDC Building" in notice.submission_location
    assert "17 th October 2021" in notice.info_date
    assert "Zoom Meeting" in notice.info_location


def test_parse_notice_html_dhivehi(dv_notice_html):
    notice = parse_notice_html(dv_notice_html, "417326")
    assert notice.notice_id == "417326"
    assert notice.url == "https://gazette.gov.mv/iulaan/print/417326"
    assert notice.gazette_type == "ބީލަން"
    assert notice.reference_number == "(IUL)245/245/2026/80"
    assert notice.agency == "ތިލަދުންމަތީ އުތުރުބުރީ އުލިގަމު ކައުންސިލްގެ އިދާރާ"
    assert "އުލިގަމު އަންހެނުންގެ ތަރައްޤީއަށް" in notice.title
    assert notice.published_iso == "2026-10-14T23:02:00"
    assert notice.deadline_iso == "2026-10-29T13:00:00"
    assert notice.body is not None
    assert "https://forms.cloud.microsoft/r/H56Wf3FLzt" in notice.document_urls
    # Milestones & Venues
    assert "މިއިދާރާއަށް ވަޑައިގެން" in notice.info_date
    assert "މިއިދާރާއަށް ވަޑައިގެން" in notice.info_location or "އޮންލައިން" in notice.info_location


def test_parse_listing_html(listing_html):
    notices = parse_listing_html(listing_html)
    assert len(notices) == 10

    first = notices[0]
    assert first.notice_id == "417326"
    assert first.url == "https://gazette.gov.mv/iulaan/417326"
    assert first.gazette_type == "ބީލަން"
    assert first.agency == "ތިލަދުންމަތީ އުތުރުބުރީ އުލިގަމު ކައުންސިލްގެ އިދާރާ"
    assert "އުލިގަމު" in first.title
    assert first.published_iso == "2026-10-14T00:00:00"
    assert first.deadline_iso == "2026-10-29T13:00:00"


# ---------------------------------------------------------------------
# Discipline classification tests
# ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "title, expected_discipline",
    [
        # Construction
        ("Upgrading of A.Dh Fenfushi Harbour", "Construction"),
        ("Reconstruction of B.Kamadhoo Harbour", "Construction"),
        ("Design and Construction of Hulhumale Tourist Jetty 2017", "Construction"),
        ("Hulhumale Phase I Major Roads - Road Markings & Asphalt Repair", "Construction"),
        ("Boundary Fence for Telecom Towers, Hulhumale Phase II", "Construction"),
        ("ރަށު ބަނދަރު އަޕްގްރޭޑް ކުރުން", "Construction"),
        ("އިދާރީ ޢިމާރާތް ބިނާކުރުމުގެ މަސައްކަތް", "Construction"),

        # IT
        ("Procurement of Contract Management System and E-signature Services Provider", "IT"),
        ("Supply and Delivery of Computer Systems & Laptops", "IT"),
        ("Installation of Dark Fiber Link between RO Annex and Borehole Office", "IT"),
        ("ކޮމްޕިއުޓަރ ސިސްޓަމްތައް ގަތުން", "IT"),

        # Medical
        ("Supply of Medical Equipment to Indira Gandhi Memorial Hospital", "Medical"),
        ("Setting up Dialysis Clinic in Kulhudhuffushi Regional Hospital", "Medical"),
        ("ހޮސްޕިޓަލަށް ބޭސް ސަޕްލައި ކުރުން", "Medical"),

        # Real Estate & Leasing
        ("Lease, Development and Operation of Tourist Guesthouse in HA. Hoarafushi", "Real Estate & Leasing"),
        ("Space Leasing for MGPL Shop Utilization", "Real Estate & Leasing"),
        ("ބީލަން އުޞޫލުން ފަތްކެޔޮ ދަނޑު ކުއްޔަށް ދޫކުރުން", "Real Estate & Leasing"),
        ("ގެސްޓްހައުސް އެޅުމަށް ބިން ކުއްޔަށް ދިނުން", "Real Estate & Leasing"),

        # Cleaning & Waste Management
        ("Providing Cleaning Services to Worksites under HDC", "Cleaning & Waste Management"),

        # Accounting & Legal
        ("Hiring an Audit Firm for Annual Review", "Accounting & Legal"),

        # Other
        ("Supply and Delivery of Safety Shoes and Gumboots", "Other"),
    ],
)
def test_classify_discipline(title, expected_discipline):
    assert classify_discipline(title) == expected_discipline


def test_classify_notices():
    notices = [
        BidNotice(
            notice_id="1", url="", gazette_type="Work", reference_number="",
            published_iso=None, deadline_iso=None, agency="",
            title="Design and Construction of Jetty",
        ),
        BidNotice(
            notice_id="2", url="", gazette_type="Work", reference_number="",
            published_iso=None, deadline_iso=None, agency="",
            title="Purchase of Desktop Computers",
        ),
    ]
    assert notices[0].discipline is None
    assert notices[1].discipline is None

    result = classify_notices(notices)
    assert result is notices
    assert notices[0].discipline == "Construction"
    assert notices[1].discipline == "IT"

    # Custom classifier callable
    custom = lambda t: "CUSTOM"
    classify_notices(notices, classifier=custom)
    assert notices[0].discipline == "CUSTOM"
    assert notices[1].discipline == "CUSTOM"


# ---------------------------------------------------------------------
# Constants and pattern matching tests
# ---------------------------------------------------------------------

def test_constants():
    assert "beelan" in TYPE_SLUGS
    assert TYPE_SLUGS["beelan"] == "Bid"
    assert "masakkaiy" in TYPE_SLUGS
    assert TYPE_SLUGS["masakkaiy"] == "Work"

    assert "Beelan" in TYPES
    assert "ބީލަން" in TYPES

    assert BID_TITLE_PATTERNS.search("Invitation for Bids for Road Construction")
    assert BID_TITLE_PATTERNS.search("IFB - Supply of Office Equipment")
    assert BID_TITLE_PATTERNS.search("Tender Notice: Security Services")
    assert BID_TITLE_PATTERNS.search("ބީލަން ހުށަހެޅުމުގެ ދަޢުވަތު")


# ---------------------------------------------------------------------
# Network layer mocking tests
# ---------------------------------------------------------------------

def test_fetch_notice_mocked(en_notice_html):
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = en_notice_html
    mock_session.get.return_value = mock_resp

    notice = fetch_notice("166396", session=mock_session)
    mock_session.get.assert_called_once_with(
        "https://gazette.gov.mv/iulaan/print/166396", timeout=15
    )
    assert notice.notice_id == "166396"
    assert notice.title == "Hulhumalé Phase I Major Roads – Road Markings & Asphalt Repair"


def test_fetch_listing_mocked(listing_html):
    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = listing_html
    mock_session.get.return_value = mock_resp

    notices = fetch_listing(type_slug="beelan", page=1, session=mock_session)
    mock_session.get.assert_called_once_with(
        f"{BASE_URL}/iulaan?type=beelan&page=1", timeout=15
    )
    assert len(notices) == 10
