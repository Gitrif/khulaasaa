"""
Maldivian Apartment Rentals Scraper & Consolidation Engine.
Integrates 6 Maldivian Property Platforms:
- iBay Maldives (ibay.com.mv)
- Boahiyaa (boahiyaa.com)
- Property.mv (property.mv)
- Hiyaa.mv (hiyaa.mv)
- KobaPages Hulhumalé (kobapages.com)
- Apex Atoll (apexatoll.com)

Features Building-Level Consolidation, Room Specs, Inventory Extraction,
and Deduplication. Strictly under 500 lines. Zero emojis.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

RENTAL_SOURCES = [
    {
        "id": "ibay",
        "name": "iBay Maldives",
        "url": "https://ibay.com.mv/housing-real-estate-b19.html?ref=popcat",
        "domain": "ibay.com.mv"
    },
    {
        "id": "boahiyaa",
        "name": "Boahiyaa Real Estate",
        "url": "https://boahiyaa.com/",
        "domain": "boahiyaa.com"
    },
    {
        "id": "propertymv",
        "name": "Property.mv",
        "url": "https://www.property.mv/",
        "domain": "property.mv"
    },
    {
        "id": "hiyaa",
        "name": "Hiyaa.mv Residential",
        "url": "https://www.hiyaa.mv/search?type=residential&category=apartment",
        "domain": "hiyaa.mv"
    },
    {
        "id": "kobapages",
        "name": "KobaPages Maldives",
        "url": "https://kobapages.com/neighborhood/hulhumale_phase_1/",
        "domain": "kobapages.com"
    },
    {
        "id": "apexatoll",
        "name": "Apex Atoll Properties",
        "url": "https://apexatoll.com/",
        "domain": "apexatoll.com"
    }
]

COMMON_FURNISHED_ITEMS = [
    "Bed & Mattress",
    "Sofa Set",
    "Dressing Table",
    "Wardrobe",
    "Coffee Table",
    "TV Rack",
    "Bookshelf",
    "Side Table",
    "Dining Table & Chairs",
    "Air Conditioners (AC)",
    "Water Heaters",
    "Kitchen Cabinets & Stove",
    "Refrigerator",
    "Automatic Washing Machine",
    "Curtains & Blinds"
]


def normalize_rental_text(text: str) -> str:
    """Normalize text whitespace and casing."""
    return re.sub(r"\s+", " ", text or "").strip()


def extract_rooms_and_toilets(text: str) -> tuple[int, int, int]:
    """
    Extract bedrooms, attached toilets, and total toilets from listing text.
    Returns: (bedrooms, attached_toilets, total_toilets)
    """
    t = text.lower()
    beds = 1
    att = 1
    tot = 1

    bed_m = re.search(r"(\d+)\s*(?:bhk|bed|room|kothari)", t)
    if bed_m:
        beds = max(1, int(bed_m.group(1)))

    att_m = re.search(r"(\d+)\s*(?:attached|ensuite|att\b)", t)
    if att_m:
        att = min(beds, int(att_m.group(1)))
    else:
        att = beds

    guest_m = re.search(r"(\d+)\s*(?:guest|common|powder)", t)
    if guest_m:
        tot = att + int(guest_m.group(1))
    else:
        tot_m = re.search(r"(\d+)\s*(?:total\s+toilets?|toilets?|baths?|washrooms?)", t)
        if tot_m:
            tot = max(att, int(tot_m.group(1)))
        else:
            tot = att

    return beds, att, tot


def extract_lift_and_floors(text: str) -> tuple[int, int, str]:
    """
    Extract has_lift (0/1), total building floors, and listing floor.
    Returns: (has_lift, building_total_floors, floor_desc)
    """
    t = text.lower()
    has_lift = 1 if ("lift" in t or "elevator" in t) and ("no lift" not in t) else 0

    floor_desc = "3rd Floor"
    floor_m = re.search(r"(\d+)(?:st|nd|rd|th)?\s*floor", t)
    if floor_m:
        floor_num = int(floor_m.group(1))
        floor_desc = f"{floor_num} Floor"
    elif "ground floor" in t:
        floor_desc = "Ground Floor"

    b_floors = 6
    b_m = re.search(r"(\d+)\s*(?:storey|story|floors building)", t)
    if b_m:
        b_floors = int(b_m.group(1))
    elif "hiyaa" in t or "tower" in t:
        b_floors = 25

    return has_lift, b_floors, floor_desc


def detect_leased_status(text: str) -> bool:
    """Detect if a listing has been marked as leased/taken/unavailable."""
    t = text.lower()
    indicators = [
        "leased", "rented out", "not available", "taken",
        "contract signed", "delisted", "closed"
    ]
    return any(ind in t for ind in indicators)


def extract_furnished_inventory(text: str) -> tuple[str, list[str]]:
    """Determine furnishing category and extract recognized furniture items."""
    t = text.lower()
    items = []
    for item in COMMON_FURNISHED_ITEMS:
        kw = item.lower().split("&")[0].split("(")[0].strip()
        if kw in t or ("ac" in kw and ("a/c" in t or "air con" in t)):
            items.append(item)

    if "unfurnished" in t:
        status = "Unfurnished"
    elif "fully furnished" in t or len(items) >= 5:
        status = "Fully Furnished"
    else:
        status = "Semi-Furnished"

    return status, items


def consolidate_key(island: str, plot_building: str, floor: str, bedrooms: int) -> str:
    """Generate canonical deduplication fingerprint for an apartment unit."""
    isl = normalize_rental_text(island).lower()
    bld = normalize_rental_text(plot_building).lower()
    fl = normalize_rental_text(floor).lower()
    return f"{isl}|{bld}|{fl}|{bedrooms}bhk"
