"""
Jobs Repository.
"""
from __future__ import annotations
import json
import secrets
import sqlite3
from typing import Any, Optional

# Standard Maldivian and international constants for CVs and Job Applications
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
]


def upsert_job(conn: sqlite3.Connection, job_data: dict[str, Any]) -> int:
    """Insert or update a job record."""
    notice_id = job_data.get("notice_id") or f"job-{secrets.token_hex(4)}"
    cursor = conn.execute(
        """
        INSERT INTO jobs (
            notice_id, title, title_en, agency, agency_name_en, discipline,
            location, salary_raw, deadline_iso, published_date, source_url,
            source_portal, requirements, is_active
        )
        VALUES (
            :notice_id, :title, :title_en, :agency, :agency_name_en, :discipline,
            :location, :salary_raw, :deadline_iso, :published_date, :source_url,
            :source_portal, :requirements, :is_active
        )
        ON CONFLICT(notice_id) DO UPDATE SET
            title = excluded.title,
            title_en = COALESCE(excluded.title_en, jobs.title_en),
            agency = excluded.agency,
            agency_name_en = COALESCE(excluded.agency_name_en, jobs.agency_name_en),
            discipline = excluded.discipline,
            location = excluded.location,
            salary_raw = COALESCE(excluded.salary_raw, jobs.salary_raw),
            deadline_iso = COALESCE(excluded.deadline_iso, jobs.deadline_iso),
            published_date = COALESCE(excluded.published_date, jobs.published_date),
            source_url = excluded.source_url,
            requirements = COALESCE(excluded.requirements, jobs.requirements),
            is_active = excluded.is_active
        RETURNING id;
        """,
        {
            "notice_id": notice_id,
            "title": job_data["title"],
            "title_en": job_data.get("title_en"),
            "agency": job_data.get("agency", "Maldives Public Service"),
            "agency_name_en": job_data.get("agency_name_en"),
            "discipline": job_data.get("discipline", "Other"),
            "location": job_data.get("location", "Male'"),
            "salary_raw": job_data.get("salary_raw"),
            "deadline_iso": job_data.get("deadline_iso"),
            "published_date": job_data.get("published_date") or job_data.get("published_raw"),
            "source_url": job_data.get("source_url") or job_data.get("url"),
            "source_portal": job_data.get("source_portal", "gazette.gov.mv"),
            "requirements": job_data.get("requirements"),
            "is_active": job_data.get("is_active", 1),
        },
    )
    row = cursor.fetchone()
    return row[0] if row else 0


def query_jobs(
    conn: sqlite3.Connection,
    discipline: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Query jobs with optional discipline and search keyword filters."""
    sql = "SELECT id, notice_id, title, title_en, agency, agency_name_en, discipline, location, salary_raw, deadline_iso, published_date, source_url, source_portal, requirements, is_active FROM jobs WHERE is_active = 1"
    params: list[Any] = []

    if discipline and discipline.lower() != "all":
        # Handle legacy category aliases gracefully
        if discipline == "Aviation, Marine & Logistics":
            sql += " AND discipline IN (?, ?, ?, ?)"
            params.extend(["Aviation", "Land Transport", "Sea Transport", "Aviation, Marine & Logistics"])
        elif discipline in ("Finance, Accounting & Banking", "Finance, Accounting & Procurement"):
            sql += " AND discipline IN (?, ?)"
            params.extend(["Finance, Accounting & Procurement", "Finance, Accounting & Banking"])
        else:
            sql += " AND discipline = ?"
            params.append(discipline)

    if search:
        sql += " AND (title LIKE ? OR agency LIKE ? OR title_en LIKE ? OR agency_name_en LIKE ?)"
        s = f"%{search.strip()}%"
        params.extend([s, s, s, s])

    sql += " ORDER BY deadline_iso ASC, created_at DESC LIMIT ?;"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_job_disciplines(conn: sqlite3.Connection) -> list[str]:
    """Get all distinct active job disciplines."""
    rows = conn.execute("SELECT DISTINCT discipline FROM jobs WHERE is_active = 1 AND discipline IS NOT NULL AND discipline != '' ORDER BY discipline ASC;").fetchall()
    return [r[0] for r in rows]


def get_job_by_id(conn: sqlite3.Connection, job_id: int) -> Optional[dict[str, Any]]:
    """Retrieve job by primary key ID."""
    row = conn.execute(
        "SELECT id, notice_id, title, title_en, agency, agency_name_en, discipline, location, salary_raw, deadline_iso, published_date, source_url, source_portal, requirements, is_active FROM jobs WHERE id = ?;",
        (job_id,),
    ).fetchone()
    return dict(row) if row else None



