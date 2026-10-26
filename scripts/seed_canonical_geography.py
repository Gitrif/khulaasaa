"""
Canonical Geography and Address Seeder for Maldives.
Seeds:
- 20 administrative atolls (atolls table)
- Inhabited and resort islands (islands table)
- Malé road network with districts (Henveiru, Galolhu, Machangoalhi, Maafannu, Vilimalé)
- 6,348 canonical residential buildings & house addresses in Malé (addresses table)

Generates:
- Direct population into SQLite database (data/khulaasaa.db)
- Production Supabase SQL migration (supabase/seed_geography.sql)
"""
from __future__ import annotations

import csv
import json
import logging
import os
import re
import sqlite3
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_geography")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ORDINON_DIR = Path(r"D:\work\Programing\Ordinon\docs\seed data for parsing")

CANONICAL_ATOLL_CODES = {
    "HA": "HA",
    "HDH": "HDh",
    "HDh": "HDh",
    "SH": "Sh",
    "Sh": "Sh",
    "N": "N",
    "R": "R",
    "B": "B",
    "LH": "Lh",
    "Lh": "Lh",
    "K": "K",
    "AA": "AA",
    "ADH": "ADh",
    "ADh": "ADh",
    "Adh": "ADh",
    "V": "V",
    "M": "M",
    "F": "F",
    "DH": "Dh",
    "Dh": "Dh",
    "TH": "Th",
    "Th": "Th",
    "L": "L",
    "GA": "GA",
    "GDH": "GDh",
    "GDh": "GDh",
    "Gdh": "GDh",
    "GN": "Gn",
    "Gn": "Gn",
    "S": "S",
    "SEENU": "S",
    "ADDU": "S",
}

DISTRICT_MAP = {
    "H": "Henveiru",
    "G": "Galolhu",
    "M": "Machangoalhi",
    "MA": "Maafannu",
    "V": "Vilimalé",
    "H , G": "Henveiru / Galolhu",
    "MA , M": "Maafannu / Machangoalhi",
    "MA , G": "Maafannu / Galolhu",
    "G , MA": "Galolhu / Maafannu",
}


def load_atolls() -> list[dict[str, str]]:
    """Parse atolls from atolls.csv."""
    atolls_file = ORDINON_DIR / "atolls.csv"
    if not atolls_file.exists():
        logger.error("atolls.csv not found at %s", atolls_file)
        return []

    atolls = []
    with open(atolls_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or len(row) < 3:
                continue
            code = row[0].replace("\ufeff", "").strip()
            # Normalize canonical atoll code
            code = CANONICAL_ATOLL_CODES.get(code, code)
            if "addu" in row[1].lower():
                code = "S"
            traditional = row[1].replace("\xa0", "").strip()
            name_en = row[2].strip()
            name_dv = row[4].strip() if len(row) > 4 else ""
            atolls.append({
                "code": code,
                "name_en": name_en,
                "traditional_name": traditional,
                "name_dv": name_dv,
            })
    logger.info("Loaded %d canonical atolls", len(atolls))
    return atolls


def load_islands() -> list[dict[str, any]]:
    """Parse islands from islands.json."""
    islands_file = ORDINON_DIR / "islands.json"
    if not islands_file.exists():
        logger.error("islands.json not found at %s", islands_file)
        return []

    islands = []
    with open(islands_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    atoll_pattern = re.compile(r"\((HA|HDh|Sh|N|R|B|Lh|K|AA|ADh|V|M|F|Dh|Th|L|GA|GDh|Gn|S)\)")
    for group in data.get("atolls", []):
        raw_name = group.get("name", "")
        m = atoll_pattern.search(raw_name)
        if m:
            atoll_code = m.group(1)
        elif "Addu" in raw_name or "Seenu" in raw_name:
            atoll_code = "S"
        elif "Gnaviyani" in raw_name or "Fuvahmulah" in raw_name:
            atoll_code = "Gn"
        elif "Male" in raw_name:
            atoll_code = "K"
        else:
            atoll_code = "K"

        atoll_code = CANONICAL_ATOLL_CODES.get(atoll_code, atoll_code)

        for island_name in group.get("inhabited", []):
            clean_name = re.sub(r"\(capital.*?\)", "", island_name).strip()
            islands.append({
                "atoll_code": atoll_code,
                "name_en": clean_name,
                "is_inhabited": 1,
            })
    logger.info("Loaded %d inhabited islands across all atolls", len(islands))
    return islands


def load_male_roads() -> dict[str, str]:
    """Parse road names and their districts from male' road names and widths.csv."""
    road_file = ORDINON_DIR / "male' road names and widths.csv"
    road_to_district = {}
    if not road_file.exists():
        logger.warning("male' road names and widths.csv not found, proceeding without road-to-district map.")
        return road_to_district

    with open(road_file, "r", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        for idx, row in enumerate(reader):
            if idx == 0 or len(row) < 3:
                continue
            road_name = row[1].strip()
            dist_code = row[2].strip()
            district = DISTRICT_MAP.get(dist_code, dist_code)
            if road_name:
                road_to_district[road_name.upper()] = district
    logger.info("Loaded %d Malé roads with district assignments", len(road_to_district))
    return road_to_district


def load_male_addresses(road_to_district: dict[str, str]) -> list[dict[str, any]]:
    """Parse canonical building addresses from male_addresses.json."""
    addr_file = ORDINON_DIR / "male_addresses.json"
    if not addr_file.exists():
        logger.error("male_addresses.json not found at %s", addr_file)
        return []

    with open(addr_file, "r", encoding="utf-8") as f:
        raw_list = json.load(f)

    seen = set()
    addresses = []
    for raw in raw_list:
        raw_clean = str(raw).strip()
        if not raw_clean or raw_clean in seen:
            continue
        seen.add(raw_clean)

        parts = [p.strip() for p in raw_clean.split(",")]
        if len(parts) >= 5:
            bld = parts[0]
            road = parts[1]
            atoll = parts[2]
            island = parts[3]
            postal = parts[4]
        elif len(parts) == 4:
            bld = parts[0]
            road = parts[1]
            atoll = "K"
            island = parts[2]
            postal = parts[3]
        else:
            bld = parts[0]
            road = parts[1] if len(parts) > 1 else ""
            atoll = "K"
            island = "Male"
            postal = "20002"

        district = road_to_district.get(road.upper(), "Henveiru" if postal.startswith("2000") or postal.startswith("2001") else "Male")
        addresses.append({
            "country_code": "MDV",
            "atoll_code": atoll,
            "atoll_name_en": "Kaafu Atoll",
            "atoll_name_dv": "ކ",
            "island_name_en": island,
            "island_name_dv": "މާލެ",
            "district": district,
            "road": road,
            "building_name": bld,
            "postal_code": postal,
            "formatted_address": raw_clean,
        })
    logger.info("Loaded %d unique Malé residential addresses", len(addresses))
    return addresses


def seed_sqlite(atolls: list[dict], islands: list[dict], addresses: list[dict]) -> None:
    """Populate local SQLite database safely via context manager."""
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    from data.connection import get_db

    with get_db() as conn:
        # 1. Atolls
        conn.execute("""
            CREATE TABLE IF NOT EXISTS atolls (
                code TEXT PRIMARY KEY,
                name_en TEXT NOT NULL,
                name_dv TEXT NOT NULL,
                traditional_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        for a in atolls:
            conn.execute("""
                INSERT INTO atolls (code, name_en, name_dv, traditional_name)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(code) DO UPDATE SET
                    name_en = excluded.name_en,
                    name_dv = excluded.name_dv,
                    traditional_name = excluded.traditional_name;
            """, (a["code"], a["name_en"], a["name_dv"], a["traditional_name"]))

        # 2. Islands
        conn.execute("""
            CREATE TABLE IF NOT EXISTS islands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                atoll_code TEXT REFERENCES atolls(code) ON DELETE CASCADE,
                name_en TEXT NOT NULL,
                name_dv TEXT,
                is_inhabited INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        for isl in islands:
            conn.execute("""
                INSERT OR IGNORE INTO islands (atoll_code, name_en, is_inhabited)
                VALUES (?, ?, ?);
            """, (isl["atoll_code"], isl["name_en"], isl["is_inhabited"]))

        # 3. Addresses
        logger.info("Seeding %d addresses into SQLite...", len(addresses))
        conn.executemany("""
            INSERT OR IGNORE INTO addresses (
                country_code, atoll_code, atoll_name_en, atoll_name_dv,
                island_name_en, island_name_dv, district, road, building_name,
                postal_code, formatted_address
            ) VALUES (
                :country_code, :atoll_code, :atoll_name_en, :atoll_name_dv,
                :island_name_en, :island_name_dv, :district, :road, :building_name,
                :postal_code, :formatted_address
            );
        """, addresses)

    logger.info("Successfully seeded geography into SQLite via get_db()")


def generate_supabase_sql(atolls: list[dict], islands: list[dict], addresses: list[dict]) -> None:
    """Generate production SQL file for Supabase PostgreSQL."""
    sql_path = PROJECT_ROOT / "supabase" / "seed_geography.sql"
    lines = [
        "-- =====================================================================",
        "-- CANONICAL MALDIVES GEOGRAPHY SEED SCRIPT FOR SUPABASE",
        "-- Seeds: Atolls, Inhabited Islands, Roads, and 6,348 Malé Addresses",
        "-- =====================================================================\n",
    ]

    # Atolls
    lines.append("-- 1. Atolls")
    lines.append("INSERT INTO atolls (code, name_en, name_dv, traditional_name) VALUES")
    atoll_vals = []
    for a in atolls:
        c = a["code"].replace("'", "''")
        ne = a["name_en"].replace("'", "''")
        nd = a["name_dv"].replace("'", "''")
        tr = a["traditional_name"].replace("'", "''")
        atoll_vals.append(f"('{c}', '{ne}', '{nd}', '{tr}')")
    lines.append(",\n".join(atoll_vals) + "\nON CONFLICT (code) DO NOTHING;\n")

    # Inhabited Islands
    lines.append("-- 2. Islands")
    island_vals = []
    for isl in islands:
        ac = isl["atoll_code"].replace("'", "''")
        ne = isl["name_en"].replace("'", "''")
        island_vals.append(f"('{ac}', '{ne}', {isl['is_inhabited']})")
    lines.append("INSERT INTO islands (atoll_code, name_en, is_inhabited) VALUES")
    lines.append(",\n".join(island_vals) + "\nON CONFLICT DO NOTHING;\n")

    # Addresses in batches
    lines.append("-- 3. Canonical Addresses (Batch insert)")
    batch_size = 500
    for i in range(0, len(addresses), batch_size):
        batch = addresses[i : i + batch_size]
        addr_vals = []
        for addr in batch:
            fmt = addr["formatted_address"].replace("'", "''")
            bld = addr["building_name"].replace("'", "''")
            rd = addr["road"].replace("'", "''")
            dist = addr["district"].replace("'", "''")
            isl = addr["island_name_en"].replace("'", "''")
            atl = addr["atoll_code"].replace("'", "''")
            post = addr["postal_code"].replace("'", "''")
            addr_vals.append(f"('MDV', '{atl}', 'Kaafu Atoll', 'ކ', '{isl}', 'މާލެ', '{dist}', '{rd}', '{bld}', '{post}', '{fmt}')")
        lines.append("INSERT INTO addresses (country_code, atoll_code, atoll_name_en, atoll_name_dv, island_name_en, island_name_dv, district, road, building_name, postal_code, formatted_address) VALUES")
        lines.append(",\n".join(addr_vals) + "\nON CONFLICT DO NOTHING;\n")

    with open(sql_path, "w", encoding="utf-8") as f:
        f.writelines("\n".join(lines))
    logger.info("Successfully wrote Supabase geography seed script (%s) - %d KB", sql_path, round(sql_path.stat().st_size / 1024))


def main() -> None:
    atolls = load_atolls()
    islands = load_islands()
    roads = load_male_roads()
    addresses = load_male_addresses(roads)

    seed_sqlite(atolls, islands, addresses)
    generate_supabase_sql(atolls, islands, addresses)


if __name__ == "__main__":
    main()
