"""
User Feedback, Suggestions, and Issue Reporting Repository.
Stores alpha/beta feedback, bug reports, and user suggestions.
"""
from __future__ import annotations

import logging
import sqlite3
from typing import Any, Optional

logger = logging.getLogger("khulaasaa.feedback")


def init_feedback_schema(conn: sqlite3.Connection) -> None:
    """Create user_feedback table if it does not exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feedback_type TEXT NOT NULL,
            message TEXT NOT NULL,
            contact_info TEXT,
            page_url TEXT,
            user_agent TEXT,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_feedback_created ON user_feedback(created_at DESC);"
    )


def save_user_feedback(conn: sqlite3.Connection, data: dict[str, Any]) -> int:
    """Insert a new user feedback or bug report into the database."""
    init_feedback_schema(conn)
    cur = conn.execute(
        """
        INSERT INTO user_feedback (feedback_type, message, contact_info, page_url, user_agent, status)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (
            data.get("feedback_type", "general"),
            data.get("message", "").strip(),
            data.get("contact_info", "").strip() or "hooks.connect@gmail.com",
            data.get("page_url", "").strip(),
            data.get("user_agent", "").strip(),
            data.get("status", "new"),
        ),
    )
    return cur.lastrowid or 0


def list_user_feedback(conn: sqlite3.Connection, limit: int = 50) -> list[dict[str, Any]]:
    """List recent user feedback entries."""
    init_feedback_schema(conn)
    cur = conn.execute(
        "SELECT * FROM user_feedback ORDER BY created_at DESC LIMIT ?;",
        (limit,),
    )
    return [dict(r) for r in cur.fetchall()]
