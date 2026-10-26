"""
Reference Data Repository for Khulaasaa.
Encapsulates lookups for Days of the Week, Gregorian Months,
Hijri Calendar Months, Prayer Times, and Administrative Districts.
Adheres to single-source-of-truth and atomic relational principles.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Canonical In-Memory Constant Dictionaries for Instant 0ms Lookups
DAYS_DATA: list[dict[str, Any]] = [
    {"day_number": 1, "code": "SUN", "name_en": "Sunday", "name_dv": "އާދީއްތަ", "is_weekend": 0},
    {"day_number": 2, "code": "MON", "name_en": "Monday", "name_dv": "ހޯމަ", "is_weekend": 0},
    {"day_number": 3, "code": "TUE", "name_en": "Tuesday", "name_dv": "އަންގާރަ", "is_weekend": 0},
    {"day_number": 4, "code": "WED", "name_en": "Wednesday", "name_dv": "ބުދަ", "is_weekend": 0},
    {"day_number": 5, "code": "THU", "name_en": "Thursday", "name_dv": "ބުރާސްފަތި", "is_weekend": 0},
    {"day_number": 6, "code": "FRI", "name_en": "Friday", "name_dv": "ހުކުރު", "is_weekend": 1},
    {"day_number": 7, "code": "SAT", "name_en": "Saturday", "name_dv": "ހޮނިހިރު", "is_weekend": 1},
]

MONTHS_DATA: list[dict[str, Any]] = [
    {"month_number": 1, "code": "JAN", "name_en": "January", "name_dv": "ޖެނުއަރީ", "abbr_en": "Jan", "days_count": 31},
    {"month_number": 2, "code": "FEB", "name_en": "February", "name_dv": "ފެބްރުއަރީ", "abbr_en": "Feb", "days_count": 28},
    {"month_number": 3, "code": "MAR", "name_en": "March", "name_dv": "މާރިޗު", "abbr_en": "Mar", "days_count": 31},
    {"month_number": 4, "code": "APR", "name_en": "April", "name_dv": "އޭޕްރީލް", "abbr_en": "Apr", "days_count": 30},
    {"month_number": 5, "code": "MAY", "name_en": "May", "name_dv": "މޭ", "abbr_en": "May", "days_count": 31},
    {"month_number": 6, "code": "JUN", "name_en": "June", "name_dv": "ޖޫން", "abbr_en": "Jun", "days_count": 30},
    {"month_number": 7, "code": "JUL", "name_en": "July", "name_dv": "ޖުލައި", "abbr_en": "Jul", "days_count": 31},
    {"month_number": 8, "code": "AUG", "name_en": "August", "name_dv": "އޯގަސްޓް", "abbr_en": "Aug", "days_count": 31},
    {"month_number": 9, "code": "SEP", "name_en": "September", "name_dv": "ސެޕްޓެމްބަރ", "abbr_en": "Sep", "days_count": 30},
    {"month_number": 10, "code": "OCT", "name_en": "October", "name_dv": "އޮކްޓޫބަރު", "abbr_en": "Oct", "days_count": 31},
    {"month_number": 11, "code": "NOV", "name_en": "November", "name_dv": "ނޮވެމްބަރު", "abbr_en": "Nov", "days_count": 30},
    {"month_number": 12, "code": "DEC", "name_en": "December", "name_dv": "ޑިސެމްބަރު", "abbr_en": "Dec", "days_count": 31},
]

HIJRI_MONTHS_DATA: list[dict[str, Any]] = [
    {"month_number": 1, "name_en": "Muharram", "name_dv": "މުޙައްރަމް", "name_ar": "محرم"},
    {"month_number": 2, "name_en": "Safar", "name_dv": "ޞަފަރު", "name_ar": "صفر"},
    {"month_number": 3, "name_en": "Rabi al-Awwal", "name_dv": "ރަބީޢުލްއައްވަލް", "name_ar": "ربيع الأول"},
    {"month_number": 4, "name_en": "Rabi al-Thani", "name_dv": "ރަބީޢުލްއާޚިރު", "name_ar": "ربيع الثاني"},
    {"month_number": 5, "name_en": "Jumada al-Awwal", "name_dv": "ޖުމާދަލްއޫލާ", "name_ar": "جمادى الأولى"},
    {"month_number": 6, "name_en": "Jumada al-Thani", "name_dv": "ޖުމާދަލްއާޚިރާ", "name_ar": "جمادى الآخرة"},
    {"month_number": 7, "name_en": "Rajab", "name_dv": "ރަޖަބް", "name_ar": "رجب"},
    {"month_number": 8, "name_en": "Shaban", "name_dv": "ޝަޢުބާން", "name_ar": "شعبان"},
    {"month_number": 9, "name_en": "Ramadan", "name_dv": "ރަމަޟާން", "name_ar": "رمضان"},
    {"month_number": 10, "name_en": "Shawwal", "name_dv": "ޝައްވާލް", "name_ar": "شوال"},
    {"month_number": 11, "name_en": "Dhu al-Qadah", "name_dv": "ޛުލްޤަޢިދާ", "name_ar": "ذو القعدة"},
    {"month_number": 12, "name_en": "Dhu al-Hijjah", "name_dv": "ޛުލްޙިއްޖާ", "name_ar": "ذو الحجة"},
]

PRAYER_TIMES_DATA: list[dict[str, Any]] = [
    {"id": 1, "slug": "fajr", "name_en": "Fajr", "name_dv": "ފަތިސް", "sort_order": 1},
    {"id": 2, "slug": "dhuhr", "name_en": "Dhuhr", "name_dv": "މެންދުރު", "sort_order": 2},
    {"id": 3, "slug": "asr", "name_en": "Asr", "name_dv": "ޢަޞްރު", "sort_order": 3},
    {"id": 4, "slug": "maghrib", "name_en": "Maghrib", "name_dv": "މަޣްރިބް", "sort_order": 4},
    {"id": 5, "slug": "isha", "name_en": "Isha", "name_dv": "ޢިޝާ", "sort_order": 5},
]

DISTRICTS_DATA: list[dict[str, Any]] = [
    {"code": "H", "name_en": "Henveiru", "name_dv": "ހެންވޭރު", "island_name_en": "Male"},
    {"code": "G", "name_en": "Galolhu", "name_dv": "ގަލޮޅު", "island_name_en": "Male"},
    {"code": "M", "name_en": "Machangoalhi", "name_dv": "މައްޗަންގޮޅި", "island_name_en": "Male"},
    {"code": "MA", "name_en": "Maafannu", "name_dv": "މާފަންނު", "island_name_en": "Male"},
    {"code": "V", "name_en": "Vilimalé", "name_dv": "ވިލިމާލެ", "island_name_en": "Vilimale"},
    {"code": "H1", "name_en": "Hulhumalé Phase 1", "name_dv": "ހުޅުމާލެ ފޭސް 1", "island_name_en": "Hulhumale"},
    {"code": "H2", "name_en": "Hulhumalé Phase 2", "name_dv": "ހުޅުމާލެ ފޭސް 2", "island_name_en": "Hulhumale"},
]


def seed_reference_tables(conn: sqlite3.Connection) -> None:
    """Seed canonical reference tables into database if empty."""
    # 1. Days
    for d in DAYS_DATA:
        conn.execute(
            """
            INSERT INTO ref_days (day_number, code, name_en, name_dv, is_weekend)
            VALUES (:day_number, :code, :name_en, :name_dv, :is_weekend)
            ON CONFLICT(day_number) DO UPDATE SET
                name_en = excluded.name_en,
                name_dv = excluded.name_dv,
                code = excluded.code;
            """,
            d,
        )

    # 2. Months
    for m in MONTHS_DATA:
        conn.execute(
            """
            INSERT INTO ref_months (month_number, code, name_en, name_dv, abbr_en, days_count)
            VALUES (:month_number, :code, :name_en, :name_dv, :abbr_en, :days_count)
            ON CONFLICT(month_number) DO UPDATE SET
                name_en = excluded.name_en,
                name_dv = excluded.name_dv,
                abbr_en = excluded.abbr_en;
            """,
            m,
        )

    # 3. Hijri Months
    for hm in HIJRI_MONTHS_DATA:
        conn.execute(
            """
            INSERT INTO ref_hijri_months (month_number, name_en, name_dv, name_ar)
            VALUES (:month_number, :name_en, :name_dv, :name_ar)
            ON CONFLICT(month_number) DO UPDATE SET
                name_en = excluded.name_en,
                name_dv = excluded.name_dv,
                name_ar = excluded.name_ar;
            """,
            hm,
        )

    # 4. Prayer Times
    for pt in PRAYER_TIMES_DATA:
        conn.execute(
            """
            INSERT INTO ref_prayer_times (id, slug, name_en, name_dv, sort_order)
            VALUES (:id, :slug, :name_en, :name_dv, :sort_order)
            ON CONFLICT(id) DO UPDATE SET
                name_en = excluded.name_en,
                name_dv = excluded.name_dv;
            """,
            pt,
        )

    # 5. Districts
    for dist in DISTRICTS_DATA:
        conn.execute(
            """
            INSERT INTO ref_districts (code, name_en, name_dv, island_name_en)
            VALUES (:code, :name_en, :name_dv, :island_name_en)
            ON CONFLICT(code) DO UPDATE SET
                name_en = excluded.name_en,
                name_dv = excluded.name_dv;
            """,
            dist,
        )


def lookup_month(identifier: str | int) -> Optional[dict[str, Any]]:
    """Lookup month by number (1-12), English name, or Dhivehi Thaana name."""
    s = str(identifier).strip().lower()
    for m in MONTHS_DATA:
        if str(m["month_number"]) == s or m["name_en"].lower() == s or m["abbr_en"].lower() == s or m["name_dv"] == identifier:
            return m
    return None


def lookup_day(identifier: str | int) -> Optional[dict[str, Any]]:
    """Lookup day of the week by number (1-7), English name, or Dhivehi Thaana name."""
    s = str(identifier).strip().lower()
    for d in DAYS_DATA:
        if str(d["day_number"]) == s or d["name_en"].lower() == s or d["code"].lower() == s or d["name_dv"] == identifier:
            return d
    return None


def lookup_prayer_time(identifier: str) -> Optional[dict[str, Any]]:
    """Lookup prayer time by slug, English, or Thaana."""
    s = str(identifier).strip().lower()
    for p in PRAYER_TIMES_DATA:
        if p["slug"] == s or p["name_en"].lower() == s or p["name_dv"] == identifier:
            return p
    return None
