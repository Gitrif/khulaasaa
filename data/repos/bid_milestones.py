"""
Tender Retention & Milestones Repository Facade.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import sqlite3

from scrapers.tenders.milestones import extract_milestones_and_venues


def purge_expired_bids(conn: sqlite3.Connection, retention_days: int = 30) -> int:
    """
    Purge bids that expired more than `retention_days` (default 30 days) ago.
    Also removes legacy placeholder notices (notice-%).
    Explicitly preserves news articles and tracked story timelines.
    """
    cutoff_dt = datetime.now() - timedelta(days=retention_days)
    cutoff_date = cutoff_dt.strftime("%Y-%m-%d")

    try:
        cursor = conn.execute(
            """
            DELETE FROM bids
            WHERE (submission_date IS NOT NULL AND submission_date < ?)
               OR (submission_date IS NULL AND published_date IS NOT NULL AND published_date < ?)
               OR notice_id LIKE ?;
            """,
            (cutoff_date, cutoff_date, "notice-%"),
        )
        return cursor.rowcount or 0
    except Exception:
        return 0


__all__ = ["extract_milestones_and_venues", "purge_expired_bids"]
