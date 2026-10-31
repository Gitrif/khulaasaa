"""
Shared parser, consolidator, and normalization helpers for Maldivian rental scrapers.
Pure functions with zero database or network dependencies.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

RENTAL_SOURCES = [
    {"name": "iBay Maldives", "domain": "ibay.com.mv", "url": "https://ibay.com.mv/housing-real-estate-b19.html"},
    {"name": "Boahiyaa Real Estate", "domain": "boahiyaa.com", "url": "https://boahiyaa.com/"},
    {"name": "Property.mv", "domain": "property.mv", "url": "https://www.property.mv/"},
    {"name": "Hiyaa.mv Residential", "domain": "hiyaa.mv", "url": "https://www.hiyaa.mv/"},
    {"name": "KobaPages Maldives", "domain": "kobapages.com", "url": "https://kobapages.com/"},
    {"name": "Apex Atoll Properties", "domain": "apexatoll.com", "url": "https://apexatoll.com/"},
]

COMMON_FURNISHED_ITEMS = [
    "Bed & Mattress", "Sofa Set", "Wardrobe", "Dining Table & Chairs",
    "Refrigerator", "Washing Machine", "Water Heaters", "Air Conditioning",
]


def detect_leased_status(text: str) -> bool:
    """Detect if listing text indicates property has already been rented out."""
    t = text.lower()
    return any(w in t for w in ["leased out", "rented", "no longer available", "occupied"])


def consolidate_key(location: str, building: str, floor: str, bedrooms: int) -> str:
    """Generate consolidation matching key for deduplicating cross-portal listings."""
    loc_clean = (location or "").strip().lower()
    bld_clean = (building or "").strip().lower()
    fl_clean = re.sub(r"[^\d]", "", str(floor or ""))
    return f"{loc_clean}|{bld_clean}|{fl_clean}|{bedrooms}bhk"


def extract_lift_and_floors(text: str) -> tuple[int, int, str]:
    """Extract lift availability (0/1), total floors, and listing floor."""
    t = text.lower()
    has_lift = 1 if ("lift" in t or "elevator" in t) and ("no lift" not in t) else 0
    floor_desc = "3rd Floor"
    floor_m = re.search(r"(\d+)(?:st|nd|rd|th)?\s*floor", t)
    if floor_m:
        floor_desc = f"{floor_m.group(1)} Floor"
    b_floors = 6
    b_m = re.search(r"(\d+)\s*(?:storey|story|floors building)", t)
    if b_m:
        b_floors = int(b_m.group(1))
    return has_lift, b_floors, floor_desc


def extract_rooms_and_toilets(text: str) -> tuple[int, int, int]:
    """
    Extract bedrooms, attached toilets, and total toilets from listing text.
    In Maldives, modern apartments allocate an attached bathroom to each bedroom.
    Returns: (bedrooms, attached_toilets, total_toilets)
    """
    t = text.lower()
    beds = 1
    bed_m = re.search(r"(\d+)\s*(?:bhk|bed|room|kothari|k\b)", t)
    if bed_m:
        beds = max(1, int(bed_m.group(1)))

    att = beds
    att_m = re.search(r"(\d+)\s*(?:attached|ensuite|att\b|toilets?\s*attached)", t)
    if att_m:
        parsed = int(att_m.group(1))
        att = parsed if parsed > 0 else beds

    guest_m = re.search(r"(\d+)\s*(?:guest|common|powder)", t)
    if guest_m:
        tot = att + int(guest_m.group(1))
    else:
        tot_m = re.search(r"(\d+)\s*(?:total\s+toilets?|toilets?|baths?|washrooms?)", t)
        tot = max(att, int(tot_m.group(1))) if tot_m else att
    return beds, att, tot


def normalize_location(loc_raw: str) -> tuple[str, str]:
    """Normalize raw Maldivian location string into (location, district)."""
    t = loc_raw.strip().lower()
    if "hulhumale" in t or "hulhumal" in t:
        if "phase 2" in t:
            return "Hulhumale Phase 2", "Hiyaa Flat Area"
        return "Hulhumale Phase 1", "Neighborhood 2"
    elif "henveiru" in t:
        return "Male City", "Henveiru"
    elif "galolhu" in t:
        return "Male City", "Galolhu"
    elif "maafannu" in t or "maafanu" in t:
        return "Male City", "Maafannu"
    elif "machangolhi" in t:
        return "Male City", "Machangolhi"
    return "Male City", "Central"


def _item(
    title: str, loc: str, dist: str, road: str, bld: str, total_f: int,
    f_num: int, f_str: str, unit: str, beds: int, att: int, tot: int, sqft: int,
    lift: int, kitchen: str, living: str, ac: str, heaters: int, furn: str,
    items: list[str], rent: int, sec_rent: Optional[int], sec_src: Optional[str],
    dep: int, src: str, url: str, sec_urls: list[str], img: str,
    parking: str, contact: str, phone: str, desc: str, ams: list[str],
    facs: list[str], adv: int = 0, late: int = 100, avail: str = "Immediate",
) -> dict[str, Any]:
    """Helper to build a normalized apartment listing record."""
    return {
        "title": title, "location": loc, "district": dist, "road": road,
        "plot_building": bld, "building_total_floors": total_f,
        "floor_num": f_num, "floor": f_str, "apartment_unit": unit,
        "bedrooms": beds, "attached_toilets": att, "total_toilets": tot,
        "sqft_size": sqft, "lift": lift, "kitchen_type": kitchen,
        "living_dining_type": living, "ac_details": ac,
        "water_heaters_count": heaters, "furnished": furn,
        "furnished_items": json.dumps(items), "is_serviced": 0,
        "garbage_management": "WAMCO Included",
        "maintenance_terms": "Lessor covers structural repairs and lift servicing",
        "rent_mvr": rent, "secondary_rent_mvr": sec_rent,
        "secondary_rent_source": sec_src, "deposit_mvr": dep,
        "advance_months": adv, "late_fine_mvr_per_day": late,
        "available_date": avail, "source_name": src, "source_url": url,
        "secondary_sources": json.dumps(sec_urls), "is_direct": 0,
        "photo_count": 8, "image_url": img, "parking_type": parking,
        "contact_name": contact, "contact_phone": phone,
        "contact_whatsapp": phone, "contact_email": "",
        "description": desc, "amenities": json.dumps(ams),
        "building_facilities": json.dumps(facs), "is_leased": 0,
    }
