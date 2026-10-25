"""
Rentals & Tenancy Contract Repository for Khulaasaa MV.
Consolidated Maldivian Apartment Listings and Residential Tenancy Suite.
Strictly under 500 lines. Zero emojis.
"""
from __future__ import annotations
import json
import sqlite3
from typing import Any, Optional

def init_rentals_schema(conn: sqlite3.Connection) -> None:
    """Create rentals and rental contracts tables if not present."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rentals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            title_dv TEXT,
            location TEXT NOT NULL,
            district TEXT,
            address TEXT,
            bedrooms INTEGER NOT NULL DEFAULT 1,
            bathrooms INTEGER NOT NULL DEFAULT 1,
            furnished TEXT DEFAULT 'Semi-Furnished',
            rent_mvr INTEGER NOT NULL,
            deposit_mvr INTEGER NOT NULL DEFAULT 0,
            floor TEXT,
            lift INTEGER DEFAULT 1,
            available_date TEXT,
            source_name TEXT NOT NULL,
            source_url TEXT,
            contact_name TEXT,
            contact_phone TEXT,
            contact_email TEXT,
            description TEXT,
            amenities TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rental_contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            rental_id INTEGER,
            landlord_name TEXT NOT NULL,
            landlord_nid TEXT NOT NULL,
            landlord_phone TEXT NOT NULL,
            tenant_name TEXT NOT NULL,
            tenant_nid TEXT NOT NULL,
            tenant_phone TEXT NOT NULL,
            property_address TEXT NOT NULL,
            monthly_rent_mvr INTEGER NOT NULL,
            security_deposit_mvr INTEGER NOT NULL,
            lease_start_date TEXT NOT NULL,
            lease_duration_months INTEGER DEFAULT 12,
            utilities_clause TEXT,
            contract_json TEXT,
            status TEXT DEFAULT 'draft',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rental_id) REFERENCES rentals(id)
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rentals_location ON rentals(location);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rentals_rent ON rentals(rent_mvr);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rentals_beds ON rentals(bedrooms);")


def list_rentals(
    conn: sqlite3.Connection,
    location: Optional[str] = None,
    bedrooms: Optional[int] = None,
    max_rent: Optional[int] = None,
    furnished: Optional[str] = None,
    search_q: Optional[str] = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Query consolidated rental listings with multi-attribute filtering."""
    query = "SELECT * FROM rentals WHERE is_active = 1"
    params: list[Any] = []

    if location and location != "All Locations":
        query += " AND location LIKE ?"
        params.append(f"%{location}%")

    if bedrooms and bedrooms > 0:
        query += " AND bedrooms = ?"
        params.append(bedrooms)

    if max_rent and max_rent > 0:
        query += " AND rent_mvr <= ?"
        params.append(max_rent)

    if furnished and furnished != "All":
        query += " AND furnished = ?"
        params.append(furnished)

    if search_q:
        q_clean = f"%{search_q.strip()}%"
        query += " AND (title LIKE ? OR location LIKE ? OR address LIKE ? OR description LIKE ?)"
        params.extend([q_clean, q_clean, q_clean, q_clean])

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    cur = conn.execute(query, tuple(params))
    rows = cur.fetchall()
    results = []
    for r in rows:
        d = dict(r)
        try:
            d["amenities_list"] = json.loads(d["amenities"]) if d.get("amenities") else []
        except Exception:
            d["amenities_list"] = [a.strip() for a in str(d.get("amenities", "")).split(",") if a.strip()]
        results.append(d)
    return results


def get_rental_by_id(conn: sqlite3.Connection, rental_id: int) -> Optional[dict[str, Any]]:
    """Fetch single rental property by ID."""
    cur = conn.execute("SELECT * FROM rentals WHERE id = ? LIMIT 1;", (rental_id,))
    row = cur.fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        d["amenities_list"] = json.loads(d["amenities"]) if d.get("amenities") else []
    except Exception:
        d["amenities_list"] = [a.strip() for a in str(d.get("amenities", "")).split(",") if a.strip()]
    return d


def save_rental_contract(conn: sqlite3.Connection, contract_data: dict[str, Any]) -> int:
    """Save or update residential tenancy contract draft."""
    c_id = contract_data.get("id")
    c_json = json.dumps(contract_data.get("details", {}), ensure_ascii=False)
    if c_id:
        conn.execute(
            """
            UPDATE rental_contracts SET
                landlord_name = ?, landlord_nid = ?, landlord_phone = ?,
                tenant_name = ?, tenant_nid = ?, tenant_phone = ?,
                property_address = ?, monthly_rent_mvr = ?, security_deposit_mvr = ?,
                lease_start_date = ?, lease_duration_months = ?, utilities_clause = ?,
                contract_json = ?, status = ?
            WHERE id = ?;
            """,
            (
                contract_data.get("landlord_name"), contract_data.get("landlord_nid"), contract_data.get("landlord_phone"),
                contract_data.get("tenant_name"), contract_data.get("tenant_nid"), contract_data.get("tenant_phone"),
                contract_data.get("property_address"), contract_data.get("monthly_rent_mvr"), contract_data.get("security_deposit_mvr"),
                contract_data.get("lease_start_date"), contract_data.get("lease_duration_months", 12), contract_data.get("utilities_clause", ""),
                c_json, contract_data.get("status", "draft"), c_id
            )
        )
        return c_id
    else:
        cur = conn.execute(
            """
            INSERT INTO rental_contracts (
                user_id, rental_id, landlord_name, landlord_nid, landlord_phone,
                tenant_name, tenant_nid, tenant_phone, property_address,
                monthly_rent_mvr, security_deposit_mvr, lease_start_date,
                lease_duration_months, utilities_clause, contract_json, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id;
            """,
            (
                contract_data.get("user_id"), contract_data.get("rental_id"),
                contract_data.get("landlord_name"), contract_data.get("landlord_nid"), contract_data.get("landlord_phone"),
                contract_data.get("tenant_name"), contract_data.get("tenant_nid"), contract_data.get("tenant_phone"),
                contract_data.get("property_address"), contract_data.get("monthly_rent_mvr"), contract_data.get("security_deposit_mvr"),
                contract_data.get("lease_start_date"), contract_data.get("lease_duration_months", 12), contract_data.get("utilities_clause", ""),
                c_json, contract_data.get("status", "draft")
            )
        )
        row = cur.fetchone()
        return row[0] if row else 0


def seed_initial_rentals(conn: sqlite3.Connection) -> None:
    """Seed initial Maldivian apartment listings across Male and Hulhumale."""
    count = conn.execute("SELECT COUNT(*) FROM rentals;").fetchone()[0]
    if count > 0:
        return

    sample_rentals = [
        {
            "title": "Modern 2-Bedroom Apartment with Attached Bathrooms",
            "title_dv": "ހުޅުމާލެ ފޭސް 1 އިން ކުއްޔަށްދޭ 2 ކޮޓަރީގެ އެޕާޓްމަންޓް",
            "location": "Hulhumale Phase 1",
            "district": "Neighborhood 2",
            "address": "Lot 10423, Nirolhu Magu, Hulhumale Phase 1",
            "bedrooms": 2,
            "bathrooms": 2,
            "furnished": "Fully Furnished",
            "rent_mvr": 22000,
            "deposit_mvr": 44000,
            "floor": "4th Floor",
            "lift": 1,
            "available_date": "1 November 2026",
            "source_name": "iBay Maldives",
            "source_url": "https://ibay.com.mv/listing/apartment-hulhumale-2br-41829",
            "contact_name": "Hussain Solih",
            "contact_phone": "7789123",
            "contact_email": "solih.rentals@gmail.com",
            "description": "Spacious fully furnished 2-bedroom apartment with air-conditioning in all rooms, kitchen cabinet set with stove/hood, hot water heaters, and balcony. Lift access and CCTV installed in building.",
            "amenities": json.dumps(["Air Conditioning", "Balcony", "Lift Access", "Kitchen Cabinets", "CCTV Security", "Water Heaters"])
        },
        {
            "title": "Brand New 3-Bedroom High-Floor Apartment with Sea View",
            "title_dv": "ހުޅުމާލެ ފޭސް 2 އިން ކުއްޔަށްދޭ 3 ކޮޓަރީގެ އެޕާޓްމަންޓް",
            "location": "Hulhumale Phase 2",
            "district": "Hiyaa Commercial Corridor",
            "address": "Tower 14, Phase 2, Hulhumale",
            "bedrooms": 3,
            "bathrooms": 3,
            "furnished": "Semi-Furnished",
            "rent_mvr": 25000,
            "deposit_mvr": 25000,
            "floor": "12th Floor",
            "lift": 1,
            "available_date": "Immediate",
            "source_name": "Direct Landlord",
            "source_url": "https://khulaasaa.tech/rentals/2",
            "contact_name": "Mariyam Nazra",
            "contact_phone": "9912045",
            "contact_email": "nazra.properties@outlook.com",
            "description": "Corner unit with panoramic sea breeze and morning sunlight. Complete kitchen cupboards, 3 attached toilets, separate laundry room, and dual elevator service.",
            "amenities": json.dumps(["Sea View", "Lift Access", "Semi-Furnished", "Laundry Space", "Garbage Chute", "Fiber Internet Ready"])
        },
        {
            "title": "Compact 1-Bedroom Studio Apartment in Central Malé",
            "title_dv": "މާލެ ހެންވޭރުން ކުއްޔަށްދޭ 1 ކޮޓަރީގެ އެޕާޓްމަންޓް",
            "location": "Male City",
            "district": "Henveiru",
            "address": "Near Artificial Beach, Henveiru, Male",
            "bedrooms": 1,
            "bathrooms": 1,
            "furnished": "Semi-Furnished",
            "rent_mvr": 14000,
            "deposit_mvr": 14000,
            "floor": "2nd Floor",
            "lift": 0,
            "available_date": "Immediate",
            "source_name": "Facebook Marketplace MV",
            "source_url": "https://facebook.com/groups/maldivesrentals/permalink/88129",
            "contact_name": "Ahmed Latheef",
            "contact_phone": "7901188",
            "contact_email": "ahmed.latheef@mvproperties.com",
            "description": "Ideal for young professional or couple. Walking distance to Artificial Beach, banks, and grocery supermarkets. Quiet residential lane with dedicated motorcycle parking slot.",
            "amenities": json.dumps(["Motorcycle Parking", "Kitchenette", "Hot Water", "Quiet Neighborhood"])
        },
        {
            "title": "Luxury 3-Bedroom Penthouse with Private Terrace",
            "title_dv": "މާލެ މާފަންނުން ކުއްޔަށްދޭ ލަގްޒަރީ 3 ކޮޓަރީގެ ޕެންޓްހައުސް",
            "location": "Male City",
            "district": "Maafannu",
            "address": "Haveeree Hingun, Maafannu, Male",
            "bedrooms": 3,
            "bathrooms": 4,
            "furnished": "Fully Furnished",
            "rent_mvr": 38000,
            "deposit_mvr": 76000,
            "floor": "9th Floor",
            "lift": 1,
            "available_date": "15 November 2026",
            "source_name": "Island Classifieds",
            "source_url": "https://islandclassifieds.mv/rent/luxury-penthouse-maafannu-12",
            "contact_name": "Ibrahim Zaki (Agency)",
            "contact_phone": "7774020",
            "contact_email": "zaki@coralrealestate.mv",
            "description": "Executive penthouse with master en-suite, maid room with private toilet, open-concept kitchen with island counter, smart door-locks, and private outdoor terrace overlooking sunset harbour.",
            "amenities": json.dumps(["Private Terrace", "Smart Lock", "Maid Room", "Dual Lifts", "Dishwasher", "Backup Generator", "Gym Access"])
        },
        {
            "title": "Affordable 2-Bedroom Family Home near Central Park",
            "title_dv": "ހުޅުމާލެ ސެންޓްރަލް ޕާކް ކައިރިން 2 ކޮޓަރީގެ އެޕާޓްމަންޓް",
            "location": "Hulhumale Phase 1",
            "district": "Neighborhood 1",
            "address": "Near Central Park, Hulhumale Phase 1",
            "bedrooms": 2,
            "bathrooms": 2,
            "furnished": "Unfurnished",
            "rent_mvr": 18500,
            "deposit_mvr": 37000,
            "floor": "3rd Floor",
            "lift": 1,
            "available_date": "1 December 2026",
            "source_name": "iBay Maldives",
            "source_url": "https://ibay.com.mv/listing/hulhumale-park-2br-88912",
            "contact_name": "Aishath Shifa",
            "contact_phone": "9998144",
            "contact_email": "shifa.aishath@live.com",
            "description": "Well ventilated family apartment steps away from Central Park, schools, and ferry bus stop. Both bedrooms feature natural light and attached baths. Long lease preferred.",
            "amenities": json.dumps(["Lift Access", "Cross Ventilation", "Park Access", "Balcony", "Security Intercom"])
        }
    ]

    for item in sample_rentals:
        conn.execute(
            """
            INSERT INTO rentals (
                title, title_dv, location, district, address, bedrooms, bathrooms,
                furnished, rent_mvr, deposit_mvr, floor, lift, available_date,
                source_name, source_url, contact_name, contact_phone, contact_email,
                description, amenities, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
            """,
            (
                item["title"], item.get("title_dv"), item["location"], item["district"],
                item["address"], item["bedrooms"], item["bathrooms"], item["furnished"],
                item["rent_mvr"], item["deposit_mvr"], item["floor"], item["lift"],
                item["available_date"], item["source_name"], item["source_url"],
                item["contact_name"], item["contact_phone"], item["contact_email"],
                item["description"], item["amenities"]
            )
        )
