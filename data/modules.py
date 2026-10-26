"""
Service Modules & Maintenance Kill-Switch Repository for Khulaasaa.
Allows administrators to stop or unpublish any service (news, tenders, jobs, rentals)
on demand, displaying a professional Service Suspended notice to visitors.
Strictly under 500 lines. Zero emojis.
"""
from __future__ import annotations
import sqlite3
from typing import Any, Optional

DEFAULT_MODULES = [
    {
        "module_key": "news",
        "name": "News & Story Clusters",
        "description": "Multi-source news aggregation, verified cluster feeds, and live timeline updates.",
        "is_enabled": 1,
        "suspended_message": "The Khulaasaa News service is temporarily undergoing scheduled updates. Please check back shortly.",
    },
    {
        "module_key": "tenders",
        "name": "Tenders & Gazette Procurement Portal",
        "description": "Official Gazette bid notices, corporate procurement, BOQ preparation, and vendor RFP tools.",
        "is_enabled": 1,
        "suspended_message": "The Gazette & Corporate Tenders portal is temporarily offline for routine database maintenance. Please check back shortly.",
    },
    {
        "module_key": "jobs",
        "name": "Job Center & Career Portal",
        "description": "Verified Maldivian employment listings, HR hiring workspace, candidate CV builder, and job applications.",
        "is_enabled": 1,
        "suspended_message": "The Khulaasaa Job Center & Employment portal is temporarily suspended for system maintenance. Please check back shortly.",
    },
    {
        "module_key": "rentals",
        "name": "Consolidated Residential Rentals",
        "description": "Cross-portal consolidated apartment rentals, tenancy agreements, and Hooks85 residential lease suite.",
        "is_enabled": 1,
        "suspended_message": "The Khulaasaa Consolidated Residential Rentals service is temporarily offline for scheduled system updates. Please check back shortly.",
    },
]


_MODULES_INIT_DONE = False


def init_modules_table(conn: Any) -> None:
    """Create service_modules table if it does not exist and populate defaults."""
    global _MODULES_INIT_DONE
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS service_modules (
                module_key TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                is_enabled INTEGER NOT NULL DEFAULT 1,
                suspended_message TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        if hasattr(conn, "commit"):
            conn.commit()
        for mod in DEFAULT_MODULES:
            conn.execute(
                """
                INSERT OR IGNORE INTO service_modules (module_key, name, description, is_enabled, suspended_message)
                VALUES (?, ?, ?, ?, ?)
                """,
                (mod["module_key"], mod["name"], mod["description"], mod["is_enabled"], mod["suspended_message"]),
            )
        if hasattr(conn, "commit"):
            conn.commit()
        _MODULES_INIT_DONE = True
    except Exception:
        if hasattr(conn, "rollback"):
            conn.rollback()


def list_service_modules(conn: Any) -> list[dict[str, Any]]:
    """List all modules with their current operational statuses."""
    if not _MODULES_INIT_DONE:
        init_modules_table(conn)
    try:
        cursor = conn.execute("SELECT module_key, name, description, is_enabled, suspended_message, updated_at FROM service_modules ORDER BY rowid ASC")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    except Exception:
        if hasattr(conn, "rollback"):
            conn.rollback()
        return [dict(m) for m in DEFAULT_MODULES]


def get_service_module(conn: Any, module_key: str) -> Optional[dict[str, Any]]:
    """Retrieve state for a specific service module."""
    if not _MODULES_INIT_DONE:
        init_modules_table(conn)
    try:
        cursor = conn.execute("SELECT module_key, name, description, is_enabled, suspended_message, updated_at FROM service_modules WHERE module_key = ?", (module_key,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception:
        if hasattr(conn, "rollback"):
            conn.rollback()
        for m in DEFAULT_MODULES:
            if m["module_key"] == module_key:
                return dict(m)
        return None


def is_service_module_enabled(conn: Any, module_key: str) -> bool:
    """Return True if the module is operational (enabled); False if suspended."""
    if not _MODULES_INIT_DONE:
        init_modules_table(conn)
    try:
        cursor = conn.execute("SELECT is_enabled FROM service_modules WHERE module_key = ? LIMIT 1;", (module_key,))
        row = cursor.fetchone()
        if row is not None:
            return bool(row[0])
    except Exception:
        if hasattr(conn, "rollback"):
            conn.rollback()
    mod = get_service_module(conn, module_key)
    if not mod:
        return True
    return bool(mod.get("is_enabled", 1))


def update_service_module_status(conn: sqlite3.Connection, module_key: str, is_enabled: bool, suspended_message: Optional[str] = None) -> bool:
    """Update enabled state and optional maintenance message for a service module."""
    if not _MODULES_INIT_DONE:
        init_modules_table(conn)
    if suspended_message and suspended_message.strip():
        conn.execute(
            """
            UPDATE service_modules
            SET is_enabled = ?, suspended_message = ?, updated_at = CURRENT_TIMESTAMP
            WHERE module_key = ?
            """,
            (1 if is_enabled else 0, suspended_message.strip(), module_key),
        )
    else:
        conn.execute(
            """
            UPDATE service_modules
            SET is_enabled = ?, updated_at = CURRENT_TIMESTAMP
            WHERE module_key = ?
            """,
            (1 if is_enabled else 0, module_key),
        )
    return True
