"""
Mock in-memory data for UI mockup phase.

This module stands in for the Phase 2/3 SQLite schema. The shapes here
(especially `article_timelines`) mirror the eventual many-to-many junction
table so the templates and route handlers don't need to change when the
real DB lands.
"""
from datetime import datetime

# --- Reference tag list (editorial macro-narratives) -----------------------
# Phase 1 assumption: pre-defined by editors, see README "Open questions".
TIMELINE_TAGS = {
    "mmprc": {"id": "mmprc", "label": "MMPRC Scandal", "color": "#B3432B"},
    "yameen": {"id": "yameen", "label": "Yameen Legal Cases", "color": "#2F7C74"},
    "adeeb": {"id": "adeeb", "label": "Ahmed Adeeb", "color": "#C89B3C"},
    "bridge": {"id": "bridge", "label": "Thilamalé Bridge Project", "color": "#5B6572"},
}

SOURCES = {
    "mihaaru": {"id": "mihaaru", "name": "Mihaaru", "initial": "M", "kind": "press"},
    "cnm": {"id": "cnm", "name": "CNM", "initial": "C", "kind": "press"},
    "haftha": {"id": "haftha", "name": "Haftha", "initial": "H", "kind": "press"},
    "sun": {"id": "sun", "name": "Sun Online", "initial": "S", "kind": "press"},
    # Primary/official sources -- not press outlets, so badged distinctly
    # (kind="official") rather than mixed in with newsroom badges.
    "mira": {"id": "mira", "name": "MIRA", "initial": "R", "kind": "official"},
    "gazette": {"id": "gazette", "name": "Gazette.mv", "initial": "G", "kind": "official"},
    # Breaking-news wire accounts (independent/citizen desks that post first,
    # ahead of press write-ups) -- badged distinctly again (kind="wire") so
    # a reader can tell "first report, unverified breadth" from "outlet
    # cross-checked coverage". "MV Crisis" stands in for the kind of fast,
    # single-account crisis-tracking feed you follow directly.
    "mvcrisis": {"id": "mvcrisis", "name": "MV Crisis", "initial": "W", "kind": "wire"},
}

# --- Informative topic labels for general/breaking items -------------------
# Distinct from TIMELINE_TAGS: these are single-story subject labels, not
# multi-milestone narrative tracks. A general item can carry a topic without
# ever needing a /timeline/{story_id} page.
TOPICS = {
    "tax": {"id": "tax", "label": "Tax & Revenue", "color": "#2F7C74"},
    "policy": {"id": "policy", "label": "Policy & Governance", "color": "#5B6572"},
    "health": {"id": "health", "label": "Health", "color": "#B3432B"},
    "economy": {"id": "economy", "label": "Economy", "color": "#C89B3C"},
    "weather": {"id": "weather", "label": "Weather", "color": "#2F7C74"},
}

# --- Unified events (public feed cards) -------------------------------------
# `section` drives which of the three feed zones an item lands in:
#   "breaking" -> short-lived, time-sensitive, no story_id needed
#   "major"    -> multi-source, cross-checked, tracked narrative (has a
#                 /timeline/{story_id} page and a TIMELINE_TAGS entry)
#   "general"  -> everyday informative/policy items, single source is fine,
#                 carries a TOPICS label instead of a narrative tag
EVENTS = [
    {
        "id": "evt-1042",
        "headline": "Supreme Court sets new hearing date in Yameen appeal",
        "summary": (
            "The Supreme Court has scheduled a fresh hearing in former "
            "President Yameen's appeal, after procedural delays pushed "
            "the case back twice this month."
        ),
        "published_raw": "25 ސެޕްޓެމްބަރ 2026",
        "published_iso": "2026-09-25",
        "sources": ["mihaaru", "cnm", "haftha"],
        "tags": ["yameen"],
        "section": "major",
        "story_id": "yameen-appeal-2026",
    },
    {
        "id": "evt-1041",
        "headline": "Auditor General flags new discrepancy in MMPRC follow-up report",
        "summary": (
            "A follow-up audit points to unresolved discrepancies in "
            "asset recovery tied to the MMPRC case, reigniting parliamentary "
            "questions this week."
        ),
        "published_raw": "24 ސެޕްޓެމްބަރ 2026",
        "published_iso": "2026-09-24",
        "sources": ["mihaaru", "sun"],
        "tags": ["mmprc"],
        "section": "major",
        "story_id": "mmprc-followup-2026",
    },
    {
        "id": "evt-1040",
        "headline": "Adeeb legal team files motion referencing MMPRC evidence",
        "summary": (
            "Lawyers representing Ahmed Adeeb submitted a motion this "
            "week citing evidence shared across the MMPRC proceedings, "
            "linking the two tracks explicitly for the first time."
        ),
        "published_raw": "23 ސެޕްޓެމްބަރ 2026",
        "published_iso": "2026-09-23",
        "sources": ["cnm", "haftha"],
        # Deliberately in two timelines at once - exercises the junction table
        "tags": ["adeeb", "mmprc"],
        "section": "major",
        "story_id": "adeeb-track-2026",
    },
    {
        "id": "evt-1039",
        "headline": "Thilamalé Bridge project enters second funding phase",
        "summary": (
            "Government officials confirmed a second phase of external "
            "financing for the Thilamalé Bridge project, with construction "
            "timelines unchanged for now."
        ),
        "published_raw": "22 ސެޕްޓެމްބަރ 2026",
        "published_iso": "2026-09-22",
        "sources": ["mihaaru", "cnm", "sun"],
        "tags": ["bridge"],
        "section": "major",
        "story_id": "bridge-funding-2026",
    },

    # --- Breaking: short-lived, time-sensitive, no story_id required --------
    # Deliberately mixed sources -- a wire feed reads as urgent partly
    # because it's visibly pulling from more than one desk at once.
    {
        "id": "evt-1051",
        "headline": "Reports of large gathering forming near Republic Square",
        "summary": "Unconfirmed reports of a crowd gathering; police presence increasing.",
        "published_raw": "25 ސެޕްޓެމްބަރ 2026, 17:05",
        "published_iso": "2026-09-25T17:05",
        "minutes_ago": 4,
        "sources": ["mvcrisis"],
        "tags": [],
        "topic": None,
        "section": "breaking",
    },
    {
        "id": "evt-1050",
        "headline": "MIRA extends Q3 GST filing deadline by one week",
        "summary": (
            "The Maldives Inland Revenue Authority pushed the Q3 GST filing "
            "deadline to 5 October, citing a technical issue on its online "
            "portal earlier this week."
        ),
        "published_raw": "25 ސެޕްޓެމްބަރ 2026, 16:40",
        "published_iso": "2026-09-25T16:40",
        "minutes_ago": 29,
        "sources": ["mira"],
        "tags": [],
        "topic": "tax",
        "section": "breaking",
    },
    {
        "id": "evt-1049b",
        "headline": "Mihaaru: police confirm road closure on Boduthakurufaanu Magu",
        "summary": "Closure in effect until further notice; diversions posted.",
        "published_raw": "25 ސެޕްޓެމްބަރ 2026, 15:52",
        "published_iso": "2026-09-25T15:52",
        "minutes_ago": 77,
        "sources": ["mihaaru"],
        "tags": [],
        "topic": None,
        "section": "breaking",
    },
    {
        "id": "evt-1049",
        "headline": "Met Office lifts yellow weather alert for northern atolls",
        "summary": (
            "The warning issued Wednesday over rough seas has been "
            "downgraded; small craft are still advised to exercise caution "
            "through the weekend."
        ),
        "published_raw": "25 ސެޕްޓެމްބަރ 2026, 12:15",
        "published_iso": "2026-09-25T12:15",
        "minutes_ago": 314,
        "sources": ["cnm"],
        "tags": [],
        "topic": "weather",
        "section": "breaking",
    },

    # --- General: everyday informative / policy items, single source is ----
    # fine, no cross-checking narrative required.
    {
        "id": "evt-1048",
        "headline": "Cabinet approves new fisheries subsidy framework",
        "summary": (
            "The framework, published in today's gazette, sets tiered fuel "
            "subsidies for pole-and-line vessels starting next quarter."
        ),
        "published_raw": "25 ސެޕްޓެމްބަރ 2026",
        "published_iso": "2026-09-25",
        "sources": ["gazette"],
        "tags": [],
        "topic": "policy",
        "section": "general",
    },
    {
        "id": "evt-1047",
        "headline": "Health Ministry announces free hepatitis B screening drive",
        "summary": (
            "Screening will run at island health centres through October, "
            "part of a wider push to close gaps in routine immunity checks."
        ),
        "published_raw": "24 ސެޕްޓެމްބަރ 2026",
        "published_iso": "2026-09-24",
        "sources": ["mihaaru"],
        "tags": [],
        "topic": "health",
        "section": "general",
    },
    {
        "id": "evt-1046",
        "headline": "Import duty schedule updated for construction materials",
        "summary": (
            "MIRA's revised schedule lowers duty on select cement and "
            "steel imports, effective from the start of next month."
        ),
        "published_raw": "24 ސެޕްޓެމްބަރ 2026",
        "published_iso": "2026-09-24",
        "sources": ["mira"],
        "tags": [],
        "topic": "tax",
        "section": "general",
    },
    {
        "id": "evt-1045",
        "headline": "Civil Aviation publishes new drone operation guidelines",
        "summary": (
            "The gazette notice sets registration and no-fly-zone rules "
            "for recreational and commercial drone operators."
        ),
        "published_raw": "23 ސެޕްޓެމްބަރ 2026",
        "published_iso": "2026-09-23",
        "sources": ["gazette"],
        "tags": [],
        "topic": "policy",
        "section": "general",
    },
    {
        "id": "evt-1044",
        "headline": "Central bank holds policy rate steady",
        "summary": (
            "The Maldives Monetary Authority cited stable inflation and "
            "tourism receipts in its decision to leave rates unchanged."
        ),
        "published_raw": "22 ސެޕްޓެމްބަރ 2026",
        "published_iso": "2026-09-22",
        "sources": ["sun"],
        "tags": [],
        "topic": "economy",
        "section": "general",
    },
]

# --- Timeline milestones (many-to-many: one milestone -> many outlets) -----
TIMELINES = {
    "mmprc-followup-2026": {
        "story_id": "mmprc-followup-2026",
        "title": "MMPRC Scandal",
        "tag": "mmprc",
        "milestones": [
            {
                "id": "m-1",
                "date_raw": "24 ސެޕްޓެމްބަރ 2026",
                "date_iso": "2026-09-24",
                "headline": "Auditor General flags new discrepancy in follow-up report",
                "detail": (
                    "The latest audit cycle identifies unresolved gaps in "
                    "recovered assets, prompting fresh parliamentary review."
                ),
                "sources": ["mihaaru", "sun"],
            },
            {
                "id": "m-2",
                "date_raw": "23 ސެޕްޓެމްބަރ 2026",
                "date_iso": "2026-09-23",
                "headline": "Adeeb motion cites shared MMPRC evidence",
                "detail": (
                    "A filing from Adeeb's legal team references material "
                    "originating in the MMPRC case file."
                ),
                "sources": ["cnm", "haftha"],
            },
            {
                "id": "m-3",
                "date_raw": "02 ސެޕްޓެމްބަރ 2026",
                "date_iso": "2026-09-02",
                "headline": "Parliamentary committee reopens asset-recovery review",
                "detail": (
                    "The oversight committee voted to reopen review sessions "
                    "on recovered MMPRC-linked assets."
                ),
                "sources": ["mihaaru", "cnm", "haftha"],
            },
        ],
    },
    "yameen-appeal-2026": {
        "story_id": "yameen-appeal-2026",
        "title": "Yameen Legal Cases",
        "tag": "yameen",
        "milestones": [
            {
                "id": "m-1",
                "date_raw": "25 ސެޕްޓެމްބަރ 2026",
                "date_iso": "2026-09-25",
                "headline": "Supreme Court sets new hearing date",
                "detail": "A fresh hearing date follows two procedural delays.",
                "sources": ["mihaaru", "cnm", "haftha"],
            },
            {
                "id": "m-2",
                "date_raw": "11 ސެޕްޓެމްބަރ 2026",
                "date_iso": "2026-09-11",
                "headline": "Hearing postponed on procedural grounds",
                "detail": "The court cited incomplete filings from the defense.",
                "sources": ["mihaaru", "sun"],
            },
        ],
    },
}

# --- Pending clusters awaiting editor approval (admin console) -------------
PENDING_CLUSTERS = [
    {
        "id": "cluster-501",
        "draft_headline": "Election Commission responds to boundary complaint",
        "article_count": 4,
        "sources": ["mihaaru", "cnm", "sun"],
        "suggested_tags": ["yameen"],
        "confidence": 0.91,
        "received_raw": "25 ސެޕްޓެމްބަރ 2026, 14:20",
    },
    {
        "id": "cluster-502",
        "draft_headline": "New witness named in MMPRC-linked testimony",
        "article_count": 6,
        "sources": ["mihaaru", "cnm", "haftha", "sun"],
        "suggested_tags": ["mmprc", "adeeb"],
        "confidence": 0.86,
        "received_raw": "25 ސެޕްޓެމްބަރ 2026, 11:05",
    },
    {
        "id": "cluster-503",
        "draft_headline": "Contractor statement on Thilamalé Bridge delay rumors",
        "article_count": 3,
        "sources": ["cnm", "sun"],
        "suggested_tags": ["bridge"],
        "confidence": 0.78,
        "received_raw": "24 ސެޕްޓެމްބަރ 2026, 19:40",
    },
]

# --- Most read / trending (sidebar social-proof rail) ----------------------
TRENDING = [
    {"rank": 1, "headline": "Supreme Court sets new hearing date in Yameen appeal", "story_id": "yameen-appeal-2026"},
    {"rank": 2, "headline": "MIRA extends Q3 GST filing deadline by one week", "story_id": None},
    {"rank": 3, "headline": "Auditor General flags new discrepancy in MMPRC follow-up report", "story_id": "mmprc-followup-2026"},
    {"rank": 4, "headline": "Central bank holds policy rate steady", "story_id": None},
    {"rank": 5, "headline": "Adeeb legal team files motion referencing MMPRC evidence", "story_id": "adeeb-track-2026"},
]

# --- Bids (from gazette.gov.mv) ---------------------------------------
# These 12 are REAL notices pulled and verified against the live site
# (see scrapers/gazette.py + scrapers/README.md for the research trail).
# Not invented placeholder data -- reference numbers, agencies, titles,
# and dates as actually published. Discipline is our own classification
# layer (scrapers/gazette.py: classify_discipline), since gazette.gov.mv
# has no discipline taxonomy for bids -- confirmed during research.
BIDS = [
    {"ref": "TES/2020/W-021", "agency": "Ministry of Finance (for MNPI)", "title": "Upgrading of A.Dh Fenfushi Harbour", "discipline": "Construction", "gazette_type": "Work", "deadline_iso": None, "source_url": "https://gazette.gov.mv/iulaan/view/127322"},
    {"ref": "TES/2020/W-022", "agency": "Ministry of Finance (for MNPI)", "title": "Reconstruction of B.Kamadhoo Harbour", "discipline": "Construction", "gazette_type": "Work", "deadline_iso": None, "source_url": "https://gazette.gov.mv/iulaan/view/127322"},
    {"ref": "TES/2021/G-019", "agency": "Ministry of Finance", "title": "Procurement of Contract Management System and E-signature Services Provider", "discipline": "IT", "gazette_type": "Goods", "deadline_iso": None, "source_url": "https://gazette.gov.mv/iulaan/169039"},
    {"ref": "HDC(161)-PRO/IU/2021/168", "agency": "Housing Development Corporation", "title": "Supply and Delivery of Safety Shoes and Gumboots", "discipline": "Other", "gazette_type": "Work", "deadline_iso": "2021-05-18T10:00:00", "source_url": "https://www.gazette.gov.mv/iulaan/view/149717"},
    {"ref": "HDC(161)-PRO/IU/2017/162", "agency": "Housing Development Corporation", "title": "Design and Construction of Hulhumale Tourist Jetty 2017", "discipline": "Construction", "gazette_type": "Work", "deadline_iso": "2017-12-19T14:00:00", "source_url": "https://gazette.gov.mv/iulaan/print/72670"},
    {"ref": "HDC(161)-PRO/IU/2020/259", "agency": "Housing Development Corporation", "title": "Supply and Delivery of Computer Systems & Laptops", "discipline": "IT", "gazette_type": "Work", "deadline_iso": "2020-12-01T13:00:00", "source_url": "https://gazette.gov.mv/iulaan/print/137279"},
    {"ref": "HDC(161)-PWM/IU/2021/600", "agency": "Housing Development Corporation", "title": "Boundary Fence for Telecom Towers, Hulhumale Phase II", "discipline": "Construction", "gazette_type": "Work", "deadline_iso": None, "source_url": "https://gazette.gov.mv/iulaan/172228"},
    {"ref": "HDC(161)-PWM/IU/2021/520", "agency": "Housing Development Corporation", "title": "Hulhumale Phase I Major Roads - Road Markings & Asphalt Repair", "discipline": "Construction", "gazette_type": "Work", "deadline_iso": "2021-11-02T11:00:00", "source_url": "https://gazette.gov.mv/iulaan/print/166396"},
    {"ref": "HDC(161)-PRO/IU/2021/122", "agency": "Housing Development Corporation", "title": "Providing Cleaning Services to Worksites under HDC", "discipline": "Other", "gazette_type": "Work", "deadline_iso": "2021-04-04T13:00:00", "source_url": "https://gazette.gov.mv/iulaan/print/147117"},
    {"ref": None, "agency": "HA. Hoarafushi Council", "title": "Lease, Development and Operation of Tourist Guesthouse in HA. Hoarafushi", "discipline": "Real Estate & Leasing", "gazette_type": "Bid", "deadline_iso": None, "source_url": "https://gazette.gov.mv/iulaan"},
    {"ref": None, "agency": "Ministry of Tourism", "title": "Space Leasing for MGPL Shop Utilization", "discipline": "Real Estate & Leasing", "gazette_type": "Bid", "deadline_iso": None, "source_url": "https://gazette.gov.mv/iulaan"},
    {"ref": None, "agency": "Secretariat of V.Fulidhoo Council", "title": "Construction and Other Services for the Finishing Work of V.Fulidhoo Police Post", "discipline": "Construction", "gazette_type": "Work", "deadline_iso": None, "source_url": "https://gazette.gov.mv/iulaan"},
]

# --- Jobs (from gazette.gov.mv, type=Vazheefaage Furusathu) -----------
# Mock data (unlike BIDS above, not pulled live this session) -- but the
# discipline field here mirrors gazette's OWN real job-category taxonomy
# confirmed during research (Construction, IT, Health/Medical, Finance,
# Legal, etc. are real category values on the site, unlike bids where we
# had to invent the taxonomy ourselves).
JOBS = [
    {"id": "job-1", "title": "Civil Engineer", "agency": "Ministry of National Planning and Infrastructure", "discipline": "Construction", "location": "Male'", "deadline_iso": "2026-10-10T14:00:00", "published_raw": "28 ސެޕްޓެމްބަރ 2026"},
    {"id": "job-2", "title": "IT Systems Administrator", "agency": "Maldives Inland Revenue Authority", "discipline": "IT", "location": "Male'", "deadline_iso": "2026-10-08T13:00:00", "published_raw": "27 ސެޕްޓެމްބަރ 2026"},
    {"id": "job-3", "title": "Staff Nurse", "agency": "Indira Gandhi Memorial Hospital", "discipline": "Medical", "location": "Male'", "deadline_iso": "2026-10-15T13:00:00", "published_raw": "26 ސެޕްޓެމްބަރ 2026"},
    {"id": "job-4", "title": "Site Supervisor", "agency": "Housing Development Corporation", "discipline": "Construction", "location": "Hulhumale'", "deadline_iso": "2026-10-05T13:00:00", "published_raw": "25 ސެޕްޓެމްބަރ 2026"},
    {"id": "job-5", "title": "Accountant", "agency": "State Trading Organization", "discipline": "Finance", "location": "Male'", "deadline_iso": "2026-10-12T13:00:00", "published_raw": "24 ސެޕްޓެމްބަރ 2026"},
]


# In-memory approval log the mock POST endpoint writes to, so the demo
# shows state changing without stuttering / a full page reload.
APPROVAL_LOG = []


def approve_cluster(cluster_id: str, tag_ids: list[str]):
    APPROVAL_LOG.append(
        {
            "cluster_id": cluster_id,
            "tags": tag_ids,
            "approved_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
    )
    global PENDING_CLUSTERS
    PENDING_CLUSTERS = [c for c in PENDING_CLUSTERS if c["id"] != cluster_id]
    return APPROVAL_LOG[-1]
