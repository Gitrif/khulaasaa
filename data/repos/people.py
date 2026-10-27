"""
People Repository.
Encapsulates all database operations and resolution for individuals (citizens, job seekers, deceased, directors).
Provides single source of truth for Person identities.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Any, Optional

logger = logging.getLogger(__name__)


def get_person_by_id(conn: sqlite3.Connection, person_id: int) -> Optional[dict[str, Any]]:
    """Fetch person record by primary key id."""
    row = conn.execute("SELECT * FROM people WHERE id = ? LIMIT 1;", (person_id,)).fetchone()
    return dict(row) if row else None


def get_person_by_nid(conn: sqlite3.Connection, nid_number: str) -> Optional[dict[str, Any]]:
    """Fetch person record by Maldivian National ID / Passport number."""
    if not nid_number or not nid_number.strip():
        return None
    row = conn.execute("SELECT * FROM people WHERE nid_number = ? LIMIT 1;", (nid_number.strip(),)).fetchone()
    return dict(row) if row else None


def resolve_or_create_person(
    conn: sqlite3.Connection,
    full_name_en: str,
    full_name_dv: Optional[str] = None,
    nid_number: Optional[str] = None,
    gender: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    permanent_address_id: Optional[int] = None,
    current_address_id: Optional[int] = None,
    date_of_birth: Optional[str] = None,
    date_of_death: Optional[str] = None,
) -> int:
    """
    Lookup existing person by NID or English/Dhivehi name, or insert a canonical Person record.
    Returns the person primary key ID.
    """
    clean_en = (full_name_en or "").strip()
    clean_dv = (full_name_dv or "").strip()
    clean_nid = (nid_number or "").strip() if nid_number else None

    # 1. Lookup by NID if supplied
    if clean_nid:
        row = conn.execute("SELECT id FROM people WHERE nid_number = ? LIMIT 1;", (clean_nid,)).fetchone()
        if row:
            return row[0] if isinstance(row, tuple) else row["id"]

    # 2. Lookup by English or Dhivehi Name and Phone
    if phone:
        row = conn.execute(
            "SELECT id FROM people WHERE (full_name_en = ? OR full_name_dv = ?) AND phone = ? LIMIT 1;",
            (clean_en, clean_dv, phone),
        ).fetchone()
        if row:
            return row[0] if isinstance(row, tuple) else row["id"]

    # 3. Lookup by exact Name
    if clean_en or clean_dv:
        row = conn.execute(
            "SELECT id FROM people WHERE full_name_en = ? OR (full_name_dv IS NOT NULL AND full_name_dv = ?) LIMIT 1;",
            (clean_en or "Unknown Person", clean_dv),
        ).fetchone()
        if row:
            return row[0] if isinstance(row, tuple) else row["id"]

    # 4. Insert new canonical Person
    cur = conn.execute(
        """
        INSERT INTO people (
            nid_number, full_name_en, full_name_dv, gender,
            phone, email, permanent_address_id, current_address_id,
            date_of_birth, date_of_death
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            clean_nid,
            clean_en or "Unknown Person",
            clean_dv or None,
            gender,
            phone,
            email,
            permanent_address_id,
            current_address_id,
            date_of_birth,
            date_of_death,
        ),
    )
    last_id = getattr(cur, "lastrowid", None)
    if last_id:
        return last_id
    if clean_nid:
        r = conn.execute("SELECT id FROM people WHERE national_id = ? LIMIT 1;", (clean_nid,)).fetchone()
        if r:
            return r["id"] if hasattr(r, "__getitem__") and not isinstance(r, tuple) else r[0]
    r_fallback = conn.execute("SELECT id FROM people ORDER BY id ASC LIMIT 1;").fetchone()
    if r_fallback:
        return r_fallback["id"] if hasattr(r_fallback, "__getitem__") and not isinstance(r_fallback, tuple) else r_fallback[0]
    return 1
