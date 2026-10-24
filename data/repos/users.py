"""
Users, Authentication, and Sessions Repository.
"""
from __future__ import annotations
import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

# =====================================================================
# Users & Authentication
# =====================================================================

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with a unique random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}:{key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against salt:key hash."""
    if not hashed or ":" not in hashed:
        return False
    try:
        salt, key_hex = hashed.split(":", 1)
        calc_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return secrets.compare_digest(calc_key.hex(), key_hex)
    except Exception:
        return False


def create_user(
    conn: sqlite3.Connection,
    email: str,
    password: str,
    full_name: str,
    phone: Optional[str] = None,
    telegram_chat_id: Optional[str] = None,
    job_alert_categories: Optional[list[str]] = None,
    is_paid: int = 0,
    viber_user_id: Optional[str] = None,
) -> int:
    """Create a new registered user. Returns user ID."""
    clean_email = email.strip().lower()
    hashed = hash_password(password)
    cats_json = json.dumps(job_alert_categories or ["all"])
    cursor = conn.execute(
        """
        INSERT INTO users (email, password_hash, full_name, phone, telegram_chat_id, viber_user_id, job_alert_categories, is_paid)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id;
        """,
        (clean_email, hashed, full_name.strip(), phone.strip() if phone else None, telegram_chat_id.strip() if telegram_chat_id else None, viber_user_id.strip() if viber_user_id else None, cats_json, is_paid),
    )
    row = cursor.fetchone()
    return row[0] if row else 0


def _parse_user_row(row: Any) -> Optional[dict[str, Any]]:
    if not row:
        return None
    d = dict(row) if hasattr(row, "keys") else row
    def safe_json(val, default):
        try:
            return json.loads(val) if val else default
        except Exception:
            return default
    return {
        "id": d["id"],
        "email": d["email"],
        "full_name": d["full_name"],
        "phone": d.get("phone"),
        "telegram_chat_id": d.get("telegram_chat_id"),
        "viber_user_id": d.get("viber_user_id"),
        "job_alert_categories": safe_json(d.get("job_alert_categories"), ["all"]),
        "job_alert_sources": safe_json(d.get("job_alert_sources"), ["all"]),
        "tender_alert_disciplines": safe_json(d.get("tender_alert_disciplines"), ["All"]),
        "tender_alert_sources": safe_json(d.get("tender_alert_sources"), ["all"]),
        "alerts_enabled": bool(d.get("alerts_enabled", 1)),
        "is_paid": bool(d.get("is_paid", 0)),
        "created_at": d.get("created_at"),
    }


def authenticate_user(conn: sqlite3.Connection, email: str, password: str) -> Optional[dict[str, Any]]:
    """Verify email & password. Returns user dict on success, None on failure."""
    clean_email = email.strip().lower()
    row = conn.execute(
        """
        SELECT id, email, password_hash, full_name, phone, telegram_chat_id, viber_user_id,
               job_alert_categories, job_alert_sources, tender_alert_disciplines, tender_alert_sources,
               alerts_enabled, is_paid, created_at
        FROM users WHERE email = ?;
        """,
        (clean_email,),
    ).fetchone()
    if not row:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    return _parse_user_row(row)


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> Optional[dict[str, Any]]:
    """Retrieve user by ID."""
    row = conn.execute(
        """
        SELECT id, email, full_name, phone, telegram_chat_id, viber_user_id,
               job_alert_categories, job_alert_sources, tender_alert_disciplines, tender_alert_sources,
               alerts_enabled, is_paid, created_at
        FROM users WHERE id = ?;
        """,
        (user_id,),
    ).fetchone()
    return _parse_user_row(row)


def get_user_by_email(conn: sqlite3.Connection, email: str) -> Optional[dict[str, Any]]:
    """Retrieve user by email."""
    row = conn.execute(
        """
        SELECT id, email, full_name, phone, telegram_chat_id, viber_user_id,
               job_alert_categories, job_alert_sources, tender_alert_disciplines, tender_alert_sources,
               alerts_enabled, is_paid, created_at
        FROM users WHERE email = ?;
        """,
        (email.strip().lower(),),
    ).fetchone()
    return _parse_user_row(row)


def get_user_by_telegram_id(conn: sqlite3.Connection, chat_id: str) -> Optional[dict[str, Any]]:
    """Retrieve user by Telegram chat ID."""
    row = conn.execute(
        """
        SELECT id, email, full_name, phone, telegram_chat_id, viber_user_id,
               job_alert_categories, job_alert_sources, tender_alert_disciplines, tender_alert_sources,
               alerts_enabled, is_paid, created_at
        FROM users WHERE telegram_chat_id = ?;
        """,
        (str(chat_id).strip(),),
    ).fetchone()
    return _parse_user_row(row)


def get_user_by_viber_id(conn: sqlite3.Connection, viber_id: str) -> Optional[dict[str, Any]]:
    """Retrieve user by Viber user ID."""
    row = conn.execute(
        """
        SELECT id, email, full_name, phone, telegram_chat_id, viber_user_id,
               job_alert_categories, job_alert_sources, tender_alert_disciplines, tender_alert_sources,
               alerts_enabled, is_paid, created_at
        FROM users WHERE viber_user_id = ?;
        """,
        (str(viber_id).strip(),),
    ).fetchone()
    return _parse_user_row(row)


def update_user_plan(conn: sqlite3.Connection, user_id: int, is_paid: int) -> bool:
    """Update user's subscription tier (0 = Free, 1 = Pro/Paid)."""
    cursor = conn.execute(
        "UPDATE users SET is_paid = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
        (is_paid, user_id),
    )
    return cursor.rowcount > 0


def update_user_job_alerts(
    conn: sqlite3.Connection,
    user_id: int,
    categories: list[str],
    telegram_chat_id: Optional[str] = None,
    viber_user_id: Optional[str] = None,
) -> bool:
    """Update job alert preferences, telegram chat ID, and viber user ID for a user."""
    cats_json = json.dumps(categories)
    updates = ["job_alert_categories = ?", "updated_at = CURRENT_TIMESTAMP"]
    params: list[Any] = [cats_json]
    if telegram_chat_id is not None:
        updates.append("telegram_chat_id = ?")
        params.append(telegram_chat_id.strip() if telegram_chat_id else None)
    if viber_user_id is not None:
        updates.append("viber_user_id = ?")
        params.append(viber_user_id.strip() if viber_user_id else None)
    params.append(user_id)
    sql = f"UPDATE users SET {', '.join(updates)} WHERE id = ?;"
    cursor = conn.execute(sql, tuple(params))
    return cursor.rowcount > 0


def update_user_alert_settings(
    conn: sqlite3.Connection,
    user_id: int,
    telegram_chat_id: Optional[str] = None,
    viber_user_id: Optional[str] = None,
    tender_alert_disciplines: Optional[list[str]] = None,
    tender_alert_sources: Optional[list[str]] = None,
    job_alert_categories: Optional[list[str]] = None,
    job_alert_sources: Optional[list[str]] = None,
    alerts_enabled: Optional[int] = None,
) -> bool:
    """Update comprehensive alert preferences and sync to bot subscribers tables."""
    updates = ["updated_at = CURRENT_TIMESTAMP"]
    params: list[Any] = []
    if telegram_chat_id is not None:
        updates.append("telegram_chat_id = ?")
        params.append(telegram_chat_id.strip() if telegram_chat_id else None)
    if viber_user_id is not None:
        updates.append("viber_user_id = ?")
        params.append(viber_user_id.strip() if viber_user_id else None)
    if tender_alert_disciplines is not None:
        updates.append("tender_alert_disciplines = ?")
        params.append(json.dumps(tender_alert_disciplines))
    if tender_alert_sources is not None:
        updates.append("tender_alert_sources = ?")
        params.append(json.dumps(tender_alert_sources))
    if job_alert_categories is not None:
        updates.append("job_alert_categories = ?")
        params.append(json.dumps(job_alert_categories))
    if job_alert_sources is not None:
        updates.append("job_alert_sources = ?")
        params.append(json.dumps(job_alert_sources))
    if alerts_enabled is not None:
        updates.append("alerts_enabled = ?")
        params.append(int(bool(alerts_enabled)))
    params.append(user_id)
    sql = f"UPDATE users SET {', '.join(updates)} WHERE id = ?;"
    conn.execute(sql, tuple(params))

    # Synchronize to subscribers tables
    user = get_user_by_id(conn, user_id)
    if not user:
        return True
    active_flag = 1 if user.get("alerts_enabled", True) else 0

    if user.get("telegram_chat_id"):
        from data.repos.subscribers import register_or_update_telegram_subscriber
        tg_disciplines = user.get("tender_alert_disciplines") or ["All"]
        tg_keywords = ["tenders", "jobs"] + (user.get("tender_alert_sources") or []) + (user.get("job_alert_sources") or [])
        register_or_update_telegram_subscriber(
            conn,
            chat_id=str(user["telegram_chat_id"]).strip(),
            name=user.get("full_name"),
            disciplines=tg_disciplines,
            keywords=tg_keywords,
            is_active=active_flag,
            is_paid=1 if user.get("is_paid") else 0,
        )

    if user.get("viber_user_id"):
        from data.repos.subscribers import register_or_update_viber_subscriber
        vb_categories = ["all", "bids", "jobs"] + (user.get("tender_alert_sources") or [])
        register_or_update_viber_subscriber(
            conn,
            viber_user_id=str(user["viber_user_id"]).strip(),
            name=user.get("full_name"),
            categories=vb_categories,
            is_active=active_flag,
            is_paid=1 if user.get("is_paid") else 0,
        )

    return True


# =====================================================================
# User Sessions
# =====================================================================

def create_user_session(conn: sqlite3.Connection, user_id: int, days_valid: int = 30) -> str:
    """Create a new session token for the user."""
    token = secrets.token_urlsafe(32)
    expires = (datetime.now() + timedelta(days=days_valid)).isoformat()
    conn.execute(
        "INSERT INTO user_sessions (token, user_id, expires_at) VALUES (?, ?, ?);",
        (token, user_id, expires),
    )
    return token


def get_user_from_session(conn: sqlite3.Connection, token: str) -> Optional[dict[str, Any]]:
    """Retrieve the user associated with a valid session token."""
    if not token:
        return None
    row = conn.execute(
        """
        SELECT u.id, u.email, u.full_name, u.phone, u.telegram_chat_id, u.viber_user_id,
               u.job_alert_categories, u.job_alert_sources, u.tender_alert_disciplines, u.tender_alert_sources,
               u.alerts_enabled, u.is_paid, u.created_at
        FROM user_sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ? AND (s.expires_at IS NULL OR s.expires_at > CURRENT_TIMESTAMP);
        """,
        (token,),
    ).fetchone()
    return _parse_user_row(row)


def delete_user_session(conn: sqlite3.Connection, token: str) -> bool:
    """Delete a user session on logout."""
    cursor = conn.execute("DELETE FROM user_sessions WHERE token = ?;", (token,))
    return cursor.rowcount > 0


# =====================================================================
# User CV Management
