"""
Atoll & Island Geographic Taxonomy for the Republic of Maldives.
"""
from __future__ import annotations
import re
from datetime import datetime, timezone
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
    # Addu City
    if any(k in full_text for k in ["އައްޑޫ", "Addu", "ހިތަދޫ", "މަރަދޫ", "ފޭދޫ", "ހުޅުމީދޫ", "Hithadhoo", "Maradhoo", "Feydhoo"]):
        island = "ހިތަދޫ" if "ހިތަދޫ" in full_text else ("މަރަދޫ" if "މަރަދޫ" in full_text else ("ފޭދޫ" if "ފޭދޫ" in full_text else "އައްޑޫ ސިޓީ"))
        return {"atoll_code": "S", "atoll_name_dv": "ސ. އައްޑޫ ސިޓީ", "island_name": island, "region_group": "south", "sort_order": 20}

    # Fuvahmulah City
    if any(k in full_text for k in ["ފުވައްމުލައް", "Fuvahmulah"]):
        return {"atoll_code": "Gn", "atoll_name_dv": "ޏ. ފުވައްމުލައް", "island_name": "ފުވައްމުލައް", "region_group": "south", "sort_order": 19}

    # Kulhudhuffushi City
    if any(k in full_text for k in ["ކުޅުދުއްފުށި", "Kulhudhuffushi"]):
        return {"atoll_code": "HDh", "atoll_name_dv": "ހދ. އަތޮޅު", "island_name": "ކުޅުދުއްފުށި", "region_group": "north", "sort_order": 2}

    # Thinadhoo City
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


_today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

INITIAL_OBITUARIES = [
    {
        "slug": "ibrahim-mohamed-roobyvilla",
        "name_dv": "އިބްރާހީމް މުޙައްމަދު",
        "name_en": "Ibrahim Mohamed (Former Minister Dr. Shainee's father)",
        "address_dv": "ހ. ރޫބީވިލާ / މާލެ",
        "address_en": "H. Roobyvilla, Male'",
        "age": 72,
        "funeral_mosque_dv": "މަސްޖިދުލް ތަޢާވުން (އާސަހަރާ މިސްކިތް) މާލެ",
        "funeral_mosque_en": "Masjid al-Ta'awun (Aasahara Mosque), Male'",
        "prayer_time_dv": "މިއަދުގެ ޢަޞްރު ނަމާދަށްފަހު",
        "prayer_time_en": "After Asr Prayer",
        "funeral_date": _today_str,
        "death_date": _today_str,
        "photo_url": "/static/obituaries/kashunamaadhu_sample.png",
        "contact_numbers": "7992266 / 9394545",
        "source_channel": "KashunamaadhuMV",
        "atoll_code": "K-MALE",
        "atoll_name_dv": "މާލެ / ހުޅުމާލެ",
        "island_name": "މާލެ",
        "region_group": "male",
        "sort_order": 0,
    },
    {
        "slug": "aishath-ali-dhaftharu",
        "name_dv": "ޢާއިޝަތު ޢަލީ",
        "name_en": "Aishath Ali",
        "address_dv": "ދަފްތަރު ނަންބަރު 4821 / މާލެ",
        "address_en": "Dhaftharu No. 4821, Male'",
        "age": 68,
        "funeral_mosque_dv": "މަސްޖިދުލް ޒައިދު ބިން ޘާބިތު (ހުޅުމާލެ ސަހަރާ މިސްކިތް)",
        "funeral_mosque_en": "Masjid Zayd bin Thabit (Hulhumale' Cemetery Mosque)",
        "prayer_time_dv": "މިއަދުގެ މަޣްރިބް ނަމާދަށްފަހު",
        "prayer_time_en": "After Maghrib Prayer",
        "funeral_date": _today_str,
        "death_date": _today_str,
        "photo_url": None,
        "contact_numbers": "7781234 / 9912345",
        "source_channel": "KashunamaadhuMV",
        "atoll_code": "K-MALE",
        "atoll_name_dv": "މާލެ / ހުޅުމާލެ",
        "island_name": "ހުޅުމާލެ",
        "region_group": "male",
        "sort_order": 0,
    },
    {
        "slug": "hassan-mohamed-kulhudhuffushi",
        "name_dv": "ޙަސަން މުޙައްމަދު",
        "name_en": "Hassan Mohamed",
        "address_dv": "ހުވަދޫގެ / ހދ. ކުޅުދުއްފުށި",
        "address_en": "Huvadhooge, HDh. Kulhudhuffushi",
        "age": 81,
        "funeral_mosque_dv": "މަސްޖިދުލް ޢަފާފް (ކުޅުދުއްފުށި)",
        "funeral_mosque_en": "Masjid al-Afaaf, Kulhudhuffushi",
        "prayer_time_dv": "މިއަދުގެ ޢިޝާ ނަމާދަށްފަހު",
        "prayer_time_en": "After Isha Prayer",
        "funeral_date": _today_str,
        "death_date": _today_str,
        "photo_url": None,
        "contact_numbers": "7914567",
        "source_channel": "KashunamaadhuMV",
        "atoll_code": "HDh",
        "atoll_name_dv": "ހދ. އަތޮޅު",
        "island_name": "ކުޅުދުއްފުށި",
        "region_group": "north",
        "sort_order": 2,
    },
    {
        "slug": "ahmed-saeed-addu",
        "name_dv": "އަޙްމަދު ސަޢީދު",
        "name_en": "Ahmed Saeed",
        "address_dv": "މ. ފިނިފެންމާގެ / ސ. ހިތަދޫ",
        "address_en": "M. Finifenmaage, S. Hithadhoo",
        "age": 74,
        "funeral_mosque_dv": "މަސްޖިދުލް ތަޤްވާ (ހިތަދޫ)",
        "funeral_mosque_en": "Masjid al-Taqwa, Hithadhoo",
        "prayer_time_dv": "މިއަދުގެ ޢަޞްރު ނަމާދަށްފަހު",
        "prayer_time_en": "After Asr Prayer",
        "funeral_date": _today_str,
        "death_date": _today_str,
        "photo_url": None,
        "contact_numbers": "7823456 / 9712389",
        "source_channel": "KashunamaadhuMV",
        "atoll_code": "S",
        "atoll_name_dv": "ސ. އައްޑޫ ސިޓީ",
        "island_name": "ހިތަދޫ",
        "region_group": "south",
        "sort_order": 20,
    },
]

INITIAL_JOBS = [
    {
        "notice_id": "job-treetop-nurse",
        "title": "Registered Nurse (ICU)",
        "title_en": "Registered Nurse (ICU)",
        "agency": "Tree Top Hospital",
        "agency_name_en": "Tree Top Hospital",
        "discipline": "Medical & Healthcare",
        "location": "Hulhumale'",
        "salary_raw": "MVR 16,000 - 20,000",
        "deadline_iso": "2026-10-30T14:00:00",
        "published_date": "2026-10-15",
        "source_url": "https://treetophospital.com/careers/nurse",
        "source_portal": "treetophospital.com",
        "requirements": "Diploma or Degree in Nursing.",
    },
    {
        "notice_id": "job-ey-audit",
        "title": "Audit Associate",
        "title_en": "Audit Associate",
        "agency": "Ernst & Young",
        "agency_name_en": "Ernst & Young",
        "discipline": "Finance, Accounting & Procurement",
        "location": "Male'",
        "salary_raw": "MVR 15,000 - 18,000",
        "deadline_iso": "2026-10-31T15:00:00",
        "published_date": "2026-10-16",
        "source_url": "https://mycareer.gov.mv/en/jobs/audit-associate",
        "source_portal": "mycareer.gov.mv",
        "requirements": "ACCA / CIMA part-qualified or Bachelor degree.",
    },
    {
        "notice_id": "job-joali-airport-mgr",
        "title": "Cluster Airport Manager (Ultra-Luxury Guest Relations)",
        "title_en": "Cluster Airport Manager (Ultra-Luxury Guest Relations)",
        "agency": "Joali Maldives & Alibey Resorts",
        "agency_name_en": "Joali Maldives & Alibey Resorts",
        "discipline": "Hospitality, Tourism & Resorts",
        "location": "Velana International Airport / Raa Atoll",
        "salary_raw": "Competitive + Service Charge",
        "deadline_iso": "2026-10-31T15:00:00",
        "published_date": "2026-10-15",
        "source_url": "https://job-maldives.com/2026/10/cluster-airport-manager-joali-maldives/",
        "source_portal": "job-maldives.com",
        "requirements": "Minimum 5 years leadership in luxury airport lounge/guest operations, VIP/CIP handling, and TMA seaplane coordination.",
        "is_active": 1,
    },
    {
        "notice_id": "job-sto-shop-sup",
        "title": "Shop Operations Supervisor (Retail Supermart)",
        "title_en": "Shop Operations Supervisor (Retail Supermart)",
        "agency": "State Trading Organization (STO)",
        "agency_name_en": "State Trading Organization Plc",
        "discipline": "Customer Service, Retail & Operations",
        "location": "Male'",
        "salary_raw": "MVR 14,500 - 18,000",
        "deadline_iso": "2026-10-27T14:00:00",
        "published_date": "2026-10-14",
        "source_url": "https://gazette.gov.mv/iulaan/248530",
        "source_portal": "gazette.gov.mv",
        "requirements": "Experience in supermarket/retail inventory management, POS reconciliation, and front-line customer handling.",
        "is_active": 1,
    },
    {
        "notice_id": "job-mira-net-sec",
        "title": "Senior Network Security Engineer",
        "title_en": "Senior Network Security Engineer",
        "agency": "Maldives Inland Revenue Authority (MIRA)",
        "agency_name_en": "Maldives Inland Revenue Authority",
        "discipline": "IT, Tech & Communications",
        "location": "Male'",
        "salary_raw": "MVR 22,000 - 28,000",
        "deadline_iso": "2026-10-28T13:00:00",
        "published_date": "2026-10-13",
        "source_url": "https://gazette.gov.mv/iulaan/248912",
        "source_portal": "gazette.gov.mv",
        "requirements": "BSc in Cybersecurity or Computer Science, CCNP/CISSP certified with enterprise firewall experience.",
        "is_active": 1,
    },
    {
        "notice_id": "job-igmh-ped-spec",
        "title": "Specialist Medical Officer (Pediatrics)",
        "title_en": "Specialist Medical Officer (Pediatrics)",
        "agency": "Indira Gandhi Memorial Hospital (IGMH)",
        "agency_name_en": "Indira Gandhi Memorial Hospital",
        "discipline": "Medical & Healthcare",
        "location": "Male'",
        "salary_raw": "MVR 34,000 - 45,000",
        "deadline_iso": "2026-11-05T14:00:00",
        "published_date": "2026-10-12",
        "source_url": "https://gazette.gov.mv/iulaan/247981",
        "source_portal": "gazette.gov.mv",
        "requirements": "MBBS with MD/Master in Pediatrics, Maldives Medical and Dental Council registration.",
        "is_active": 1,
    },
    {
        "notice_id": "job-min-infra-eng",
        "title": "Civil Engineer (Harbour & Coastal Infrastructure)",
        "title_en": "Civil Engineer (Harbour & Coastal Infrastructure)",
        "agency": "Ministry of Construction and Infrastructure",
        "agency_name_en": "Ministry of Construction and Infrastructure",
        "discipline": "Construction, Architecture & Engineering",
        "location": "Male' / Project Sites",
        "salary_raw": "MVR 20,000 - 26,000",
        "deadline_iso": "2026-10-29T14:00:00",
        "published_date": "2026-10-14",
        "source_url": "https://gazette.gov.mv/iulaan/248102",
        "source_portal": "gazette.gov.mv",
        "requirements": "Degree in Civil Engineering, AutoCAD/Revit proficiency, experience supervising breakwaters and reclamation.",
        "is_active": 1,
    },
    {
        "notice_id": "job-stelco-power-mgr",
        "title": "Electrical Power Systems Project Manager",
        "title_en": "Electrical Power Systems Project Manager",
        "agency": "State Electric Company Limited (STELCO)",
        "agency_name_en": "State Electric Company Limited",
        "discipline": "Construction, Architecture & Engineering",
        "location": "Male' / Greater Malé Grid",
        "salary_raw": "MVR 24,000 - 30,000",
        "deadline_iso": "2026-10-30T14:00:00",
        "published_date": "2026-10-11",
        "source_url": "https://gazette.gov.mv/iulaan/248440",
        "source_portal": "gazette.gov.mv",
        "requirements": "BSc in Electrical Engineering, MV/HV grid distribution experience, switchgear maintenance.",
        "is_active": 1,
    },
    {
        "notice_id": "job-hdc-proc-lead",
        "title": "Senior Procurement Officer",
        "title_en": "Senior Procurement Officer",
        "agency": "Housing Development Corporation (HDC)",
        "agency_name_en": "Housing Development Corporation",
        "discipline": "Finance, Accounting & Procurement",
        "location": "Hulhumale'",
        "salary_raw": "MVR 18,000 - 22,000",
        "deadline_iso": "2026-10-26T13:00:00",
        "published_date": "2026-10-10",
        "source_url": "https://jobs.hdc.mv/announcements/senior-procurement-officer-2026",
        "source_portal": "hdc.mv",
        "requirements": "Degree in Procurement, Supply Chain or Accounting. CIPS qualifications preferred.",
        "is_active": 1,
    },
    {
        "notice_id": "job-male-city-admin",
        "title": "Senior Administrative Officer",
        "title_en": "Senior Administrative Officer",
        "agency": "Malé City Council",
        "agency_name_en": "Malé City Council",
        "discipline": "Administration & Management",
        "location": "Male'",
        "salary_raw": "MVR 12,000 - 15,000",
        "deadline_iso": "2026-10-25T13:30:00",
        "published_date": "2026-10-12",
        "source_url": "https://gazette.gov.mv/iulaan/248315",
        "source_portal": "gazette.gov.mv",
        "requirements": "Diploma/Degree in Public Administration or Business Administration. Strong Thaana & English communication.",
        "is_active": 1,
    },
    {
        "notice_id": "job-macl-transport-lead",
        "title": "Airport Fleet & Transport Coordinator",
        "title_en": "Airport Fleet & Transport Coordinator",
        "agency": "Maldives Airports Company Limited (MACL)",
        "agency_name_en": "Maldives Airports Company Limited",
        "discipline": "Land Transport",
        "location": "Velana International Airport (Hulhulé)",
        "salary_raw": "MVR 15,000 - 19,000",
        "deadline_iso": "2026-11-02T14:00:00",
        "published_date": "2026-10-14",
        "source_url": "https://gazette.gov.mv/iulaan/248720",
        "source_portal": "gazette.gov.mv",
        "requirements": "Valid Maldivian Driving License (B1/B2/C1/C2), experience dispatching passenger transport and VIP vehicles.",
        "is_active": 1,
    },
    {
        "notice_id": "job-finolhu-guest-rel",
        "title": "VIP Guest Relations Representative",
        "title_en": "VIP Guest Relations Representative",
        "agency": "Finolhu Island Resort",
        "agency_name_en": "Finolhu Island Resort",
        "discipline": "Hospitality, Tourism & Resorts",
        "location": "Baa Atoll / Male' Airport Office",
        "salary_raw": "USD 900 - 1,400 + SC",
        "deadline_iso": "2026-11-04T16:00:00",
        "published_date": "2026-10-15",
        "source_url": "https://job-maldives.com/2026/10/vip-guest-relations-finolhu-island/",
        "source_portal": "job-maldives.com",
        "requirements": "Fluency in English (multilingual Dhivehi/German a plus). Exceptional guest service etiquette.",
        "is_active": 1,
    },
    {
        "notice_id": "job-dharumavantha-edu",
        "title": "Secondary English Teacher (Grade 9 & 10)",
        "title_en": "Secondary English Teacher (Grade 9 & 10)",
        "agency": "Dharumavantha School / Ministry of Education",
        "agency_name_en": "Ministry of Education",
        "discipline": "Education & Teaching",
        "location": "Male'",
        "salary_raw": "Civil Service Teacher Matrix (MVR 16,000 - 20,000)",
        "deadline_iso": "2026-10-29T13:00:00",
        "published_date": "2026-10-13",
        "source_url": "https://gazette.gov.mv/iulaan/248604",
        "source_portal": "gazette.gov.mv",
        "requirements": "Bachelor of Education in English or relevant discipline. Cambridge O'Level curriculum experience.",
        "is_active": 1,
    },
]


