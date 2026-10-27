"""
Sources Repository.
Encapsulates all database operations and resolution for media outlets,
gazette portals, job boards, and classifieds marketplaces.
Adheres to atomic single-source-of-truth principles.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Any, Optional

logger = logging.getLogger(__name__)

DOMAIN_TO_SLUG_MAP = {
    "gazette.gov.mv": "gazette",
    "macl.aero": "macl",
    "hdc.mv": "hdc",
    "mwsc.com.mv": "mwsc",
    "stelco.com.mv": "stelco",
    "sto.mv": "sto",
    "fenaka.mv": "fenaka",
    "jobcenter.mv": "jobcenter",
    "ibay.com.mv": "ibay",
    "boahiyaa.com": "boahiyaa",
    "property.mv": "boahiyaa",
    "t.me/kashunamaadhumv": "kashunamaadhu",
    "kashunamaadhumv": "kashunamaadhu",
    "sun.mv": "sun",
    "dhauru.com": "dhauru",
    "standard.mv": "standard",
    "atolltimes.mv": "atolltimes",
    "haftha.mv": "haftha",
    "adhadhu.com": "adhadhu",
    "psmnews.mv": "psm",
    "mihaaru.com": "mihaaru",
    "avas.mv": "avas",
    "cnm.mv": "cnm",
    "edition.mv": "edition",
    "voice.mv": "voice",
    "miadhu.mv": "miadhu",
    "mira.gov.mv": "mira",
}


def get_source_by_slug(conn: sqlite3.Connection, slug: str) -> Optional[dict[str, Any]]:
    """Fetch source by unique slug."""
    row = conn.execute("SELECT * FROM sources WHERE slug = ? LIMIT 1;", (slug.lower().strip(),)).fetchone()
    return dict(row) if row else None


def get_source_by_id(conn: sqlite3.Connection, source_id: int) -> Optional[dict[str, Any]]:
    """Fetch source by primary key id."""
    row = conn.execute("SELECT * FROM sources WHERE id = ? LIMIT 1;", (source_id,)).fetchone()
    return dict(row) if row else None


def list_sources(conn: sqlite3.Connection, source_type: Optional[str] = None) -> list[dict[str, Any]]:
    """List all registered sources with optional type filtering."""
    if source_type:
        rows = conn.execute(
            "SELECT * FROM sources WHERE source_type = ? AND is_active = 1 ORDER BY name ASC;",
            (source_type,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM sources WHERE is_active = 1 ORDER BY source_type, name ASC;"
        ).fetchall()
    return [dict(r) for r in rows]


def resolve_or_create_source(
    conn: sqlite3.Connection,
    identifier: str,
    name: Optional[str] = None,
    domain: Optional[str] = None,
    source_type: Optional[str] = None,
    logo_url: Optional[str] = None,
) -> int:
    """
    Resolve canonical source ID from slug, domain, or raw source string.
    If the source record does not exist, it will be automatically created.
    """
    if not identifier or not str(identifier).strip():
        identifier = "gazette"

    ident_clean = str(identifier).strip().lower()

    # 1. Map known domains or URLs to slug
    for d_key, s_slug in DOMAIN_TO_SLUG_MAP.items():
        if d_key in ident_clean:
            ident_clean = s_slug
            break

    # 2. Strip protocol and query params
    slug = (
        ident_clean.replace("https://", "")
        .replace("http://", "")
        .replace("www.", "")
        .split("/")[0]
        .split("?")[0]
        .replace(".gov.mv", "")
        .replace(".com.mv", "")
        .replace(".mv", "")
        .replace(".com", "")
        .replace(".aero", "")
        .replace(" ", "-")
    )
    if not slug:
        slug = "gazette"

    # 3. Check existing by slug or domain
    row = conn.execute(
        "SELECT id FROM sources WHERE slug = ? OR domain = ? OR LOWER(name) = ? LIMIT 1;",
        (slug, ident_clean, ident_clean),
    ).fetchone()
    if row:
        return row[0] if isinstance(row, tuple) else row["id"]

    # 4. Create new canonical source record
    clean_name = name or slug.replace("-", " ").title()
    clean_type = source_type or "press"
    clean_logo = logo_url or f"/static/logos/{slug}.png"

    try:
        cur = conn.execute(
            """
            INSERT INTO sources (slug, name, domain, source_type, logo_url, is_active)
            VALUES (?, ?, ?, ?, ?, 1);
            """,
            (slug, clean_name, domain or ident_clean, clean_type, clean_logo),
        )
        last_id = getattr(cur, "lastrowid", None)
        if last_id:
            return last_id
    except Exception:
        if hasattr(conn, "rollback"):
            try:
                conn.rollback()
            except Exception:
                pass

    r2 = conn.execute("SELECT id FROM sources WHERE slug = ? LIMIT 1;", (slug,)).fetchone()
    if r2:
        return r2[0] if isinstance(r2, tuple) else r2["id"]

    r_fallback = conn.execute("SELECT id FROM sources ORDER BY id ASC LIMIT 1;").fetchone()
    if r_fallback:
        return r_fallback[0] if isinstance(r_fallback, tuple) else r_fallback["id"]
    return 1
