"""
Source Synchronization Observability Repository.
Tracks per-source health, fetch/persist latencies, HTTP statuses, and record counts.
Supports both SQLite and PostgreSQL without external ORMs.
"""
from __future__ import annotations

import datetime
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

CREATE_SYNC_STATUS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS source_sync_status (
    source_id TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'healthy',
    last_attempt_at TIMESTAMP,
    last_success_fetch_at TIMESTAMP,
    last_success_persist_at TIMESTAMP,
    fetch_duration_ms INTEGER DEFAULT 0,
    persist_duration_ms INTEGER DEFAULT 0,
    http_status INTEGER,
    failure_reason TEXT,
    fetched_count INTEGER DEFAULT 0,
    parsed_count INTEGER DEFAULT 0,
    rejected_count INTEGER DEFAULT 0,
    deduped_count INTEGER DEFAULT 0,
    inserted_count INTEGER DEFAULT 0,
    updated_count INTEGER DEFAULT 0,
    last_error TEXT,
    PRIMARY KEY (source_id, category)
);
"""


def init_sync_status_table(conn: Any) -> None:
    """Ensure source_sync_status table exists in target database."""
    try:
        conn.execute("SAVEPOINT sync_table_init;")
        conn.execute(CREATE_SYNC_STATUS_TABLE_SQL)
        conn.execute("RELEASE SAVEPOINT sync_table_init;")
    except Exception as exc:
        try:
            conn.execute("ROLLBACK TO SAVEPOINT sync_table_init;")
        except Exception:
            pass
        logger.debug("Table init skipped or already exists: %s", exc)


def record_sync_success(
    conn: Any,
    source_id: str,
    category: str,
    fetch_ms: int = 0,
    persist_ms: int = 0,
    fetched: int = 0,
    parsed: int = 0,
    rejected: int = 0,
    deduped: int = 0,
    inserted: int = 0,
    updated: int = 0,
    http_status: int = 200,
) -> None:
    """Record a fully successful fetch and persistence event for a source."""
    init_sync_status_table(conn)
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    status = "healthy" if (parsed > 0 or fetched > 0) else "partial"

    sql = """
    INSERT INTO source_sync_status (
        source_id, category, status, last_attempt_at, last_success_fetch_at,
        last_success_persist_at, fetch_duration_ms, persist_duration_ms,
        http_status, failure_reason, fetched_count, parsed_count,
        rejected_count, deduped_count, inserted_count, updated_count, last_error
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, NULL)
    ON CONFLICT (source_id, category) DO UPDATE SET
        status = excluded.status,
        last_attempt_at = excluded.last_attempt_at,
        last_success_fetch_at = excluded.last_success_fetch_at,
        last_success_persist_at = excluded.last_success_persist_at,
        fetch_duration_ms = excluded.fetch_duration_ms,
        persist_duration_ms = excluded.persist_duration_ms,
        http_status = excluded.http_status,
        failure_reason = NULL,
        fetched_count = excluded.fetched_count,
        parsed_count = excluded.parsed_count,
        rejected_count = excluded.rejected_count,
        deduped_count = excluded.deduped_count,
        inserted_count = excluded.inserted_count,
        updated_count = excluded.updated_count,
        last_error = NULL;
    """
    try:
        conn.execute("SAVEPOINT sync_rec_sp;")
        conn.execute(
            sql,
            (
                source_id, category, status, now_iso, now_iso, now_iso,
                fetch_ms, persist_ms, http_status, fetched, parsed,
                rejected, deduped, inserted, updated,
            ),
        )
        conn.execute("RELEASE SAVEPOINT sync_rec_sp;")
    except Exception as exc:
        try:
            conn.execute("ROLLBACK TO SAVEPOINT sync_rec_sp;")
        except Exception:
            pass
        logger.debug("Failed recording sync success for %s: %s", source_id, exc)


def record_sync_failure(
    conn: Any,
    source_id: str,
    category: str,
    http_status: Optional[int] = None,
    failure_reason: str = "Unknown error",
    is_blocked: bool = False,
    fetch_ms: int = 0,
) -> None:
    """Record an operational failure (HTTP error, parser failure, network block) for a source."""
    init_sync_status_table(conn)
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    status = "blocked" if (is_blocked or http_status == 403) else "failing"

    sql = """
    INSERT INTO source_sync_status (
        source_id, category, status, last_attempt_at,
        fetch_duration_ms, http_status, failure_reason, last_error
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT (source_id, category) DO UPDATE SET
        status = excluded.status,
        last_attempt_at = excluded.last_attempt_at,
        fetch_duration_ms = excluded.fetch_duration_ms,
        http_status = excluded.http_status,
        failure_reason = excluded.failure_reason,
        last_error = excluded.last_error;
    """
    try:
        conn.execute("SAVEPOINT sync_fail_sp;")
        conn.execute(
            sql,
            (
                source_id, category, status, now_iso,
                fetch_ms, http_status, failure_reason, failure_reason,
            ),
        )
        conn.execute("RELEASE SAVEPOINT sync_fail_sp;")
    except Exception as exc:
        try:
            conn.execute("ROLLBACK TO SAVEPOINT sync_fail_sp;")
        except Exception:
            pass
        logger.debug("Failed recording sync failure for %s: %s", source_id, exc)


def get_all_sync_statuses(conn: Any) -> list[dict[str, Any]]:
    """Query current synchronization health for all sources."""
    init_sync_status_table(conn)
    rows = conn.execute("""
        SELECT
            source_id, category, status, last_attempt_at,
            last_success_fetch_at, last_success_persist_at,
            fetch_duration_ms, persist_duration_ms, http_status,
            failure_reason, fetched_count, parsed_count,
            rejected_count, deduped_count, inserted_count, updated_count, last_error
        FROM source_sync_status
        ORDER BY category ASC, source_id ASC;
    """).fetchall()
    return [dict(r) for r in rows]
