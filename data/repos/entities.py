from __future__ import annotations

import logging
import sqlite3
from typing import Any, Optional

from data.utils import slugify, detect_entity_type

logger = logging.getLogger(__name__)


def resolve_or_create_entity(conn: sqlite3.Connection, raw_name: str) -> int:
    """
    Look up an entity in the dictionary using exact, alias, or fuzzy matching.
    If no match is found, automatically creates and classifies a new entity record.
    Returns the entity's database ID.
    """
    if not raw_name or not raw_name.strip():
        raw_name = "Unknown Agency"

    clean_name = raw_name.strip()

    # 1. Exact match on English or Dhivehi name
    row = conn.execute(
        "SELECT id FROM entities WHERE LOWER(name_en) = LOWER(?) OR name_dv = ?",
        (clean_name, clean_name),
    ).fetchone()
    if row:
        return row["id"]

    # 2. Known abbreviations / keywords matching
    low = clean_name.lower()
    if "housing development corporation" in low or "hdc" in low:
        target_slug = "housing-development-corporation"
    elif "water and sewerage" in low or "mwsc" in low:
        target_slug = "male-water-and-sewerage-company"
    elif "state trading" in low or "sto" in low:
        target_slug = "state-trading-organization"
    elif "stelco" in low or "state electric" in low:
        target_slug = "state-electric-company"
    elif "fenaka" in low or "ފެނަކަ" in clean_name:
        target_slug = "fenaka-corporation"
    elif "finance" in low and ("ministry" in low or "މިނިސްޓްރީ" in clean_name):
        target_slug = "ministry-of-finance"
    elif "tourism" in low and ("ministry" in low or "މިނިސްޓްރީ" in clean_name):
        target_slug = "ministry-of-tourism"
    elif "health" in low and ("ministry" in low or "މިނިސްޓްރީ" in clean_name):
        target_slug = "ministry-of-health"
    elif "education" in low and ("ministry" in low or "މިނިސްޓްރީ" in clean_name):
        target_slug = "ministry-of-education"
    # The 5 Official Cities in the Maldives
    elif ("malé" in low or "male'" in low or "male" in low or "މާލެ" in clean_name) and ("city" in low or "ސިޓީ" in clean_name):
        target_slug = "council-male-city"
    elif ("addu" in low or "އައްޑޫ" in clean_name or "އައްޑު" in clean_name) and ("city" in low or "ސިޓީ" in clean_name or "council" in low or "ކައުންސިލް" in clean_name):
        target_slug = "council-addu-city"
    elif "fuvahmulah" in low or "ފުވައްމުލައް" in clean_name or "ފުވައްމުލަކު" in clean_name:
        target_slug = "council-fuvahmulah-city"
    elif "kulhudhuffushi" in low or "ކުޅުދުއްފުށި" in clean_name or "ކުޅުދުއްފުށީ" in clean_name:
        target_slug = "council-kulhudhuffushi-city"
    elif ("thinadhoo" in low or "ތިނަދޫ" in clean_name) and ("city" in low or "ސިޓީ" in clean_name or "council" in low or "ކައުންސިލް" in clean_name):
        target_slug = "council-thinadhoo-city"
    # Specific known island councils
    elif "uligan" in low or "އުލިގަމު" in clean_name:
        target_slug = "council-uligan"
    elif "hoarafushi" in low or "ހޯރަފުށީ" in clean_name:
        target_slug = "council-hoarafushi"
    elif "fulidhoo" in low or "ފުލިދޫ" in clean_name:
        target_slug = "council-fulidhoo"
    elif "timarafushi" in low or "ތިމަރަފުށީ" in clean_name:
        target_slug = "council-timarafushi"
    elif "polytechnic" in low or "ޕޮލިޓެކްނިކް" in clean_name:
        target_slug = "maldives-polytechnic"
    elif "customs" in low or "ކަސްޓަމްސް" in clean_name:
        target_slug = "maldives-customs-service"
    elif "post" in low or "ޕޯސްޓް" in clean_name:
        target_slug = "maldives-post"
    elif "fuel supplies" in low or "fsm" in low:
        target_slug = "fuel-supplies-maldives"
    else:
        target_slug = None

    if target_slug:
        row = conn.execute("SELECT id FROM entities WHERE slug = ?", (target_slug,)).fetchone()
        if row:
            return row["id"]

    # 3. Create a new entity in the dictionary
    from scrapers.translator import is_dhivehi, translate_agency, clean_residual_thaana
    has_thaana = is_dhivehi(clean_name)
    if has_thaana:
        name_en = clean_residual_thaana(translate_agency(clean_name)) or "Public Authority"
        name_dv = clean_name
    else:
        name_en = clean_name
        name_dv = None

    entity_type = detect_entity_type(name_en) if not has_thaana else detect_entity_type(clean_name)

    base_slug = slugify(name_en)
    if entity_type == "Council" and not base_slug.startswith("council-"):
        base_slug = f"council-{base_slug}"

    slug = base_slug
    idx = 1
    while conn.execute("SELECT 1 FROM entities WHERE slug = ?", (slug,)).fetchone():
        slug = f"{base_slug}-{idx}"
        idx += 1

    cursor = conn.execute(
        """
        INSERT INTO entities (slug, name_en, name_dv, entity_type)
        VALUES (?, ?, ?, ?)
        """,
        (slug, name_en, name_dv, entity_type),
    )
    return cursor.lastrowid


def list_entities(conn: sqlite3.Connection, entity_type: Optional[str] = None) -> list[dict[str, Any]]:
    """List all entities in the dictionary with their active tender counts."""
    query = """
    SELECT
        e.id,
        e.slug,
        e.name_en,
        e.name_dv,
        e.entity_type,
        e.location,
        e.website,
        COUNT(b.id) AS tender_count
    FROM entities e
    LEFT JOIN bids b ON e.id = b.entity_id AND b.is_active = 1
    """
    params: list[Any] = []
    if entity_type:
        query += " WHERE e.entity_type = ?"
        params.append(entity_type)
    query += " GROUP BY e.id ORDER BY tender_count DESC, e.name_en ASC;"
    return [dict(row) for row in conn.execute(query, params).fetchall()]


# ---------------------------------------------------------------------
# Tender / Bid Operations
# ---------------------------------------------------------------------



# =====================================================================
