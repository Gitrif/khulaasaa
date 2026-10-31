"""
Atoll & Island Geographic Taxonomy for the Republic of Maldives.
Pure classification and resolution module: contains zero database, service, or alert dependencies.
"""
from __future__ import annotations

import re
from typing import Any, Optional

ATOLL_TAXONOMY = [
    # Male' & Greater Male'
    {"code": "K-MALE", "prefix_dv": "މާލެ", "atoll_dv": "މާލެ / ހުޅުމާލެ", "atoll_en": "Malé & Hulhumalé", "region": "male", "sort": 0},
    # North Atolls
    {"code": "HA", "prefix_dv": "ހއ", "atoll_dv": "ހއ. އަތޮޅު", "atoll_en": "Haa Alif", "region": "north", "sort": 1},
    {"code": "HDh", "prefix_dv": "ހދ", "atoll_dv": "ހދ. އަތޮޅު", "atoll_en": "Haa Dhaalu", "region": "north", "sort": 2},
    {"code": "Sh", "prefix_dv": "ށ", "atoll_dv": "ށ. އަތޮޅު", "atoll_en": "Shaviyani", "region": "north", "sort": 3},
    {"code": "N", "prefix_dv": "ނ", "atoll_dv": "ނ. އަތޮޅު", "atoll_en": "Noonu", "region": "north", "sort": 4},
    {"code": "R", "prefix_dv": "ރ", "atoll_dv": "ރ. އަތޮޅު", "atoll_en": "Raa", "region": "north", "sort": 5},
    {"code": "B", "prefix_dv": "ބ", "atoll_dv": "ބ. އަތޮޅު", "atoll_en": "Baa", "region": "north", "sort": 6},
    {"code": "Lh", "prefix_dv": "ޅ", "atoll_dv": "ޅ. އަތޮޅު", "atoll_en": "Lhaviyani", "region": "north", "sort": 7},
    # Central Atolls
    {"code": "K", "prefix_dv": "ކ", "atoll_dv": "ކ. އަތޮޅު", "atoll_en": "Kaafu", "region": "central", "sort": 8},
    {"code": "AA", "prefix_dv": "އއ", "atoll_dv": "އއ. އަތޮޅު", "atoll_en": "Alif Alif", "region": "central", "sort": 9},
    {"code": "ADh", "prefix_dv": "އދ", "atoll_dv": "އދ. އަތޮޅު", "atoll_en": "Alif Dhaalu", "region": "central", "sort": 10},
    {"code": "V", "prefix_dv": "ވ", "atoll_dv": "ވ. އަތޮޅު", "atoll_en": "Vaavu", "region": "central", "sort": 11},
    {"code": "M", "prefix_dv": "މ", "atoll_dv": "މ. އަތޮޅު", "atoll_en": "Meemu", "region": "central", "sort": 12},
    {"code": "F", "prefix_dv": "ފ", "atoll_dv": "ފ. އަތޮޅު", "atoll_en": "Faafu", "region": "central", "sort": 13},
    {"code": "Dh", "prefix_dv": "ދ", "atoll_dv": "ދ. އަތޮޅު", "atoll_en": "Dhaalu", "region": "central", "sort": 14},
    # South Atolls
    {"code": "Th", "prefix_dv": "ތ", "atoll_dv": "ތ. އަތޮޅު", "atoll_en": "Thaa", "region": "south", "sort": 15},
    {"code": "L", "prefix_dv": "ލ", "atoll_dv": "ލ. އަތޮޅު", "atoll_en": "Laamu", "region": "south", "sort": 16},
    {"code": "GA", "prefix_dv": "ގއ", "atoll_dv": "ގއ. އަތޮޅު", "atoll_en": "Gaafu Alif", "region": "south", "sort": 17},
    {"code": "GDh", "prefix_dv": "ގދ", "atoll_dv": "ގދ. އަތޮޅު", "atoll_en": "Gaafu Dhaalu", "region": "south", "sort": 18},
    {"code": "Gn", "prefix_dv": "ޏ", "atoll_dv": "ޏ. ފުވައްމުލައް", "atoll_en": "Gnaviyani (Fuvahmulah)", "region": "south", "sort": 19},
    {"code": "S", "prefix_dv": "ސ", "atoll_dv": "ސ. އައްޑޫ ސިޓީ", "atoll_en": "Seenu (Addu City)", "region": "south", "sort": 20},
]


def extract_atoll_and_island(
    address_dv: Optional[str] = None,
    address_en: Optional[str] = None,
    mosque_dv: Optional[str] = None,
    mosque_en: Optional[str] = None,
) -> dict[str, Any]:
    """
    Extracts atoll code, Dhivehi atoll name, island name, and geographical region
    from address and cemetery mosque strings.
    """
    text_dv = f"{address_dv or ''} {mosque_dv or ''}".strip()
    text_en = f"{address_en or ''} {mosque_en or ''}".strip()
    full_text = f"{text_dv} {text_en}"

    # 1. Distinct Administrative Cities
    if any(k in full_text for k in ["އައްޑޫ", "Addu", "ހިތަދޫ", "މަރަދޫ", "ފޭދޫ", "ހުޅުމީދޫ", "Hithadhoo", "Maradhoo", "Feydhoo"]):
        island = "ހިތަދޫ" if "ހިތަދޫ" in full_text else ("މަރަދޫ" if "މަރަދޫ" in full_text else ("ފޭދޫ" if "ފޭދޫ" in full_text else "އައްޑޫ ސިޓީ"))
        return {"atoll_code": "S", "atoll_name_dv": "ސ. އައްޑޫ ސިޓީ", "island_name": island, "region_group": "south", "sort_order": 20}

    if any(k in full_text for k in ["ފުވައްމުލައް", "Fuvahmulah"]):
        return {"atoll_code": "Gn", "atoll_name_dv": "ޏ. ފުވައްމުލައް", "island_name": "ފުވައްމުލައް", "region_group": "south", "sort_order": 19}

    if any(k in full_text for k in ["ކުޅުދުއްފުށި", "Kulhudhuffushi"]):
        return {"atoll_code": "HDh", "atoll_name_dv": "ހދ. އަތޮޅު", "island_name": "ކުޅުދުއްފުށި", "region_group": "north", "sort_order": 2}

    if any(k in full_text for k in ["ތިނަދޫ", "Thinadhoo"]):
        return {"atoll_code": "GDh", "atoll_name_dv": "ގދ. އަތޮޅު", "island_name": "ތިނަދޫ", "region_group": "south", "sort_order": 18}

    # 2. Dhivehi Atoll Prefix pattern (e.g. "ހދ. ކުޅުދުއްފުށި", "ބ. އޭދަފުށި")
    m_dv = re.search(r"(?:^|\s|\/|,)(ހއ|ހދ|ށ|ނ|ރ|ބ|ޅ|ކ|އއ|އދ|ވ|މ|ފ|ދ|ތ|ލ|ގއ|ގދ|ޏ|ސ)\.\s*([^\/\n,\(\)]+)?", text_dv)
    if m_dv:
        pfx = m_dv.group(1).strip()
        isl = (m_dv.group(2) or "").strip()
        matched = next((a for a in ATOLL_TAXONOMY if a.get("prefix_dv") == pfx), None)
        if matched:
            return {
                "atoll_code": matched["code"],
                "atoll_name_dv": matched["atoll_dv"],
                "island_name": isl or matched["atoll_dv"],
                "region_group": matched["region"],
                "sort_order": matched["sort"],
            }

    # 3. English Atoll Prefix pattern (e.g. "HDh. Kulhudhuffushi", "B. Eydhafushi")
    m_en = re.search(r"\b(HA|HDh|Sh|N|R|B|Lh|K|AA|ADh|V|M|F|Dh|Th|L|GA|GDh|Gn|S)\.\s*([^\/\n,]+)?", text_en, re.IGNORECASE)
    if m_en:
        code_upper = m_en.group(1).upper()
        isl = (m_en.group(2) or "").strip()
        matched = next((a for a in ATOLL_TAXONOMY if a["code"].upper() == code_upper), None)
        if matched:
            return {
                "atoll_code": matched["code"],
                "atoll_name_dv": matched["atoll_dv"],
                "island_name": isl or matched["atoll_en"],
                "region_group": matched["region"],
                "sort_order": matched["sort"],
            }

    # 4. Greater Male' area (Male', Hulhumale', Vilimale', Aasahara)
    if any(k in full_text for k in ["ހުޅުމާލެ", "Hulhumale", "Hulhumalé"]):
        return {"atoll_code": "K-MALE", "atoll_name_dv": "މާލެ / ހުޅުމާލެ", "island_name": "ހުޅުމާލެ", "region_group": "male", "sort_order": 0}
    if any(k in full_text for k in ["ވިލިމާލެ", "Vilimale", "Vilimalé", "ވިލިނގިލި"]):
        return {"atoll_code": "K-MALE", "atoll_name_dv": "މާލެ / ހުޅުމާލެ", "island_name": "ވިލިމާލެ", "region_group": "male", "sort_order": 0}
    if any(k in full_text for k in ["މާލެ", "މާލޭ", "Male", "Male'", "އާސަހަރާ", "އިސްލާމީ މަރުކަޒު"]):
        return {"atoll_code": "K-MALE", "atoll_name_dv": "މާލެ / ހުޅުމާލެ", "island_name": "މާލެ", "region_group": "male", "sort_order": 0}

    # 5. Fallback
    return {
        "atoll_code": "K-MALE",
        "atoll_name_dv": "މާލެ / ހުޅުމާލެ",
        "island_name": "މާލެ",
        "region_group": "male",
        "sort_order": 0,
    }
