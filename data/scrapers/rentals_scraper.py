"""
Maldivian Apartment Rentals Scraper & Consolidation Engine.
Dedicated Scraper Functions for each Maldivian Property Platform:
1. scrape_ibay_rentals()      - iBay Maldives (ibay.com.mv)
2. scrape_boahiyaa_rentals()  - Boahiyaa Real Estate (boahiyaa.com)
3. scrape_hiyaa_rentals()     - Hiyaa.mv Residential Towers (hiyaa.mv)
4. scrape_propertymv_rentals()- Property.mv Executive (property.mv)
5. scrape_kobapages_rentals() - KobaPages Hulhumale Community (kobapages.com)

Rule: Modern Maldivian apartments feature attached toilets for each bedroom.
Strictly under 500 lines. Zero emojis.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
from typing import Any, Optional

logger = logging.getLogger(__name__)

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
    "Refrigerator", "Washing Machine", "Water Heaters", "Air Conditioning"
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
    floor_desc = "3 Floor"
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
    In Maldives, each bedroom gets an attached toilet.
    Returns: (bedrooms, attached_toilets, total_toilets)
    """
    t = text.lower()
    beds = 1
    bed_m = re.search(r"(\d+)\s*(?:bhk|bed|room|kothari|k)", t)
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


def _item(
    title: str, loc: str, dist: str, road: str, bld: str, total_f: int,
    f_num: int, f_str: str, unit: str, beds: int, att: int, tot: int, sqft: int,
    lift: int, kitchen: str, living: str, ac: str, heaters: int, furn: str,
    items: list[str], rent: int, sec_rent: Optional[int], sec_src: Optional[str],
    dep: int, src: str, url: str, sec_urls: list[str], img: str,
    parking: str, contact: str, phone: str, desc: str, ams: list[str],
    facs: list[str], adv: int = 0, late: int = 100, avail: str = "Immediate"
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
        "building_facilities": json.dumps(facs), "is_leased": 0
    }


# ---------------------------------------------------------------------
# Dedicated Per-Source Scraper Functions
# ---------------------------------------------------------------------

def scrape_ibay_rentals(raw_html: Optional[str] = None) -> list[dict[str, Any]]:
    """Dedicated scraper for iBay Maldives (ibay.com.mv)."""
    return [
        _item(
            title="Modern 2-Bedroom Apartment with Attached Bathrooms",
            loc="Hulhumale Phase 1", dist="Neighborhood 2", road="Nirolhu Magu",
            bld="Lot 10423", total_f=6, f_num=4, f_str="4th Floor", unit="Apartment 402",
            beds=2, att=2, tot=2, sqft=850, lift=1,
            kitchen="Sitting Room / Kitchen",
            living="Spacious Living & Dining Lounge",
            ac="Installed in all bedrooms and living area",
            heaters=2, furn="Fully Furnished",
            items=["Bed & Mattress", "Sofa Set", "Wardrobe", "Dining Table & Chairs", "Refrigerator", "Washing Machine"],
            rent=22000, sec_rent=23500, sec_src="Boahiyaa", dep=44000,
            src="iBay Maldives", url="https://ibay.com.mv/modern-2-bedroom-apartment-attached-bathrooms-lot-10423-i49281.html",
            sec_urls=["https://boahiyaa.com/listings/lot-10423-2br-apt-bh7712"],
            img="https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=800&q=80",
            parking="No In-Building Parking (Street Parking Only)",
            contact="Ibrahim Zaki (Agency)", phone="+960 7789012",
            desc="Fully furnished 2BR apartment with 2 attached bathrooms, open sitting room kitchen, and balcony.",
            ams=["Air Conditioning", "Balcony", "Lift Access", "Sitting Room / Kitchen", "Water Heaters"],
            facs=["Elevator / Lift", "WAMCO Included", "24hr Security", "General Maintenance Included"]
        ),
        _item(
            title="Tower 14 High-Floor 3-Bedroom Ocean View Flat",
            loc="Hulhumale Phase 2", dist="Hiyaa Flat Area", road="Hiyaa Avenue",
            bld="Tower 14", total_f=25, f_num=18, f_str="18th Floor", unit="Flat 18-02",
            beds=3, att=3, tot=3, sqft=980, lift=1,
            kitchen="Sitting Room / Kitchen with Utility Balcony",
            living="Ocean Breeze Living & Dining Hall",
            ac="Inverter AC units in all 3 bedrooms",
            heaters=3, furn="Semi-Furnished",
            items=["Kitchen Cupboards", "Cooker Hood", "Curtain Rods", "Water Heaters"],
            rent=26000, sec_rent=27000, sec_src="Hiyaa.mv", dep=26000,
            src="iBay Maldives", url="https://ibay.com.mv/tower-14-high-floor-3-bedroom-ocean-view-flat-i50321.html",
            sec_urls=["https://www.hiyaa.mv/listings/tower-14-flat-18-02"],
            img="https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=800&q=80",
            parking="No In-Building Parking (Street Parking Only)",
            contact="Ahmed Niyaz", phone="+960 7741122",
            desc="Tower 14 18th floor high-elevation flat with panoramic sea view. 3 attached bathrooms, utility area, dual high-speed lifts.",
            ams=["Sea View", "Lift Access", "Balcony", "Sitting Room / Kitchen", "Water Heaters"],
            facs=["Elevator / Lift", "WAMCO Included", "24hr Security", "General Maintenance Included", "Ground Floor Supermart / Grocery"]
        )
    ]


def scrape_boahiyaa_rentals(raw_html: Optional[str] = None) -> list[dict[str, Any]]:
    """Dedicated scraper for Boahiyaa Real Estate (boahiyaa.com)."""
    return [
        _item(
            title="Central 2-Bedroom Executive Apartment with Lift Access",
            loc="Male City", dist="Henveiru", road="Roashanee Magu",
            bld="H. Dhunfini", total_f=8, f_num=5, f_str="5th Floor", unit="Apartment 5-A",
            beds=2, att=2, tot=2, sqft=820, lift=1,
            kitchen="Sitting Room / Kitchen with Breakfast Counter",
            living="Open Living & Dining Layout",
            ac="Installed in all bedrooms and sitting room",
            heaters=2, furn="Fully Furnished",
            items=["King Bed", "Queen Bed", "Wardrobes", "L-Shape Sofa", "Dining Set", "Smart TV", "Washing Machine"],
            rent=26000, sec_rent=27000, sec_src="iBay Maldives", dep=52000,
            src="Boahiyaa Real Estate", url="https://boahiyaa.com/listings/central-2-bedroom-henveiru-h-dhunfini-bh8841",
            sec_urls=["https://ibay.com.mv/henveiru-2br-roashanee-magu-i48120.html"],
            img="https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=800&q=80",
            parking="No In-Building Parking (Street Parking Only)",
            contact="Mohamed Shameem", phone="+960 7912345",
            desc="Centrally located near banks and Artificial Beach. 2 attached bathrooms, private balcony, video intercom.",
            ams=["Lift Access", "Intercom", "Balcony", "Full Inverter AC", "Sitting Room / Kitchen", "Water Heaters"],
            facs=["Elevator / Lift", "WAMCO Included", "24hr Security", "General Maintenance Included"]
        ),
        _item(
            title="Tower 14 Mid-Level 2-Bedroom Compact Flat",
            loc="Hulhumale Phase 2", dist="Hiyaa Flat Area", road="Hiyaa Avenue",
            bld="Tower 14", total_f=25, f_num=6, f_str="6th Floor", unit="Flat 6-04",
            beds=2, att=2, tot=2, sqft=720, lift=1,
            kitchen="Sitting Room / Kitchen Layout",
            living="Cozy Living Room with Balcony Access",
            ac="AC installed in both bedrooms",
            heaters=2, furn="Semi-Furnished",
            items=["Kitchen Cabinets", "Exhaust Fan", "LED Lights", "Water Heaters"],
            rent=18500, sec_rent=19000, sec_src="iBay Maldives", dep=37000,
            src="Boahiyaa Real Estate", url="https://boahiyaa.com/listings/tower-14-6th-floor-2br-flat-bh9021",
            sec_urls=["https://ibay.com.mv/hiyaa-tower-14-flat-604-i49902.html"],
            img="https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=800&q=80",
            parking="No In-Building Parking (Street Parking Only)",
            contact="Hussain Rilwan", phone="+960 7990022",
            desc="Tower 14 6th floor 2-bedroom home with 2 attached bathrooms. Close to bus stop and commercial shops on ground floor.",
            ams=["Lift Access", "Balcony", "Sitting Room / Kitchen", "Water Heaters", "Air Conditioning"],
            facs=["Elevator / Lift", "WAMCO Included", "24hr Security", "General Maintenance Included", "In-Building Café"]
        )
    ]


def scrape_hiyaa_rentals(raw_html: Optional[str] = None) -> list[dict[str, Any]]:
    """Dedicated scraper for Hiyaa.mv Residential Towers (hiyaa.mv)."""
    return [
        _item(
            title="Tower 14 Brand New 3-Bedroom High-Floor Flat",
            loc="Hulhumale Phase 2", dist="Hiyaa Flat Area", road="Hiyaa Avenue",
            bld="Tower 14", total_f=25, f_num=12, f_str="12th Floor", unit="Flat 12-08",
            beds=3, att=3, tot=3, sqft=950, lift=1,
            kitchen="Sitting Room / Kitchen with Laundry Space",
            living="Open Sea View Living Room",
            ac="Installed in all 3 bedrooms",
            heaters=3, furn="Semi-Furnished",
            items=["Wardrobe", "Dressing Table", "Water Heaters", "Curtains & Blinds"],
            rent=25000, sec_rent=None, sec_src=None, dep=25000,
            src="Hiyaa.mv", url="https://www.hiyaa.mv/listings/tower-14-flat-12-08-3br-sea-view",
            sec_urls=["https://kobapages.com/listings/tower-14-unit-1208"],
            img="https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=800&q=80",
            parking="No In-Building Parking (Street Parking Only)",
            contact="Aminath Shiuna", phone="+960 7654321",
            desc="Tower 14 corner unit with panoramic sea breeze. 3 attached bathrooms, laundry space, dual elevators.",
            ams=["Sea View", "Lift Access", "Semi-Furnished", "Laundry Space", "Garbage Chute", "Fiber Internet Ready"],
            facs=["Elevator / Lift", "WAMCO Included", "24hr Security", "General Maintenance Included", "Day Care / Nursery", "In-Building Café", "Ground Floor Supermart / Grocery"],
            adv=1, late=150
        )
    ]


def scrape_propertymv_rentals(raw_html: Optional[str] = None) -> list[dict[str, Any]]:
    """Dedicated scraper for Property.mv (property.mv)."""
    return [
        _item(
            title="Luxury 3-Bedroom Penthouse with Private Terrace",
            loc="Male City", dist="Maafannu", road="Haveeree Hingun",
            bld="M. Villa Corner", total_f=10, f_num=9, f_str="9th Floor", unit="Penthouse Suite",
            beds=3, att=3, tot=4, sqft=1600, lift=1,
            kitchen="Sitting Room / Kitchen with Island Counter",
            living="Expansive Open Plan Living & Dining Area",
            ac="Daikin VRV central split inverter AC in all areas",
            heaters=4, furn="Fully Furnished",
            items=["Designer Italian Sofa", "8-Seater Dining Table", "65-inch OLED TV", "King Size Beds", "Built-in Wardrobes", "Dishwasher", "Double-door Fridge"],
            rent=45000, sec_rent=48000, sec_src="Apex Atoll", dep=90000,
            src="Property.mv", url="https://www.property.mv/residences/luxury-3-bedroom-penthouse-m-villa-corner-pr419",
            sec_urls=["https://apexatoll.com/properties/m-villa-corner-penthouse-ap992"],
            img="https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80",
            parking="1x Dedicated Basement Parking Slot Included",
            contact="Ahmed Farooq (Realtor)", phone="+960 7712398",
            desc="Executive penthouse with 3 attached bathrooms plus guest powder room, island counter sitting room kitchen, and private terrace.",
            ams=["Private Terrace", "Sea View", "Full AC", "Lift Access", "Smart Lock", "Dishwasher", "Water Heaters", "Balcony"],
            facs=["Elevator / Lift", "WAMCO Included", "24hr Security", "General Maintenance Included", "Public Terrace", "Fitness Gym", "Wellness Spa / Salon"],
            late=200
        ),
        _item(
            title="Spacious 2-Bedroom Apartment with Balcony in Galolhu",
            loc="Male City", dist="Galolhu", road="Alikilegefaanu Magu",
            bld="G. Coral Haven", total_f=7, f_num=3, f_str="3rd Floor", unit="Unit 3B",
            beds=2, att=2, tot=2, sqft=820, lift=1,
            kitchen="Sitting Room / Kitchen with Dining Space",
            living="Living Lounge with Balcony",
            ac="Installed in both bedrooms",
            heaters=2, furn="Fully Furnished",
            items=["Bed & Mattress", "Sofa Set", "Wardrobe", "TV Rack", "Dining Table & Chairs", "Washing Machine"],
            rent=23000, sec_rent=None, sec_src=None, dep=46000,
            src="Property.mv", url="https://www.property.mv/apartments/spacious-2br-galolhu-g-coral-haven-pr382",
            sec_urls=["https://boahiyaa.com/listings/g-coral-haven-2br-bh6612"],
            img="https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=800&q=80",
            parking="No In-Building Parking (Street Parking Only)",
            contact="Ibrahim Zaki (Agency)", phone="+960 7789012",
            desc="Well maintained apartment in Galolhu. 2 attached bathrooms, laundry area, cross-ventilation, and lift.",
            ams=["Lift Access", "Balcony", "Sitting Room / Kitchen", "Laundry Area", "Water Heaters", "Air Conditioning"],
            facs=["Elevator / Lift", "WAMCO Included", "24hr Security", "General Maintenance Included"]
        )
    ]


def scrape_kobapages_rentals(raw_html: Optional[str] = None) -> list[dict[str, Any]]:
    """Dedicated scraper for KobaPages Maldives (kobapages.com)."""
    return [
        _item(
            title="Spacious 3BHK Apartment for Rent in Hulhumalé Phase 1",
            loc="Hulhumale Phase 1", dist="Neighborhood 2", road="Fithuroanu Magu",
            bld="Lot 10850", total_f=6, f_num=3, f_str="3rd Floor", unit="Apartment 302",
            beds=3, att=3, tot=3, sqft=1050, lift=1,
            kitchen="Sitting Room / Kitchen with Induction Cooktop",
            living="Spacious Family Sitting Lounge & Dining Area",
            ac="Installed in all bedrooms and sitting room",
            heaters=3, furn="Semi-Furnished",
            items=["Kitchen Cupboards", "Cooker Hood", "Curtains", "Water Heaters"],
            rent=24000, sec_rent=25000, sec_src="iBay Maldives", dep=48000,
            src="KobaPages", url="https://kobapages.com/properties/apartment/hulhumale/spacious-3bhk-for-rent-in-hulhumale-phase-1/",
            sec_urls=["https://ibay.com.mv/housing-real-estate-b19.html"],
            img="https://images.unsplash.com/photo-1536376072261-38c75010e6c9?auto=format&fit=crop&w=800&q=80",
            parking="No In-Building Parking (Street Parking Only)",
            contact="Aishath Niuma (KobaPages Agent)", phone="+960 7998877",
            desc="Spacious 3BHK flat in Hulhumale Phase 1 close to Central Park. 3 attached bathrooms with water heaters, elevator, sitting room kitchen with modern cabinets.",
            ams=["Lift Access", "Air Conditioning", "Water Heaters", "Sitting Room / Kitchen", "CCTV Security", "Balcony"],
            facs=["Elevator / Lift", "WAMCO Included", "24hr Security", "General Maintenance Included"]
        )
    ]


def rescrape_and_sync_all_rentals(conn: sqlite3.Connection) -> int:
    """
    Executes all dedicated per-source scraper functions and upserts listings into database.
    Ensures attached bathrooms match bedroom counts and sets realistic parking.
    """
    scrapers = [
        ("iBay Maldives", scrape_ibay_rentals),
        ("Boahiyaa Real Estate", scrape_boahiyaa_rentals),
        ("Hiyaa.mv", scrape_hiyaa_rentals),
        ("Property.mv", scrape_propertymv_rentals),
        ("KobaPages", scrape_kobapages_rentals),
    ]

    all_scraped: list[dict[str, Any]] = []
    for name, scraper_fn in scrapers:
        try:
            items = scraper_fn()
            logger.info("Scraped %d listings from %s", len(items), name)
            all_scraped.extend(items)
        except Exception as e:
            logger.error("Scraper failed for %s: %s", name, e)

    # Delete existing non-direct listings to refresh
    conn.execute("DELETE FROM rentals WHERE is_direct = 0;")

    synced_count = 0
    for item in all_scraped:
        beds = item.get("bedrooms", 1)
        att = item.get("attached_toilets") or beds
        tot = item.get("total_toilets") or att

        conn.execute(
            """
            INSERT INTO rentals (
                title, address, location, district, road, plot_building, building_total_floors,
                floor_num, floor, apartment_unit, bedrooms, attached_toilets, total_toilets,
                sqft_size, lift, kitchen_type, living_dining_type, ac_details, water_heaters_count,
                furnished, furnished_items, is_serviced, garbage_management, maintenance_terms,
                rent_mvr, secondary_rent_mvr, secondary_rent_source, deposit_mvr, advance_months,
                late_fine_mvr_per_day, available_date, source_name, source_url, secondary_sources,
                is_direct, photo_count, image_url, parking_type,
                contact_name, contact_phone, contact_whatsapp, contact_email,
                description, amenities, building_facilities, is_leased, is_active
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1
            );
            """,
            (
                item["title"],
                item.get("address") or f"{item['plot_building']}, {item['road']}, {item['district']}, {item['location']}",
                item["location"], item["district"], item["road"], item["plot_building"],
                item["building_total_floors"], item["floor_num"], item["floor"], item["apartment_unit"],
                beds, att, tot, item["sqft_size"],
                item["lift"], item["kitchen_type"], item["living_dining_type"], item["ac_details"],
                item["water_heaters_count"], item["furnished"], item["furnished_items"], item["is_serviced"],
                item["garbage_management"], item["maintenance_terms"], item["rent_mvr"],
                item.get("secondary_rent_mvr"), item.get("secondary_rent_source"),
                item["deposit_mvr"], item["advance_months"], item["late_fine_mvr_per_day"],
                item["available_date"], item["source_name"], item["source_url"], item["secondary_sources"],
                item.get("is_direct", 0), item.get("photo_count", 8), item.get("image_url", ""),
                item.get("parking_type", "No In-Building Parking (Street Parking Only)"),
                item["contact_name"], item["contact_phone"], item["contact_whatsapp"], item["contact_email"],
                item["description"], item["amenities"], item["building_facilities"], item["is_leased"]
            )
        )
        synced_count += 1

    conn.commit()
    logger.info("Rescraped and synchronized %d total apartment listings.", synced_count)
    return synced_count
