"""
User Content Follows Repository for Khulaasaa.
Handles canonical following for Stories, Topics, Sections, and Sources.
"""
from __future__ import annotations

import sqlite3
from typing import Any, Optional

from data.sources_data import SOURCES, TIMELINE_TAGS, TOPICS
from services.clustering import KNOWN_STORY_CLUSTERS

VALID_FOLLOW_TYPES = {"story", "topic", "section", "source"}

VALID_SECTIONS = {
    "major": "Major News",
    "general": "General News",
    "tenders": "Tenders & Procurement",
    "jobs": "Job Opportunities",
    "rentals": "Property & Rentals",
    "breaking": "Breaking Alerts",
}


def validate_and_resolve_target(
    conn: Optional[sqlite3.Connection],
    target_type: str,
    target_id: str,
    target_title: Optional[str] = None,
) -> tuple[str, str, str]:
    """
    Validate target_type and target_id, and resolve a canonical title.
    Returns (clean_type, clean_id, canonical_title).
    Raises ValueError on invalid target.
    """
    clean_type = (target_type or "").strip().lower()
    clean_id = (target_id or "").strip().lower()

    if clean_type not in VALID_FOLLOW_TYPES:
        raise ValueError(f"Invalid target_type '{target_type}'. Must be one of: {', '.join(sorted(VALID_FOLLOW_TYPES))}")

    if not clean_id:
        raise ValueError("target_id cannot be empty")

    clean_title = (target_title or "").strip()

    if clean_type == "section":
        if clean_id not in VALID_SECTIONS:
            valid_secs = ", ".join(sorted(VALID_SECTIONS.keys()))
            raise ValueError(f"Invalid section '{clean_id}'. Valid sections: {valid_secs}")
        if not clean_title:
            clean_title = VALID_SECTIONS[clean_id]

    elif clean_type == "topic":
        if clean_id in TOPICS:
            if not clean_title:
                clean_title = TOPICS[clean_id].get("label", clean_id.capitalize())
        else:
            known_topics = {"policy", "economy", "infrastructure", "weather", "crime", "health", "tourism", "inflation", "sports", "education"}
            if clean_id not in known_topics and not clean_title:
                raise ValueError(f"Unknown topic '{clean_id}' and no display title provided.")
            if not clean_title:
                clean_title = clean_id.capitalize()

    elif clean_type == "source":
        if clean_id in SOURCES:
            if not clean_title:
                clean_title = SOURCES[clean_id].get("name", clean_id.upper())
        elif conn is not None:
            row = conn.execute("SELECT name FROM sources WHERE slug = ?;", (clean_id,)).fetchone()
            if row:
                if not clean_title:
                    clean_title = row[0]
            else:
                if not clean_title:
                    raise ValueError(f"Unknown publisher source '{clean_id}'")
        else:
            if not clean_title:
                clean_title = clean_id.upper()

    elif clean_type == "story":
        # Check known clusters or timeline tags
        matched_cluster = next((c for c in KNOWN_STORY_CLUSTERS if c.get("story_id") == clean_id or c.get("id") == clean_id), None)
        if matched_cluster:
            # Normalize cluster id to stable story_id so follows survive multi-outlet re-clustering
            if matched_cluster.get("story_id"):
                clean_id = matched_cluster["story_id"]
            if not clean_title:
                clean_title = matched_cluster.get("headline", clean_id)
        elif clean_id in TIMELINE_TAGS and not clean_title:
            clean_title = TIMELINE_TAGS[clean_id].get("label", clean_id)
        elif not clean_title:
            clean_title = clean_id.replace("-", " ").title()

    return clean_type, clean_id, clean_title


def add_follow(
    conn: sqlite3.Connection,
    user_id: int,
    target_type: str,
    target_id: str,
    target_title: Optional[str] = None,
) -> dict[str, Any]:
    """
    Idempotently add a followed target for a user.
    """
    clean_type, clean_id, title = validate_and_resolve_target(conn, target_type, target_id, target_title)

    cursor = conn.execute(
        """
        INSERT INTO user_follows (user_id, target_type, target_id, target_title)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, target_type, target_id) DO UPDATE SET
            target_title = excluded.target_title
        RETURNING id, user_id, target_type, target_id, target_title, created_at;
        """,
        (user_id, clean_type, clean_id, title),
    )
    row = cursor.fetchone()
    if row:
        d = dict(row) if hasattr(row, "keys") else {
            "id": row[0],
            "user_id": row[1],
            "target_type": row[2],
            "target_id": row[3],
            "target_title": row[4],
            "created_at": row[5],
        }
        return d

    # Fallback lookup if RETURNING is not supported
    row = conn.execute(
        "SELECT id, user_id, target_type, target_id, target_title, created_at FROM user_follows WHERE user_id = ? AND target_type = ? AND target_id = ?;",
        (user_id, clean_type, clean_id),
    ).fetchone()
    return dict(row) if row else {}


def remove_follow(
    conn: sqlite3.Connection,
    user_id: int,
    target_type: str,
    target_id: str,
) -> bool:
    """
    Remove a followed target for a user. Returns True if deleted, False otherwise.
    """
    clean_type = (target_type or "").strip().lower()
    clean_id = (target_id or "").strip().lower()

    cursor = conn.execute(
        "DELETE FROM user_follows WHERE user_id = ? AND target_type = ? AND target_id = ?;",
        (user_id, clean_type, clean_id),
    )
    return cursor.rowcount > 0


def list_user_follows(
    conn: sqlite3.Connection,
    user_id: int,
    target_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    """
    List all followed targets for a user, optionally filtered by target_type.
    """
    if target_type:
        clean_type = target_type.strip().lower()
        rows = conn.execute(
            """
            SELECT id, user_id, target_type, target_id, target_title, created_at
            FROM user_follows
            WHERE user_id = ? AND target_type = ?
            ORDER BY created_at DESC;
            """,
            (user_id, clean_type),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, user_id, target_type, target_id, target_title, created_at
            FROM user_follows
            WHERE user_id = ?
            ORDER BY target_type ASC, created_at DESC;
            """,
            (user_id,),
        ).fetchall()

    return [dict(r) if hasattr(r, "keys") else {
        "id": r[0],
        "user_id": r[1],
        "target_type": r[2],
        "target_id": r[3],
        "target_title": r[4],
        "created_at": r[5],
    } for r in rows]


def is_following(
    conn: sqlite3.Connection,
    user_id: int,
    target_type: str,
    target_id: str,
) -> bool:
    """
    Check if a user is following a specific target.
    """
    clean_type = (target_type or "").strip().lower()
    clean_id = (target_id or "").strip().lower()

    row = conn.execute(
        "SELECT 1 FROM user_follows WHERE user_id = ? AND target_type = ? AND target_id = ? LIMIT 1;",
        (user_id, clean_type, clean_id),
    ).fetchone()
    return row is not None


def get_followers_for_target(
    conn: sqlite3.Connection,
    target_type: str,
    target_id: str,
) -> list[dict[str, Any]]:
    """
    Retrieve all users following a given target.
    """
    clean_type = (target_type or "").strip().lower()
    clean_id = (target_id or "").strip().lower()

    rows = conn.execute(
        """
        SELECT u.id, u.email, u.full_name, u.telegram_chat_id, u.viber_user_id, u.alerts_enabled, u.is_paid
        FROM user_follows f
        JOIN users u ON f.user_id = u.id
        WHERE f.target_type = ? AND f.target_id = ?;
        """,
        (clean_type, clean_id),
    ).fetchall()

    return [dict(r) if hasattr(r, "keys") else {
        "id": r[0],
        "email": r[1],
        "full_name": r[2],
        "telegram_chat_id": r[3],
        "viber_user_id": r[4],
        "alerts_enabled": bool(r[5]),
        "is_paid": bool(r[6]),
    } for r in rows]


def get_user_follow_counts(
    conn: sqlite3.Connection,
    user_id: int,
) -> dict[str, int]:
    """
    Get counts of follows for a user broken down by type.
    """
    rows = conn.execute(
        """
        SELECT target_type, COUNT(*) as count
        FROM user_follows
        WHERE user_id = ?
        GROUP BY target_type;
        """,
        (user_id,),
    ).fetchall()

    counts = {"total": 0, "story": 0, "topic": 0, "section": 0, "source": 0}
    for r in rows:
        ttype = r["target_type"] if hasattr(r, "keys") else r[0]
        cnt = r["count"] if hasattr(r, "keys") else r[1]
        counts[ttype] = cnt
        counts["total"] += cnt
    return counts
