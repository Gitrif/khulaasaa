"""
Seed data repository for Maldivian Consolidated Rentals.
Covers major sources with full building, room, and inventory specs.
Rule: Modern Maldivian apartments feature attached toilets for each bedroom.
Strictly under 500 lines. Zero emojis.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Optional


def _sample(
    title: str, loc: str, dist: str, road: str, bld: str, total_f: int,
    f_num: int, f_str: str, unit: str, beds: int, att: int, tot: int, sqft: int,
    lift: int, kitchen: str, living: str, ac: str, heaters: int, furn: str,
    items: list[str], rent: int, sec_rent: Optional[int], sec_src: Optional[str],
    dep: int, src: str, url: str, sec_urls: list[str], img: str,
    parking: str, contact: str, phone: str, desc: str, ams: list[str],
    facs: list[str], adv: int = 0, late: int = 100, avail: str = "Immediate"
) -> dict[str, Any]:
    """Build normalized sample rental record."""
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


SAMPLE_RENTALS = [
    _sample(
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
        desc="Spacious fully furnished 2-bedroom home with 2 attached bathrooms, ACs in all rooms, sitting room kitchen with cabinets and cooker hood, water heaters, and balcony.",
        ams=["Air Conditioning", "Balcony", "Lift Access", "Sitting Room / Kitchen", "CCTV Security", "Water Heaters"],
        facs=["Elevator / Lift", "WAMCO Included", "24hr Security", "General Maintenance Included"]
    ),
    _sample(
        title="Tower 14 High-Floor 3-Bedroom Ocean View Flat",
        loc="Hulhumale Phase 2", dist="Commercial Corridor", road="Hiyaa Avenue",
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
        desc="Tower 14 18th floor high-elevation flat with panoramic sea view. 3 attached bathrooms, utility area, dual high-speed elevators.",
        ams=["Sea View", "Lift Access", "Balcony", "Sitting Room / Kitchen", "Water Heaters"],
        facs=["Elevator / Lift", "WAMCO Included", "24hr Security", "General Maintenance Included", "Ground Floor Supermart / Grocery"]
    ),
    _sample(
        title="Tower 14 Mid-Level 2-Bedroom Compact Flat",
        loc="Hulhumale Phase 2", dist="Commercial Corridor", road="Hiyaa Avenue",
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
    ),
    _sample(
        title="Tower 14 Brand New 3-Bedroom High-Floor Flat",
        loc="Hulhumale Phase 2", dist="Commercial Corridor", road="Hiyaa Avenue",
        bld="Tower 14", total_f=25, f_num=12, f_str="12th Floor", unit="Flat 12-08",
        beds=3, att=3, tot=3, sqft=950, lift=1,
        kitchen="Sitting Room / Kitchen with Laundry Space",
        living="Open Sea View Living Room",
        ac="Installed in all 3 bedrooms",
        heaters=3, furn="Semi-Furnished",
        items=["Wardrobe", "Dressing Table", "Water Heaters", "Curtains & Blinds"],
        rent=25000, sec_rent=None, sec_src=None, dep=25000,
        src="Hiyaa.mv Residential", url="https://www.hiyaa.mv/listings/tower-14-flat-12-08-3br-sea-view",
        sec_urls=["https://kobapages.com/listings/tower-14-unit-1208"],
        img="https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=800&q=80",
        parking="No In-Building Parking (Street Parking Only)",
        contact="Aminath Shiuna", phone="+960 7654321",
        desc="Corner unit with panoramic sea breeze and morning sunlight. Complete kitchen cupboards, 3 attached bathrooms, separate laundry room, and dual elevator service.",
        ams=["Sea View", "Lift Access", "Semi-Furnished", "Laundry Space", "Garbage Chute", "Fiber Internet Ready"],
        facs=["Elevator / Lift", "WAMCO Included", "24hr Security", "General Maintenance Included", "Day Care / Nursery", "In-Building Café", "Ground Floor Supermart / Grocery"],
        adv=1, late=150
    ),
    _sample(
        title="Central 2-Bedroom Executive Apartment with Lift Access",
        loc="Male City", dist="Henveiru", road="Roashanee Magu",
        bld="H. Dhunfini", total_f=8, f_num=5, f_str="5th Floor", unit="Apartment 5-A",
        beds=2, att=2, tot=2, sqft=780, lift=1,
        kitchen="Sitting Room / Kitchen with Breakfast Counter",
        living="Cozy Living Lounge",
        ac="Full inverter AC in all rooms",
        heaters=2, furn="Fully Furnished",
        items=["Bed & Mattress", "Sofa Set", "Wardrobe", "TV Rack", "Dining Table & Chairs", "Refrigerator", "Washing Machine"],
        rent=24000, sec_rent=None, sec_src=None, dep=48000,
        src="Property.mv", url="https://boahiyaa.com/listings/central-2-bedroom-henveiru-h-dhunfini-bh8841",
        sec_urls=["https://apexatoll.com/listings/h-dhunfini-5a"],
        img="https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=800&q=80",
        parking="No In-Building Parking (Street Parking Only)",
        contact="Mohamed Shameem", phone="+960 7912345",
        desc="Centrally located near banks, schools, and Artificial Beach. Features 2 attached bathrooms, private balcony, and video intercom system.",
        ams=["Lift Access", "Intercom", "Balcony", "Full Inverter AC", "Sitting Room / Kitchen", "Water Heaters"],
        facs=["Elevator / Lift", "WAMCO Included", "24hr Security", "General Maintenance Included"]
    ),
    _sample(
        title="Luxury 3-Bedroom Penthouse with Private Terrace",
        loc="Male City", dist="Maafannu", road="Haveeree Hingun",
        bld="M. Villa Corner", total_f=10, f_num=9, f_str="9th Floor", unit="Penthouse Suite",
        beds=3, att=3, tot=4, sqft=1350, lift=1,
        kitchen="Sitting Room / Kitchen with Island Counter",
        living="Expansive Living Room & Formal Dining Area",
        ac="Centralized inverter AC throughout all rooms",
        heaters=4, furn="Fully Furnished",
        items=["Bed & Mattress", "Sofa Set", "Wardrobe", "Coffee Table", "TV Rack", "Dining Table & Chairs", "Refrigerator", "Oven & Microwave", "Washing Machine"],
        rent=38000, sec_rent=40000, sec_src="Boahiyaa", dep=76000,
        src="Apex Atoll Properties", url="https://www.property.mv/residences/luxury-3-bedroom-penthouse-m-villa-corner-pr419",
        sec_urls=["https://boahiyaa.com/listings/m-villa-corner-penthouse-bh991"],
        img="https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=800&q=80",
        parking="1x Dedicated Basement Parking Slot Included",
        contact="Apex Leasing Team", phone="+960 7901234",
        desc="Executive penthouse with master en-suite, 3 attached bathrooms plus guest powder room, island counter kitchen, and outdoor private terrace overlooking harbour.",
        ams=["Private Terrace", "Smart Lock", "Dual Lifts", "Dishwasher", "Backup Generator", "Gym Access"],
        facs=["Elevator / Lift", "WAMCO Included", "24hr Security", "General Maintenance Included", "Public Terrace", "Fitness Gym", "Wellness Spa / Salon"],
        late=200
    ),
    _sample(
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
        src="KobaPages Maldives", url="https://kobapages.com/properties/apartment/hulhumale/spacious-3bhk-for-rent-in-hulhumale-phase-1/",
        sec_urls=["https://ibay.com.mv/housing-real-estate-b19.html"],
        img="https://images.unsplash.com/photo-1536376072261-38c75010e6c9?auto=format&fit=crop&w=800&q=80",
        parking="No In-Building Parking (Street Parking Only)",
        contact="Aishath Niuma (KobaPages Agent)", phone="+960 7998877",
        desc="Spacious 3BHK flat in Hulhumale Phase 1 close to Central Park. 3 attached bathrooms with water heaters, elevator, sitting room kitchen with modern cabinets.",
        ams=["Lift Access", "Air Conditioning", "Water Heaters", "Sitting Room / Kitchen", "CCTV Security", "Balcony"],
        facs=["Elevator / Lift", "WAMCO Included", "24hr Security", "General Maintenance Included"],
        late=100
    ),
    _sample(
        title="Spacious 2-Bedroom Apartment with Balcony in Galolhu",
        loc="Male City", dist="Galolhu", road="Alikilegefaanu Magu",
        bld="G. Coral Haven", total_f=7, f_num=3, f_str="3rd Floor", unit="Unit 3B",
        beds=2, att=2, tot=2, sqft=820, lift=1,
        kitchen="Sitting Room / Kitchen with Dining Space",
        living="Living Lounge with Balcony",
        ac="Installed in both bedrooms",
        heaters=2, furn="Fully Furnished",
        items=["Bed & Mattress", "Sofa Set", "Wardrobe", "Coffee Table", "TV Rack", "Dining Table & Chairs", "Washing Machine"],
        rent=23000, sec_rent=None, sec_src=None, dep=46000,
        src="Boahiyaa Real Estate", url="https://www.property.mv/apartments/spacious-2br-galolhu-g-coral-haven-pr382",
        sec_urls=["https://ibay.com.mv/galolhu-coral-haven-2br-i42199.html"],
        img="https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80",
        parking="No In-Building Parking (Street Parking Only)",
        contact="Ibrahim Zaki (Agency)", phone="+960 7789012",
        desc="Well maintained residential apartment in quiet Galolhu lane. 2 spacious bedrooms with 2 attached bathrooms, dedicated laundry area, and lift.",
        ams=["Lift Access", "Balcony", "Sitting Room / Kitchen", "Laundry Area", "Water Heaters", "Air Conditioning"],
        facs=["Elevator / Lift", "WAMCO Included", "24hr Security", "General Maintenance Included", "In-Building Café"]
    )
]


def seed_initial_rentals(conn: sqlite3.Connection) -> None:
    """Seed or refresh sample rental properties into the rentals table."""
    from data.repos.sources import resolve_or_create_source
    from data.repos.addresses import resolve_or_create_address
    from data.repos.people import resolve_or_create_person

    # Delete legacy dummy-seeded aggregated listings
    conn.execute("DELETE FROM rentals WHERE is_direct = 0;")

    now_d = "2026-10-26"
    now_t = "12:00:00"

    for item in SAMPLE_RENTALS:
        src_id = resolve_or_create_source(conn, item["source_name"], source_type="marketplace")
        addr_str = item.get("address") or f"{item['plot_building']}, {item['road']}, {item['district']}, {item['location']}"
        addr_id = resolve_or_create_address(
            conn,
            formatted_address=addr_str,
            island_name_en=item["location"],
            district=item["district"],
            road=item["road"],
            building_name=item["plot_building"],
            floor=item.get("floor"),
            unit=item.get("apartment_unit"),
        )
        landlord_id = resolve_or_create_person(
            conn,
            full_name_en=item["contact_name"] or "Boahiyaa Agent",
            phone=item.get("contact_phone"),
            email=item.get("contact_email"),
        )

        conn.execute(
            """
            INSERT INTO rentals (
                source_id, address_id, landlord_person_id,
                title, address, location, district, road, plot_building, building_total_floors,
                floor_num, floor, apartment_unit, bedrooms, attached_toilets, total_toilets,
                sqft_size, lift, kitchen_type, living_dining_type, ac_details, water_heaters_count,
                furnished, furnished_items, is_serviced, garbage_management, maintenance_terms,
                rent_mvr, secondary_rent_mvr, secondary_rent_source, deposit_mvr, advance_months,
                late_fine_mvr_per_day, available_date, posted_date, posted_time, source_name, source_url, secondary_sources,
                is_direct, photo_count, image_url, parking_type,
                contact_name, contact_phone, contact_whatsapp, contact_email,
                description, amenities, building_facilities, is_leased, is_active
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, 1
            );
            """,
            (
                src_id, addr_id, landlord_id,
                item["title"],
                addr_str,
                item["location"], item["district"], item["road"], item["plot_building"],
                item["building_total_floors"], item["floor_num"], item["floor"], item["apartment_unit"],
                item["bedrooms"], item["attached_toilets"], item["total_toilets"], item["sqft_size"],
                item["lift"], item["kitchen_type"], item["living_dining_type"], item["ac_details"],
                item["water_heaters_count"], item["furnished"], item["furnished_items"], item["is_serviced"],
                item["garbage_management"], item["maintenance_terms"], item["rent_mvr"],
                item.get("secondary_rent_mvr"), item.get("secondary_rent_source"),
                item["deposit_mvr"], item["advance_months"], item["late_fine_mvr_per_day"],
                item["available_date"], now_d, now_t, item["source_name"], item["source_url"], item["secondary_sources"],
                item.get("is_direct", 0), item.get("photo_count", 8), item.get("image_url", ""),
                item.get("parking_type", "No In-Building Parking (Street Parking Only)"),
                item["contact_name"], item["contact_phone"], item["contact_whatsapp"], item["contact_email"],
                item["description"], item["amenities"], item["building_facilities"], item["is_leased"]
            )
        )
    conn.commit()
