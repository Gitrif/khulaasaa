"""
Company Profiles Repository (Maldivian MED & International Bidders).
"""
from __future__ import annotations
import json
import sqlite3
from typing import Any, Optional

def save_company_profile(
    conn: sqlite3.Connection,
    profile_data: dict[str, Any],
    user_id: Optional[int] = None,
    profile_id: Optional[int] = None,
) -> int:
    """Save or update a company profile for government & private bid submissions."""
    company_name = (profile_data.get("company_name") or "My Company Pvt Ltd").strip()
    entity_type = (profile_data.get("entity_type") or "maldivian").strip()
    country_of_origin = (profile_data.get("country_of_origin") or "Maldives").strip()
    reg_no = (profile_data.get("registration_number") or "").strip()
    reg_date = (profile_data.get("registration_date") or "").strip()
    tin_no = (profile_data.get("tin_number") or "").strip()
    foreign_reg_no = (profile_data.get("foreign_reg_no") or "").strip()
    foreign_tax_id = (profile_data.get("foreign_tax_id") or "").strip()
    local_agent_name = (profile_data.get("local_agent_name") or "").strip()
    local_agent_reg = (profile_data.get("local_agent_reg") or "").strip()
    local_agent_phone = (profile_data.get("local_agent_phone") or "").strip()
    local_agent_email = (profile_data.get("local_agent_email") or "").strip()
    reg_addr = (profile_data.get("registered_address") or "").strip()
    phone = (profile_data.get("phone") or "").strip()
    email = (profile_data.get("email") or "").strip()
    website = (profile_data.get("website") or "").strip()
    philosophy = (profile_data.get("philosophy") or "").strip()
    mission = (profile_data.get("mission") or "").strip()
    md_name = (profile_data.get("managing_director_name") or "").strip()
    md_msg = (profile_data.get("managing_director_message") or "").strip()
    directors_json = json.dumps(profile_data.get("directors") or [], ensure_ascii=False)
    core_biz_json = json.dumps(profile_data.get("core_business") or [], ensure_ascii=False)
    values_json = json.dumps(profile_data.get("values") or [], ensure_ascii=False)
    clients_json = json.dumps(profile_data.get("clients") or [], ensure_ascii=False)
    logo_data = profile_data.get("logo_data")
    cover_image_url = profile_data.get("cover_image_url")
    template = profile_data.get("template", "corporate")

    if profile_id:
        conn.execute(
            """
            UPDATE company_profiles SET
                company_name = ?, entity_type = ?, country_of_origin = ?, registration_number = ?, registration_date = ?, tin_number = ?,
                foreign_reg_no = ?, foreign_tax_id = ?, local_agent_name = ?, local_agent_reg = ?, local_agent_phone = ?, local_agent_email = ?,
                registered_address = ?, phone = ?, email = ?, website = ?,
                philosophy = ?, mission = ?, managing_director_name = ?, managing_director_message = ?,
                directors_json = ?, core_business_json = ?, values_json = ?, clients_json = ?,
                logo_data = COALESCE(?, logo_data), cover_image_url = COALESCE(?, cover_image_url),
                template = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
            """,
            (
                company_name, entity_type, country_of_origin, reg_no, reg_date, tin_no,
                foreign_reg_no, foreign_tax_id, local_agent_name, local_agent_reg, local_agent_phone, local_agent_email,
                reg_addr, phone, email, website,
                philosophy, mission, md_name, md_msg, directors_json, core_biz_json, values_json, clients_json,
                logo_data, cover_image_url, template, profile_id,
            ),
        )
        return profile_id
    elif user_id:
        existing = conn.execute("SELECT id FROM company_profiles WHERE user_id = ?;", (user_id,)).fetchone()
        if existing:
            return save_company_profile(conn, profile_data, user_id=None, profile_id=existing["id"])

    cursor = conn.execute(
        """
        INSERT INTO company_profiles (
            user_id, company_name, entity_type, country_of_origin, registration_number, registration_date, tin_number,
            foreign_reg_no, foreign_tax_id, local_agent_name, local_agent_reg, local_agent_phone, local_agent_email,
            registered_address, phone, email, website, philosophy, mission,
            managing_director_name, managing_director_message, directors_json, core_business_json,
            values_json, clients_json, logo_data, cover_image_url, template
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id;
        """,
        (
            user_id, company_name, entity_type, country_of_origin, reg_no, reg_date, tin_no,
            foreign_reg_no, foreign_tax_id, local_agent_name, local_agent_reg, local_agent_phone, local_agent_email,
            reg_addr, phone, email, website, philosophy, mission,
            md_name, md_msg, directors_json, core_biz_json,
            values_json, clients_json, logo_data, cover_image_url, template,
        ),
    )
    row = cursor.fetchone()
    return row[0] if row else 0


def get_company_profile(
    conn: sqlite3.Connection,
    profile_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> Optional[dict[str, Any]]:
    """Retrieve a company profile by ID or for an authenticated user."""
    if profile_id:
        row = conn.execute("SELECT * FROM company_profiles WHERE id = ?;", (profile_id,)).fetchone()
    elif user_id:
        row = conn.execute("SELECT * FROM company_profiles WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1;", (user_id,)).fetchone()
    else:
        row = conn.execute("SELECT * FROM company_profiles ORDER BY updated_at DESC LIMIT 1;").fetchone()

    if not row:
        return None

    d = dict(row)
    d.setdefault("entity_type", "maldivian")
    d.setdefault("country_of_origin", "Maldives")
    d.setdefault("foreign_reg_no", "")
    d.setdefault("foreign_tax_id", "")
    d.setdefault("local_agent_name", "")
    d.setdefault("local_agent_reg", "")
    d.setdefault("local_agent_phone", "")
    d.setdefault("local_agent_email", "")
    for field in ["directors_json", "core_business_json", "values_json", "clients_json"]:
        raw = d.get(field)
        clean_key = field.replace("_json", "")
        try:
            d[clean_key] = json.loads(raw) if raw else []
        except Exception:
            d[clean_key] = []
    return d


# Standard Maldivian and international constants
STANDARD_LANGUAGES = [
    "English",
    "Dhivehi",
    "Arabic",
    "Hindi",
    "Urdu",
    "Sinhala",
    "Bengali",
    "Malayalam",
    "Tamil",
    "French",
    "Russian",
    "Chinese",
    "German",
]

LANGUAGE_PROFICIENCIES = [
    "Native / Bilingual (މާދަރީ ބަސް)",
    "Fluent / Full Professional",
    "Professional Working",
    "Intermediate / Conversational",
    "Elementary / Basic",
]

EDUCATION_LEVELS = [
    "Primary School",
    "Secondary / O-Level",
    "Higher Secondary / A-Level",
    "Certificate / Diploma",
    "Advanced Diploma",
    "Undergraduate / Bachelor's Degree",
    "Postgraduate Diploma",
    "Master's Degree",
    "PhD / Doctorate",
]

STANDARD_INSTITUTIONS = [
    "The Maldives National University (MNU)",
    "Villa College",
    "Cyryx College",
    "MAPS College",
    "Avid College",
    "Islamic University of Maldives (IUM)",
    "Center for Higher Secondary Education (CHSE)",
    "Majeediyya School",
    "Aminiya School",
    "Dharumavantha School",
    "Ahmadhiyya International School",
    "Kalaafaanu School",
    "Maldives Polytechnic",
    "Other / Overseas University",
]


# =====================================================================
# Jobs Directory & Scraping Repository
# =====================================================================

