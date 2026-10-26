from __future__ import annotations

"""
News Sources, Publishers, and Topic Taxonomies for Khulaasaa.

Canonical narrative taxonomies, sources, running story tracks, and editorial constants.
This replaces the mock data file with production-ready definitions for Maldivian news
aggregation, timeline tracking, and multi-source cross-checking.
"""
from datetime import datetime, timezone
from typing import Any, Optional

SOURCES: dict[str, dict[str, Any]] = {
    "standard": {
        "id": "standard",
        "name": "The Standard",
        "initial": "S",
        "kind": "press",
        "domain": "standard.mv",
        "logo": "/static/logos/standard.png",
    },
    "sun": {
        "id": "sun",
        "name": "Sun Online",
        "initial": "S",
        "kind": "press",
        "domain": "sun.mv",
        "logo": "/static/logos/sun.png",
    },
    "atolltimes": {
        "id": "atolltimes",
        "name": "Atoll Times",
        "initial": "A",
        "kind": "press",
        "domain": "atolltimes.mv",
        "logo": "/static/logos/atolltimes.svg",
    },
    "dhauru": {
        "id": "dhauru",
        "name": "Dhauru",
        "initial": "D",
        "kind": "press",
        "domain": "dhauru.com",
        "logo": "/static/logos/dhauru.png",
    },
    "haftha": {
        "id": "haftha",
        "name": "Haftha",
        "initial": "H",
        "kind": "press",
        "domain": "haftha.mv",
        "logo": "/static/logos/haftha.png",
    },
    "adhadhu": {
        "id": "adhadhu",
        "name": "Adhadhu",
        "initial": "A",
        "kind": "press",
        "domain": "adhadhu.com",
        "logo": "/static/logos/adhadhu.png",
    },
    "psm": {
        "id": "psm",
        "name": "PSM News",
        "initial": "P",
        "kind": "official",
        "domain": "psmnews.mv",
        "logo": "/static/logos/psm.png",
    },
    "mvcrisis": {
        "id": "mvcrisis",
        "name": "MV Crisis",
        "initial": "C",
        "kind": "wire",
        "domain": "t.me/MvCrisis",
        "logo": "/static/logos/mvcrisis.svg",
    },
    "mihaaru": {
        "id": "mihaaru",
        "name": "Mihaaru",
        "initial": "M",
        "kind": "press",
        "domain": "mihaaru.com",
        "logo": "/static/logos/mihaaru.png",
    },
    "cnm": {
        "id": "cnm",
        "name": "CNM",
        "initial": "C",
        "kind": "press",
        "domain": "cnm.mv",
        "logo": "/static/logos/cnm.png",
    },
    "edition": {
        "id": "edition",
        "name": "The Edition",
        "initial": "E",
        "kind": "press",
        "domain": "edition.mv",
        "logo": "/static/logos/edition.png",
    },
    "avas": {
        "id": "avas",
        "name": "AVAS",
        "initial": "A",
        "kind": "press",
        "domain": "avas.mv",
        "logo": "/static/logos/avas.png",
    },
    "mira": {
        "id": "mira",
        "name": "MIRA",
        "initial": "R",
        "kind": "official",
        "domain": "mira.gov.mv",
        "logo": "/static/logos/mira.png",
    },
    "gazette": {
        "id": "gazette",
        "name": "Gazette.mv",
        "initial": "G",
        "kind": "official",
        "domain": "gazette.gov.mv",
        "logo": "/static/logos/gazette.svg",
    },
    "miadhu": {
        "id": "miadhu",
        "name": "Miadhu",
        "initial": "M",
        "kind": "press",
        "domain": "miadhu.mv",
        "logo": "/static/logos/miadhu.png",
    },
    "voice": {
        "id": "voice",
        "name": "Voice",
        "initial": "V",
        "kind": "press",
        "domain": "voice.mv",
        "logo": "/static/logos/voice.png",
    },
}

# --- Canonical System-wide Sources Directory ---------------------------------
INITIAL_SOURCES: list[dict[str, Any]] = [
    # News & Media Outlets
    {"slug": "standard", "name": "The Standard", "domain": "standard.mv", "source_type": "press", "logo_url": "/static/logos/standard.png"},
    {"slug": "sun", "name": "Sun Online", "domain": "sun.mv", "source_type": "press", "logo_url": "/static/logos/sun.png"},
    {"slug": "atolltimes", "name": "Atoll Times", "domain": "atolltimes.mv", "source_type": "press", "logo_url": "/static/logos/atolltimes.svg"},
    {"slug": "dhauru", "name": "Dhauru", "domain": "dhauru.com", "source_type": "press", "logo_url": "/static/logos/dhauru.png"},
    {"slug": "haftha", "name": "Haftha", "domain": "haftha.mv", "source_type": "press", "logo_url": "/static/logos/haftha.png"},
    {"slug": "adhadhu", "name": "Adhadhu", "domain": "adhadhu.com", "source_type": "press", "logo_url": "/static/logos/adhadhu.png"},
    {"slug": "psm", "name": "PSM News", "domain": "psmnews.mv", "source_type": "official", "logo_url": "/static/logos/psm.png"},
    {"slug": "mvcrisis", "name": "MV Crisis", "domain": "t.me/MvCrisis", "source_type": "wire", "logo_url": "/static/logos/mvcrisis.svg"},
    {"slug": "mihaaru", "name": "Mihaaru", "domain": "mihaaru.com", "source_type": "press", "logo_url": "/static/logos/mihaaru.png"},
    {"slug": "cnm", "name": "CNM", "domain": "cnm.mv", "source_type": "press", "logo_url": "/static/logos/cnm.png"},
    {"slug": "edition", "name": "The Edition", "domain": "edition.mv", "source_type": "press", "logo_url": "/static/logos/edition.png"},
    {"slug": "avas", "name": "AVAS", "domain": "avas.mv", "source_type": "press", "logo_url": "/static/logos/avas.png"},
    {"slug": "mira", "name": "MIRA", "domain": "mira.gov.mv", "source_type": "official", "logo_url": "/static/logos/mira.png"},
    {"slug": "miadhu", "name": "Miadhu", "domain": "miadhu.mv", "source_type": "press", "logo_url": "/static/logos/miadhu.png"},
    {"slug": "voice", "name": "Voice", "domain": "voice.mv", "source_type": "press", "logo_url": "/static/logos/voice.png"},
    # Government Gazette & Public Portals
    {"slug": "gazette", "name": "Government Gazette", "domain": "gazette.gov.mv", "source_type": "official", "logo_url": "/static/logos/gazette.svg"},
    {"slug": "macl", "name": "Maldives Airports Company Limited", "domain": "macl.aero", "source_type": "portal", "logo_url": "/static/logos/macl.svg"},
    {"slug": "hdc", "name": "Housing Development Corporation", "domain": "hdc.mv", "source_type": "portal", "logo_url": "/static/logos/hdc.svg"},
    {"slug": "mwsc", "name": "Male' Water & Sewerage Company", "domain": "mwsc.com.mv", "source_type": "portal", "logo_url": "/static/logos/mwsc.svg"},
    {"slug": "stelco", "name": "State Electric Company Limited", "domain": "stelco.com.mv", "source_type": "portal", "logo_url": "/static/logos/stelco.svg"},
    {"slug": "sto", "name": "State Trading Organization Plc", "domain": "sto.mv", "source_type": "portal", "logo_url": "/static/logos/sto.svg"},
    # Employment Portals
    {"slug": "jobcenter", "name": "JobCenter Maldives", "domain": "jobcenter.mv", "source_type": "official", "logo_url": "/static/logos/jobcenter.svg"},
    # Classifieds & Real Estate Marketplaces
    {"slug": "ibay", "name": "iBay Maldives", "domain": "ibay.com.mv", "source_type": "marketplace", "logo_url": "/static/logos/ibay.png"},
    {"slug": "boahiyaa", "name": "Boahiyaa Real Estate", "domain": "boahiyaa.com", "source_type": "marketplace", "logo_url": "/static/logos/boahiyaa.png"},
    {"slug": "direct", "name": "Direct Owner / Landlord", "domain": None, "source_type": "marketplace", "logo_url": "/static/logos/direct.svg"},
    # Obituaries / Janaza Channels
    {"slug": "kashunamaadhu", "name": "KashunamaadhuMV", "domain": "t.me/KashunamaadhuMV", "source_type": "wire", "logo_url": "/static/logos/kashunamaadhu.svg"},
]

# --- National Running Stories (Multi-Milestone Editorial Tracks) -------------
TIMELINE_TAGS: dict[str, dict[str, str]] = {
    "traffic-reform": {
        "id": "traffic-reform",
        "label": "Greater Malé Traffic Ban",
        "color": "#B3432B",
    },
    "ras-male": {
        "id": "ras-male",
        "label": "Ras Malé Project",
        "color": "#2F7C74",
    },
    "utility-merger": {
        "id": "utility-merger",
        "label": "Fenaka & STELCO Restructuring",
        "color": "#C89B3C",
    },
    "diplomacy": {
        "id": "diplomacy",
        "label": "President Muizzu State Visits",
        "color": "#5B6572",
    },
    "5m-trees": {
        "id": "5m-trees",
        "label": "5 Million Trees Project",
        "color": "#2F7C74",
    },
    "atoll-operations": {
        "id": "atoll-operations",
        "label": "Counter-Narcotics Operations",
        "color": "#B3432B",
    },
    "sultan-park": {
        "id": "sultan-park",
        "label": "Sultan Park Redevelopment",
        "color": "#2F7C74",
    },
    "tgst-tax": {
        "id": "tgst-tax",
        "label": "TGST & Tourism Tax",
        "color": "#C89B3C",
    },
    "green-tax": {
        "id": "green-tax",
        "label": "Green Tax & Levies",
        "color": "#2F7C74",
    },
    "bridge-safety": {
        "id": "bridge-safety",
        "label": "Sinamalé Bridge & Highway",
        "color": "#B3432B",
    },
    "presidential-speeches": {
        "id": "presidential-speeches",
        "label": "President Muizzu Remarks",
        "color": "#5B6572",
    },
}

# --- Informative Topic Labels for General / Breaking News --------------------
TOPICS: dict[str, dict[str, str]] = {
    "policy": {
        "id": "policy",
        "label": "Policy & Governance",
        "color": "#5B6572",
    },
    "economy": {
        "id": "economy",
        "label": "Economy & Markets",
        "color": "#C89B3C",
    },
    "infrastructure": {
        "id": "infrastructure",
        "label": "Infrastructure & Urban",
        "color": "#2F7C74",
    },
    "weather": {
        "id": "weather",
        "label": "Weather & Marine Alerts",
        "color": "#2F7C74",
    },
    "crime": {
        "id": "crime",
        "label": "Law Enforcement & Justice",
        "color": "#B3432B",
    },
    "health": {
        "id": "health",
        "label": "Health & Safety",
        "color": "#B3432B",
    },
}

# --- Current Trending Stories (Sidebar Social-Proof Rail) --------------------
TRENDING: list[dict[str, Any]] = [
    {
        "rank": 1,
        "headline": "Heavy vehicles and goods transport restricted during peak hours in Greater Malé",
        "story_id": "male-traffic-ban",
    },
    {
        "rank": 2,
        "headline": "Ras Malé land reclamation and eco-city development progress",
        "story_id": "ras-male-project",
    },
    {
        "rank": 3,
        "headline": "Cabinet initiates Fenaka Corporation merger with STELCO",
        "story_id": "fenaka-stelco-merger",
    },
    {
        "rank": 4,
        "headline": "President Dr. Muizzu undertakes official bilateral visit to Pakistan",
        "story_id": None,
    },
    {
        "rank": 5,
        "headline": "Police launch major counter-narcotics sweep across northern atolls",
        "story_id": None,
    },
]

# --- Story Timelines (Many-to-Many Milestones with Multi-Outlet Coverage) -----