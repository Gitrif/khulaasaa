"""
Addresses Repository.
Encapsulates all database operations and resolution for Maldivian addresses.
Provides single source of truth for Atolls, Islands, Districts, Roads, and Buildings.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Any, Optional

logger = logging.getLogger(__name__)


def get_address_by_id(conn: sqlite3.Connection, address_id: int) -> Optional[dict[str, Any]]:
    """Fetch address record by primary key id."""
    row = conn.execute("SELECT * FROM addresses WHERE id = ? LIMIT 1;", (address_id,)).fetchone()
    return dict(row) if row else None


def resolve_or_create_address(
    conn: sqlite3.Connection,
    formatted_address: str,
    atoll_code: Optional[str] = None,
    atoll_name_en: Optional[str] = None,
    island_name_en: Optional[str] = None,
    district: Optional[str] = None,
    road: Optional[str] = None,
    building_name: Optional[str] = None,
    floor: Optional[str] = None,
    unit: Optional[str] = None,
    postal_code: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> int:
    """
    Lookup existing address by formatted string or create a canonical new address record.
    Returns the address record primary key ID.
    """
    clean_addr = (formatted_address or "").strip()
    if not clean_addr and (building_name or road or district or island_name_en):
        parts = [p for p in [building_name, road, district, island_name_en] if p]
        clean_addr = ", ".join(parts)

    if not clean_addr:
        clean_addr = "Malé, Republic of Maldives"

    row = conn.execute(
        "SELECT id FROM addresses WHERE formatted_address = ? LIMIT 1;",
        (clean_addr,),
    ).fetchone()
    if row:
        return row[0] if isinstance(row, tuple) else row["id"]

    cur = conn.execute(
        """
        INSERT INTO addresses (
            country_code, atoll_code, atoll_name_en, island_name_en,
            district, road, building_name, floor, unit, postal_code,
            latitude, longitude, formatted_address
        )
        VALUES ('MDV', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            atoll_code,
            atoll_name_en,
            island_name_en or "Malé",
            district,
            road,
            building_name,
            floor,
            unit,
            postal_code,
            latitude,
            longitude,
            clean_addr,
        ),
    )
    return cur.lastrowid
