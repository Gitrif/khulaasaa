"""
Obituaries Repository and Parsing Engine.
"""
from __future__ import annotations
import json
import re
import sqlite3
from typing import Any, Optional
from data.taxonomy import extract_atoll_and_island

def parse_obituary_text(text: str) -> dict[str, Any]:
    """Parse key attributes (name, age, address, mosque, prayer time, contacts) from Thaana obituary notice."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    data: dict[str, Any] = {
        "name_dv": "",
        "name_en": None,
        "address_dv": "",
        "address_en": None,
        "age": None,
        "funeral_mosque_dv": "މަސްޖިދުލް ތަޢާވުން (އާސަހަރާ މިސްކިތް)",
        "funeral_mosque_en": "Masjid al-Ta'awun (Aasahara Mosque)",
        "prayer_time_dv": "މިއަދުގެ ޢަޞްރު ނަމާދަށްފަހު",
        "prayer_time_en": "After Asr Prayer",
        "contact_numbers": None,
    }

    # Extract contacts: e.g. 7992266 / 9394545
    phones = re.findall(r"(?:(?:\+?960\s*)?[79]\d{6})", text)
    if phones:
        data["contact_numbers"] = " / ".join(dict.fromkeys(phones))

    # Extract age: e.g. (72އ) or 72 އަހަރު or (72)
    age_match = re.search(r"\(?\b(\d{1,3})\s*(?:އ|އަހަރު|\))\b", text)
    if age_match:
        try:
            data["age"] = int(age_match.group(1))
        except Exception:
            pass

    # Extract Mosque
    if "ހުޅުމާލެ" in text or "ޒައިދު" in text:
        data["funeral_mosque_dv"] = "މަސްޖިދުލް ޒައިދު ބިން ޘާބިތު (ހުޅުމާލެ ސަހަރާ މިސްކިތް)"
        data["funeral_mosque_en"] = "Masjid Zayd bin Thabit (Hulhumale' Cemetery Mosque)"
    elif "ފުރްޤާން" in text or "ފުރްގާން" in text:
        data["funeral_mosque_dv"] = "މަސްޖިދުލް ފުރްޤާން"
        data["funeral_mosque_en"] = "Masjid al-Furqan"
    elif "އިސްލާމީ މަރުކަޒު" in text:
        data["funeral_mosque_dv"] = "މަސްޖިދުލް ސުލްޠާން މުޙައްމަދު ތަކުރުފާނުލް އަޢުޡަމް (އިސްލާމީ މަރުކަޒު)"
        data["funeral_mosque_en"] = "Islamic Centre Mosque"
    elif "ކުޅުދުއްފުށި" in text or "ޢަފާފް" in text:
        data["funeral_mosque_dv"] = "މަސްޖިދުލް ޢަފާފް (ކުޅުދުއްފުށި)"
        data["funeral_mosque_en"] = "Masjid al-Afaaf, Kulhudhuffushi"

    # Extract Prayer Time
    if "ޢަޞްރު" in text or "ޢަސްރު" in text or "އަސްރު" in text or "asr" in text.lower():
        data["prayer_time_dv"] = "މިއަދުގެ ޢަޞްރު ނަމާދަށްފަހު"
        data["prayer_time_en"] = "After Asr Prayer"
    elif "މަޣްރިބް" in text or "މަޣްރިބު" in text or "maghrib" in text.lower():
        data["prayer_time_dv"] = "މިއަދުގެ މަޣްރިބް ނަމާދަށްފަހު"
        data["prayer_time_en"] = "After Maghrib Prayer"
    elif "ޢިޝާ" in text or "އިޝާ" in text or "isha" in text.lower():
        data["prayer_time_dv"] = "މިއަދުގެ ޢިޝާ ނަމާދަށްފަހު"
        data["prayer_time_en"] = "After Isha Prayer"
    elif "މެންދުރު" in text or "zuhr" in text.lower():
        data["prayer_time_dv"] = "މިއަދުގެ މެންދުރު ނަމާދަށްފަހު"
        data["prayer_time_en"] = "After Zuhr Prayer"
    elif "ފަތިސް" in text or "fajr" in text.lower():
        data["prayer_time_dv"] = "މިއަދުގެ ފަތިސް ނަމާދަށްފަހު"
        data["prayer_time_en"] = "After Fajr Prayer"

    # Look for Name and Address from lines
    filtered_lines = []
    for l in lines:
        if any(h in l for h in ["Kashunamaadhu", "ކަށުނަމާދު", "صلاة الجنازة", "إِنَّا لِلَّهِ", "އިންނާލިއްލާހި"]):
            continue
        if any(h in l for h in ["އޮންނާނީ", "ނަމާދަށްފަހު", "މިސްކިތުގައި", "ނަންބަރު", "ފޯނު"]):
            continue
        filtered_lines.append(l)

    if filtered_lines:
        first_line = filtered_lines[0]
        name_clean = re.sub(r"\(?\b\d{1,3}\s*(?:އ|އަހަރު|\))\b\)?", "", first_line).strip()
        data["name_dv"] = name_clean or first_line
        if len(filtered_lines) > 1:
            data["address_dv"] = filtered_lines[1]

    if not data["name_dv"]:
        data["name_dv"] = "މަރުޙޫމް"

    return data


def upsert_scraped_obituary(conn: sqlite3.Connection, text: str, link: Optional[str] = None) -> Optional[int]:
    """Parse and record an obituary notice from a wire or Telegram post."""
    parsed = parse_obituary_text(text)
    slug = f"ob-{abs(hash(text[:120]))}"
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    geo = extract_atoll_and_island(parsed.get("address_dv"), parsed.get("address_en"), parsed.get("funeral_mosque_dv"), parsed.get("funeral_mosque_en"))

    cursor = conn.execute(
        """
        INSERT INTO obituaries (
            slug, name_dv, name_en, address_dv, address_en, age,
            funeral_mosque_dv, funeral_mosque_en, prayer_time_dv, prayer_time_en,
            funeral_date, death_date, photo_url, contact_numbers, source_channel, announcement_type,
            atoll_code, atoll_name_dv, island_name, region_group, sort_order
        )
        VALUES (:slug, :name_dv, :name_en, :address_dv, :address_en, :age,
            :funeral_mosque_dv, :funeral_mosque_en, :prayer_time_dv, :prayer_time_en,
            :funeral_date, :death_date, :photo_url, :contact_numbers, :source_channel, :announcement_type,
            :atoll_code, :atoll_name_dv, :island_name, :region_group, :sort_order)
        ON CONFLICT(slug) DO UPDATE SET
            name_dv = excluded.name_dv,
            funeral_mosque_dv = excluded.funeral_mosque_dv,
            prayer_time_dv = excluded.prayer_time_dv,
            contact_numbers = excluded.contact_numbers,
            atoll_code = excluded.atoll_code,
            atoll_name_dv = excluded.atoll_name_dv,
            island_name = excluded.island_name,
            region_group = excluded.region_group,
            sort_order = excluded.sort_order
        RETURNING id;
        """,
        {
            "slug": slug,
            "name_dv": parsed["name_dv"],
            "name_en": parsed["name_en"],
            "address_dv": parsed["address_dv"],
            "address_en": parsed["address_en"],
            "age": parsed["age"],
            "funeral_mosque_dv": parsed["funeral_mosque_dv"],
            "funeral_mosque_en": parsed["funeral_mosque_en"],
            "prayer_time_dv": parsed["prayer_time_dv"],
            "prayer_time_en": parsed["prayer_time_en"],
            "funeral_date": today_str,
            "death_date": today_str,
            "photo_url": None,
            "contact_numbers": parsed["contact_numbers"],
            "source_channel": "KashunamaadhuMV",
            "announcement_type": "Janaza",
            "atoll_code": geo["atoll_code"],
            "atoll_name_dv": geo["atoll_name_dv"],
            "island_name": geo["island_name"],
            "region_group": geo["region_group"],
            "sort_order": geo["sort_order"],
        },
    )
    row = cursor.fetchone()
    return row[0] if row else None


def list_obituaries(
    conn: sqlite3.Connection,
    search_q: Optional[str] = None,
    atoll_code: Optional[str] = None,
    region_group: Optional[str] = None,
    limit: int = 100,
    active_only: bool = True,
    retention_days: int = 7,
) -> list[dict[str, Any]]:
    """List obituaries within 7-day history, sorted by atoll/island order."""
    try:
        purge_expired_obituaries(conn, retention_days=retention_days)
    except Exception:
        pass

    clauses = []
    params: list[Any] = []
    if active_only:
        clauses.append("is_active = 1")

    # 7-day retention filter
    from datetime import datetime, timedelta, timezone, timezone
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=retention_days)).strftime("%Y-%m-%d")
    clauses.append("(funeral_date IS NULL OR funeral_date >= ?)")
    params.append(cutoff_date)

    if region_group and region_group != "all":
        clauses.append("region_group = ?")
        params.append(region_group)

    if atoll_code and atoll_code != "all":
        clauses.append("atoll_code = ?")
        params.append(atoll_code)

    if search_q:
        q = f"%{search_q.strip()}%"
        clauses.append(
            "(name_dv LIKE ? OR name_en LIKE ? OR address_dv LIKE ? OR address_en LIKE ? OR funeral_mosque_dv LIKE ? OR funeral_mosque_en LIKE ? OR island_name LIKE ? OR atoll_name_dv LIKE ?)"
        )
        params.extend([q, q, q, q, q, q, q, q])

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    # Sort by atoll sort_order ASC, atoll_code ASC, island_name ASC, then funeral_date DESC, created_at DESC
    sql = f"""
        SELECT * FROM obituaries
        {where_sql}
        ORDER BY sort_order ASC, atoll_code ASC, island_name ASC, funeral_date DESC, created_at DESC, id DESC
        LIMIT ?;
    """
    params.append(limit)

    rows = conn.execute(sql, tuple(params)).fetchall()
    return [dict(r) for r in rows]


def get_obituary(conn: sqlite3.Connection, ob_id: int) -> Optional[dict[str, Any]]:
    """Retrieve an obituary by primary key ID."""
    row = conn.execute("SELECT * FROM obituaries WHERE id = ?;", (ob_id,)).fetchone()
    return dict(row) if row else None


def get_obituary_by_slug(conn: sqlite3.Connection, slug: str) -> Optional[dict[str, Any]]:
    """Retrieve an obituary by slug."""
    row = conn.execute("SELECT * FROM obituaries WHERE slug = ?;", (slug,)).fetchone()
    return dict(row) if row else None


def upsert_obituary(conn: sqlite3.Connection, ob: dict[str, Any]) -> int:
    """Insert or update an obituary notice with geo-enrichment."""
    geo = extract_atoll_and_island(ob.get("address_dv"), ob.get("address_en"), ob.get("funeral_mosque_dv"), ob.get("funeral_mosque_en"))
    cursor = conn.execute(
        """
        INSERT INTO obituaries (
            slug, name_dv, name_en, address_dv, address_en, age,
            funeral_mosque_dv, funeral_mosque_en, prayer_time_dv, prayer_time_en,
            funeral_date, death_date, photo_url, contact_numbers, source_channel, announcement_type, is_active,
            atoll_code, atoll_name_dv, island_name, region_group, sort_order
        )
        VALUES (:slug, :name_dv, :name_en, :address_dv, :address_en, :age,
            :funeral_mosque_dv, :funeral_mosque_en, :prayer_time_dv, :prayer_time_en,
            :funeral_date, :death_date, :photo_url, :contact_numbers, :source_channel, :announcement_type, :is_active,
            :atoll_code, :atoll_name_dv, :island_name, :region_group, :sort_order)
        ON CONFLICT(slug) DO UPDATE SET
            name_dv = excluded.name_dv,
            name_en = excluded.name_en,
            address_dv = excluded.address_dv,
            address_en = excluded.address_en,
            age = excluded.age,
            funeral_mosque_dv = excluded.funeral_mosque_dv,
            funeral_mosque_en = excluded.funeral_mosque_en,
            prayer_time_dv = excluded.prayer_time_dv,
            prayer_time_en = excluded.prayer_time_en,
            funeral_date = excluded.funeral_date,
            death_date = excluded.death_date,
            photo_url = COALESCE(excluded.photo_url, obituaries.photo_url),
            contact_numbers = excluded.contact_numbers,
            source_channel = excluded.source_channel,
            announcement_type = excluded.announcement_type,
            is_active = excluded.is_active,
            atoll_code = excluded.atoll_code,
            atoll_name_dv = excluded.atoll_name_dv,
            island_name = excluded.island_name,
            region_group = excluded.region_group,
            sort_order = excluded.sort_order
        RETURNING id;
        """,
        {
            "slug": ob["slug"],
            "name_dv": ob["name_dv"],
            "name_en": ob.get("name_en"),
            "address_dv": ob.get("address_dv"),
            "address_en": ob.get("address_en"),
            "age": ob.get("age"),
            "funeral_mosque_dv": ob.get("funeral_mosque_dv"),
            "funeral_mosque_en": ob.get("funeral_mosque_en"),
            "prayer_time_dv": ob.get("prayer_time_dv"),
            "prayer_time_en": ob.get("prayer_time_en"),
            "funeral_date": ob.get("funeral_date"),
            "death_date": ob.get("death_date"),
            "photo_url": ob.get("photo_url"),
            "contact_numbers": ob.get("contact_numbers"),
            "source_channel": ob.get("source_channel", "KashunamaadhuMV"),
            "announcement_type": ob.get("announcement_type", "Janaza"),
            "is_active": ob.get("is_active", 1),
            "atoll_code": ob.get("atoll_code") or geo["atoll_code"],
            "atoll_name_dv": ob.get("atoll_name_dv") or geo["atoll_name_dv"],
            "island_name": ob.get("island_name") or geo["island_name"],
            "region_group": ob.get("region_group") or geo["region_group"],
            "sort_order": ob.get("sort_order", geo["sort_order"]),
        },
    )
    row = cursor.fetchone()
    return row[0] if row else 0


def toggle_obituary(conn: sqlite3.Connection, ob_id: int) -> bool:
    """Toggle active status of an obituary."""
    cursor = conn.execute(
        "UPDATE obituaries SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?;",
        (ob_id,),
    )
    return cursor.rowcount > 0


def delete_obituary(conn: sqlite3.Connection, ob_id: int) -> bool:
    """Permanently delete an obituary notice."""
    cursor = conn.execute("DELETE FROM obituaries WHERE id = ?;", (ob_id,))
    return cursor.rowcount > 0


def purge_expired_obituaries(conn: sqlite3.Connection, retention_days: int = 30) -> int:
    """Purge obituaries older than retention_days."""
    cursor = conn.execute(
        """
        DELETE FROM obituaries 
        WHERE (funeral_date IS NOT NULL AND funeral_date != '' AND funeral_date < date('now', '-' || ? || ' days'))
           OR (death_date IS NOT NULL AND death_date != '' AND death_date < date('now', '-' || ? || ' days'))
           OR created_at < datetime('now', '-' || ? || ' days');
        """,
        (retention_days, retention_days, retention_days),
    )
    return cursor.rowcount


