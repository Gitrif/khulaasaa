"""
Rentals & Tenancy Contract Repository for Khulaasaa.
Consolidated Maldivian Apartment Listings, Building-Level Aggregation,
Room Specs, Inventory, and Court-Admissible Tenancy Leases.
Strictly under 500 lines. Zero emojis.
"""
from __future__ import annotations

import datetime
import json
import sqlite3
from typing import Any, Optional
from data.seed_rentals import seed_initial_rentals


def _ensure_column(conn: sqlite3.Connection, table: str, col: str, col_type: str) -> None:
    """Safely add column to SQLite table if it does not already exist."""
    try:
        cur = conn.execute(f"PRAGMA table_info({table});")
        existing = [row[1] for row in cur.fetchall()]
        if col not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};")
    except Exception:
        pass


def init_rentals_schema(conn: sqlite3.Connection) -> None:
    """Create or upgrade rentals and rental contracts tables."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rentals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
            address_id INTEGER REFERENCES addresses(id) ON DELETE SET NULL,
            landlord_person_id INTEGER REFERENCES people(id) ON DELETE SET NULL,
            title TEXT NOT NULL,
            location TEXT NOT NULL,
            district TEXT,
            address TEXT,
            road TEXT,
            plot_building TEXT,
            building_total_floors INTEGER DEFAULT 1,
            floor_num INTEGER DEFAULT 1,
            floor TEXT,
            apartment_unit TEXT,
            bedrooms INTEGER NOT NULL DEFAULT 1,
            attached_toilets INTEGER NOT NULL DEFAULT 1,
            total_toilets INTEGER NOT NULL DEFAULT 1,
            sqft_size INTEGER,
            lift INTEGER DEFAULT 1,
            kitchen_type TEXT DEFAULT 'Sitting Room / Kitchen',
            living_dining_type TEXT DEFAULT 'Sitting & Dining Area',
            ac_details TEXT,
            water_heaters_count INTEGER DEFAULT 1,
            furnished TEXT DEFAULT 'Semi-Furnished',
            furnished_items TEXT,
            is_serviced INTEGER DEFAULT 0,
            garbage_management TEXT DEFAULT 'WAMCO Included',
            maintenance_terms TEXT DEFAULT 'Lessor covers structural; tenant covers minor consumables',
            rent_mvr INTEGER NOT NULL,
            deposit_mvr INTEGER NOT NULL DEFAULT 0,
            advance_months INTEGER DEFAULT 0,
            late_fine_mvr_per_day INTEGER DEFAULT 100,
            available_date TEXT,
            posted_date TEXT,
            posted_time TEXT,
            source_name TEXT NOT NULL,
            source_url TEXT,
            secondary_sources TEXT,
            secondary_rent_mvr INTEGER,
            secondary_rent_source TEXT,
            is_direct INTEGER DEFAULT 0,
            photo_count INTEGER DEFAULT 8,
            image_url TEXT,
            parking_type TEXT DEFAULT 'No In-Building Parking (Street Parking Only)',
            contact_name TEXT,
            contact_phone TEXT,
            contact_email TEXT,
            contact_whatsapp TEXT,
            description TEXT,
            amenities TEXT,
            building_facilities TEXT,
            is_leased INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    cols_to_check = [
        ("road", "TEXT"), ("plot_building", "TEXT"), ("building_total_floors", "INTEGER DEFAULT 1"),
        ("floor_num", "INTEGER DEFAULT 1"), ("apartment_unit", "TEXT"), ("attached_toilets", "INTEGER DEFAULT 1"),
        ("total_toilets", "INTEGER DEFAULT 1"), ("sqft_size", "INTEGER"), ("kitchen_type", "TEXT DEFAULT 'Sitting Room / Kitchen'"),
        ("living_dining_type", "TEXT DEFAULT 'Sitting & Dining Area'"), ("ac_details", "TEXT"),
        ("water_heaters_count", "INTEGER DEFAULT 1"), ("furnished_items", "TEXT"),
        ("is_serviced", "INTEGER DEFAULT 0"), ("garbage_management", "TEXT DEFAULT 'WAMCO Included'"),
        ("maintenance_terms", "TEXT"), ("advance_months", "INTEGER DEFAULT 0"),
        ("late_fine_mvr_per_day", "INTEGER DEFAULT 100"), ("secondary_sources", "TEXT"),
        ("contact_whatsapp", "TEXT"), ("building_facilities", "TEXT"), ("is_leased", "INTEGER DEFAULT 0"),
        ("is_direct", "INTEGER DEFAULT 0"), ("secondary_rent_mvr", "INTEGER"),
        ("secondary_rent_source", "TEXT"), ("photo_count", "INTEGER DEFAULT 8"),
        ("image_url", "TEXT"), ("parking_type", "TEXT DEFAULT '1x Motorbike Parking Included'"),
        ("source_id", "INTEGER REFERENCES sources(id)"),
        ("address_id", "INTEGER REFERENCES addresses(id)"),
        ("landlord_person_id", "INTEGER REFERENCES people(id)"),
        ("posted_date", "TEXT"),
        ("posted_time", "TEXT")
    ]
    for c, ctype in cols_to_check:
        _ensure_column(conn, "rentals", c, ctype)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rental_contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            rental_id INTEGER,
            landlord_name TEXT NOT NULL,
            landlord_nid TEXT NOT NULL,
            landlord_phone TEXT NOT NULL,
            landlord_address TEXT,
            tenant_name TEXT NOT NULL,
            tenant_nid TEXT NOT NULL,
            tenant_phone TEXT NOT NULL,
            tenant_address TEXT,
            property_address TEXT NOT NULL,
            plot_building TEXT,
            apartment_unit TEXT,
            monthly_rent_mvr INTEGER NOT NULL,
            security_deposit_mvr INTEGER NOT NULL,
            late_fine_mvr_per_day INTEGER DEFAULT 100,
            advance_amount_mvr INTEGER DEFAULT 0,
            lease_start_date TEXT NOT NULL,
            lease_duration_months INTEGER DEFAULT 12,
            notice_period_days INTEGER DEFAULT 30,
            utilities_clause TEXT,
            maintenance_clause TEXT,
            illegal_activities_clause TEXT,
            inventory_items TEXT,
            contract_language TEXT DEFAULT 'en',
            contract_json TEXT,
            status TEXT DEFAULT 'draft',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rental_id) REFERENCES rentals(id)
        );
        """
    )
    contract_cols = [
        ("landlord_address", "TEXT"), ("tenant_address", "TEXT"), ("plot_building", "TEXT"),
        ("apartment_unit", "TEXT"), ("late_fine_mvr_per_day", "INTEGER DEFAULT 100"),
        ("advance_amount_mvr", "INTEGER DEFAULT 0"), ("notice_period_days", "INTEGER DEFAULT 30"),
        ("maintenance_clause", "TEXT"), ("illegal_activities_clause", "TEXT"),
        ("inventory_items", "TEXT"), ("contract_language", "TEXT DEFAULT 'en'")
    ]
    for c, ctype in contract_cols:
        _ensure_column(conn, "rental_contracts", c, ctype)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_rentals_location ON rentals(location);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rentals_rent ON rentals(rent_mvr);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rentals_beds ON rentals(bedrooms);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rentals_leased ON rentals(is_leased);")


def redact_contact_name(name: Optional[str]) -> str:
    """Mask landlord/lister contact names for public classified privacy."""
    if not name or not name.strip():
        return "Verified Lister"
    clean = name.strip()
    if clean.lower() in ("direct lister", "lister", "landlord", "owner", "private owner"):
        return "Verified Lister"
    words = clean.split()
    redacted = []
    for w in words:
        if len(w) <= 2:
            redacted.append(w[0] + "*")
        else:
            redacted.append(w[0] + "*" * (len(w) - 1))
    return " ".join(redacted)


def list_rentals(
    conn: sqlite3.Connection,
    location: Optional[str] = None,
    bedrooms: Optional[int] = None,
    max_rent: Optional[int] = None,
    furnished: Optional[str] = None,
    has_lift: Optional[int] = None,
    has_ac: Optional[int] = None,
    has_water_heater: Optional[int] = None,
    search_q: Optional[str] = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Query consolidated rental listings with multi-attribute filtering."""
    query = "SELECT * FROM rentals WHERE is_active = 1 AND is_leased = 0"
    params: list[Any] = []

    if location and location not in ("All Locations", "All"):
        query += " AND (location LIKE ? OR district LIKE ?)"
        params.extend([f"%{location}%", f"%{location}%"])

    if bedrooms and bedrooms > 0:
        query += " AND bedrooms = ?"
        params.append(bedrooms)

    if max_rent and max_rent > 0:
        query += " AND rent_mvr <= ?"
        params.append(max_rent)

    if furnished and furnished not in ("All Furnishing", "All"):
        query += " AND furnished = ?"
        params.append(furnished)

    if has_lift == 1:
        query += " AND lift = 1"

    if has_ac == 1:
        query += " AND (ac_details IS NOT NULL AND ac_details != 'None' AND ac_details != '')"

    if has_water_heater == 1:
        query += " AND water_heaters_count > 0"

    if search_q:
        q_clean = f"%{search_q.strip()}%"
        query += " AND (title LIKE ? OR location LIKE ? OR address LIKE ? OR plot_building LIKE ? OR description LIKE ?)"
        params.extend([q_clean, q_clean, q_clean, q_clean, q_clean])

    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    cur = conn.execute(query, tuple(params))
    rows = cur.fetchall()
    results = []

    # Calculate building unit density across the active database
    bld_cur = conn.execute("SELECT plot_building, COUNT(*) FROM rentals WHERE is_active = 1 AND is_leased = 0 GROUP BY plot_building;")
    bld_counts = {row[0]: row[1] for row in bld_cur.fetchall() if row[0]}

    from core.time_utils import calculate_minutes_ago, format_relative_time

    for r in rows:
        d = dict(r)
        d["contact_name_raw"] = d.get("contact_name")
        d["contact_name"] = redact_contact_name(d.get("contact_name"))
        d["bathrooms"] = d.get("attached_toilets") or d.get("bedrooms") or 1
        d["building_units_count"] = bld_counts.get(d.get("plot_building"), 1)
        d["amenities_list"] = _parse_json_or_csv(d.get("amenities"))
        d["furnished_items_list"] = _parse_json_or_csv(d.get("furnished_items"))
        d["building_facilities_list"] = _parse_json_or_csv(d.get("building_facilities"))
        d["secondary_sources_list"] = _parse_json_or_csv(d.get("secondary_sources"))

        ts = d.get("created_at") or d.get("posted_date")
        if ts:
            mins = calculate_minutes_ago(ts)
            d["updated_ago"] = format_relative_time(mins, ts)
        else:
            d["updated_ago"] = "Recently"

        results.append(d)
    return results


def _parse_json_or_csv(val: Any) -> list[str]:
    """Parse JSON array or comma-separated string into list of strings."""
    if not val:
        return []
    if isinstance(val, list):
        return val
    try:
        loaded = json.loads(val)
        if isinstance(loaded, list):
            return [str(x) for x in loaded]
    except Exception:
        pass
    return [x.strip() for x in str(val).split(",") if x.strip()]


def get_rental_by_id(conn: sqlite3.Connection, rental_id: int) -> Optional[dict[str, Any]]:
    """Fetch single rental property by ID with structured lists."""
    cur = conn.execute("SELECT * FROM rentals WHERE id = ? LIMIT 1;", (rental_id,))
    row = cur.fetchone()
    if not row:
        return None
    d = dict(row)
    d["contact_name_raw"] = d.get("contact_name")
    d["contact_name"] = redact_contact_name(d.get("contact_name"))
    d["bathrooms"] = d.get("attached_toilets") or d.get("bedrooms") or 1
    d["amenities_list"] = _parse_json_or_csv(d.get("amenities"))
    d["furnished_items_list"] = _parse_json_or_csv(d.get("furnished_items"))
    d["building_facilities_list"] = _parse_json_or_csv(d.get("building_facilities"))
    d["secondary_sources_list"] = _parse_json_or_csv(d.get("secondary_sources"))
    return d


def save_rental_contract(conn: sqlite3.Connection, contract_data: dict[str, Any]) -> int:
    """Save or update residential tenancy contract draft with all Maldivian legal clauses."""
    c_id = contract_data.get("id")
    c_json = json.dumps(contract_data.get("details", {}), ensure_ascii=False)
    inv_json = json.dumps(contract_data.get("inventory_items", []), ensure_ascii=False)
    lang = contract_data.get("contract_language", "en")
    start_date = contract_data.get("lease_start_date") or datetime.date.today().isoformat()

    if c_id:
        conn.execute(
            """
            UPDATE rental_contracts SET
                landlord_name = ?, landlord_nid = ?, landlord_phone = ?, landlord_address = ?,
                tenant_name = ?, tenant_nid = ?, tenant_phone = ?, tenant_address = ?,
                property_address = ?, plot_building = ?, apartment_unit = ?,
                monthly_rent_mvr = ?, security_deposit_mvr = ?, late_fine_mvr_per_day = ?,
                advance_amount_mvr = ?, lease_start_date = ?, lease_duration_months = ?,
                notice_period_days = ?, utilities_clause = ?, maintenance_clause = ?,
                illegal_activities_clause = ?, inventory_items = ?, contract_language = ?,
                contract_json = ?, status = ?
            WHERE id = ?;
            """,
            (
                contract_data.get("landlord_name"), contract_data.get("landlord_nid"), contract_data.get("landlord_phone"), contract_data.get("landlord_address", ""),
                contract_data.get("tenant_name"), contract_data.get("tenant_nid"), contract_data.get("tenant_phone"), contract_data.get("tenant_address", ""),
                contract_data.get("property_address"), contract_data.get("plot_building", ""), contract_data.get("apartment_unit", ""),
                contract_data.get("monthly_rent_mvr", 0), contract_data.get("security_deposit_mvr", 0), contract_data.get("late_fine_mvr_per_day", 100),
                contract_data.get("advance_amount_mvr", 0), start_date, contract_data.get("lease_duration_months", 12),
                contract_data.get("notice_period_days", 30), contract_data.get("utilities_clause", ""), contract_data.get("maintenance_clause", ""),
                contract_data.get("illegal_activities_clause", ""), inv_json, lang, c_json, contract_data.get("status", "draft"), c_id
            )
        )
        return c_id
    else:
        cur = conn.execute(
            """
            INSERT INTO rental_contracts (
                user_id, rental_id, landlord_name, landlord_nid, landlord_phone, landlord_address,
                tenant_name, tenant_nid, tenant_phone, tenant_address,
                property_address, plot_building, apartment_unit,
                monthly_rent_mvr, security_deposit_mvr, late_fine_mvr_per_day, advance_amount_mvr,
                lease_start_date, lease_duration_months, notice_period_days,
                utilities_clause, maintenance_clause, illegal_activities_clause,
                inventory_items, contract_language, contract_json, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id;
            """,
            (
                contract_data.get("user_id"), contract_data.get("rental_id"),
                contract_data.get("landlord_name"), contract_data.get("landlord_nid"), contract_data.get("landlord_phone"), contract_data.get("landlord_address", ""),
                contract_data.get("tenant_name"), contract_data.get("tenant_nid"), contract_data.get("tenant_phone"), contract_data.get("tenant_address", ""),
                contract_data.get("property_address"), contract_data.get("plot_building", ""), contract_data.get("apartment_unit", ""),
                contract_data.get("monthly_rent_mvr", 0), contract_data.get("security_deposit_mvr", 0), contract_data.get("late_fine_mvr_per_day", 100), contract_data.get("advance_amount_mvr", 0),
                start_date, contract_data.get("lease_duration_months", 12), contract_data.get("notice_period_days", 30),
                contract_data.get("utilities_clause", ""), contract_data.get("maintenance_clause", ""), contract_data.get("illegal_activities_clause", ""),
                inv_json, lang, c_json, contract_data.get("status", "draft")
            )
        )
        row = cur.fetchone()
        return row[0] if row else 0
