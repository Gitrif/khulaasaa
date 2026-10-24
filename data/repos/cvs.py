"""
User CVs Repository.
"""
from __future__ import annotations
import json
import sqlite3
from typing import Any, Optional

# =====================================================================

def save_user_cv(
    conn: sqlite3.Connection,
    user_id: int,
    cv_data: dict[str, Any],
    title: str = "Maldivian Curriculum Vitae",
    template: str = "standard",
    photo_data: Optional[str] = None,
) -> int:
    """Save or update user's CV record."""
    data_str = json.dumps(cv_data, ensure_ascii=False)
    # Check if existing CV exists for user
    existing = conn.execute("SELECT id FROM user_cvs WHERE user_id = ?;", (user_id,)).fetchone()
    if existing:
        conn.execute(
            """
            UPDATE user_cvs
            SET title = ?, template = ?, data_json = ?, photo_data = COALESCE(?, photo_data), updated_at = CURRENT_TIMESTAMP
            WHERE id = ?;
            """,
            (title, template, data_str, photo_data, existing["id"]),
        )
        return existing["id"]
    else:
        cursor = conn.execute(
            """
            INSERT INTO user_cvs (user_id, title, template, data_json, photo_data)
            VALUES (?, ?, ?, ?, ?)
            RETURNING id;
            """,
            (user_id, title, template, data_str, photo_data),
        )
        row = cursor.fetchone()
        return row[0] if row else 0


def get_user_cv(conn: sqlite3.Connection, user_id: int) -> Optional[dict[str, Any]]:
    """Retrieve CV for a specific user."""
    row = conn.execute(
        "SELECT id, user_id, title, template, data_json, photo_data, created_at, updated_at FROM user_cvs WHERE user_id = ? ORDER BY updated_at DESC LIMIT 1;",
        (user_id,),
    ).fetchone()
    if not row:
        return None
    try:
        cv_dict = json.loads(row["data_json"])
    except Exception:
        cv_dict = {}
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "title": row["title"],
        "template": row["template"],
        "data": cv_dict,
        "photo_data": row["photo_data"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


# =====================================================================
# Company Profiles (for Bids & Corporate Tender Submissions)
# =====================================================================

