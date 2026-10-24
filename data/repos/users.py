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


def authenticate_user(conn: sqlite3.Connection, email: str, password: str) -> Optional[dict[str, Any]]:
    """Verify email & password. Returns user dict on success, None on failure."""
    clean_email = email.strip().lower()
    row = conn.execute(
        "SELECT id, email, password_hash, full_name, phone, telegram_chat_id, viber_user_id, job_alert_categories, is_paid, created_at FROM users WHERE email = ?;",
        (clean_email,),
    ).fetchone()
    if not row:
        return None
    if not verify_password(password, row["password_hash"]):
        return None
    
    cats = []
    try:
        cats = json.loads(row["job_alert_categories"] or "[]")
    except Exception:
        pass

    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "phone": row["phone"],
        "telegram_chat_id": row["telegram_chat_id"],
        "viber_user_id": row["viber_user_id"],
        "job_alert_categories": cats,
        "is_paid": bool(row["is_paid"]),
        "created_at": row["created_at"],
    }


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> Optional[dict[str, Any]]:
    """Retrieve user by ID."""
    row = conn.execute(
        "SELECT id, email, full_name, phone, telegram_chat_id, viber_user_id, job_alert_categories, is_paid, created_at FROM users WHERE id = ?;",
        (user_id,),
    ).fetchone()
    if not row:
        return None
    cats = []
    try:
        cats = json.loads(row["job_alert_categories"] or "[]")
    except Exception:
        pass
    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "phone": row["phone"],
        "telegram_chat_id": row["telegram_chat_id"],
        "viber_user_id": row["viber_user_id"],
        "job_alert_categories": cats,
        "is_paid": bool(row["is_paid"]),
        "created_at": row["created_at"],
    }


def get_user_by_email(conn: sqlite3.Connection, email: str) -> Optional[dict[str, Any]]:
    """Retrieve user by email."""
    row = conn.execute(
        "SELECT id, email, full_name, phone, telegram_chat_id, viber_user_id, job_alert_categories, is_paid, created_at FROM users WHERE email = ?;",
        (email.strip().lower(),),
    ).fetchone()
    if not row:
        return None
    cats = []
    try:
        cats = json.loads(row["job_alert_categories"] or "[]")
    except Exception:
        pass
    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "phone": row["phone"],
        "telegram_chat_id": row["telegram_chat_id"],
        "viber_user_id": row["viber_user_id"],
        "job_alert_categories": cats,
        "is_paid": bool(row["is_paid"]),
        "created_at": row["created_at"],
    }


def get_user_by_telegram_id(conn: sqlite3.Connection, chat_id: str) -> Optional[dict[str, Any]]:
    """Retrieve user by Telegram chat ID."""
    row = conn.execute(
        "SELECT id, email, full_name, phone, telegram_chat_id, viber_user_id, job_alert_categories, is_paid, created_at FROM users WHERE telegram_chat_id = ?;",
        (str(chat_id).strip(),),
    ).fetchone()
    if not row:
        return None
    cats = []
    try:
        cats = json.loads(row["job_alert_categories"] or "[]")
    except Exception:
        pass
    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "phone": row["phone"],
        "telegram_chat_id": row["telegram_chat_id"],
        "viber_user_id": row["viber_user_id"],
        "job_alert_categories": cats,
        "is_paid": bool(row["is_paid"]),
        "created_at": row["created_at"],
    }


def get_user_by_viber_id(conn: sqlite3.Connection, viber_id: str) -> Optional[dict[str, Any]]:
    """Retrieve user by Viber user ID."""
    row = conn.execute(
        "SELECT id, email, full_name, phone, telegram_chat_id, viber_user_id, job_alert_categories, is_paid, created_at FROM users WHERE viber_user_id = ?;",
        (str(viber_id).strip(),),
    ).fetchone()
    if not row:
        return None
    cats = []
    try:
        cats = json.loads(row["job_alert_categories"] or "[]")
    except Exception:
        pass
    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "phone": row["phone"],
        "telegram_chat_id": row["telegram_chat_id"],
        "viber_user_id": row["viber_user_id"],
        "job_alert_categories": cats,
        "is_paid": bool(row["is_paid"]),
        "created_at": row["created_at"],
    }


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
        SELECT u.id, u.email, u.full_name, u.phone, u.telegram_chat_id, u.viber_user_id, u.job_alert_categories, u.is_paid, u.created_at
        FROM user_sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ? AND (s.expires_at IS NULL OR s.expires_at > CURRENT_TIMESTAMP);
        """,
        (token,),
    ).fetchone()
    if not row:
        return None
    cats = []
    try:
        cats = json.loads(row["job_alert_categories"] or "[]")
    except Exception:
        pass
    return {
        "id": row["id"],
        "email": row["email"],
        "full_name": row["full_name"],
        "phone": row["phone"],
        "telegram_chat_id": row["telegram_chat_id"],
        "viber_user_id": row["viber_user_id"],
        "job_alert_categories": cats,
        "is_paid": bool(row["is_paid"]),
        "created_at": row["created_at"],
    }


def delete_user_session(conn: sqlite3.Connection, token: str) -> bool:
    """Delete a user session on logout."""
    cursor = conn.execute("DELETE FROM user_sessions WHERE token = ?;", (token,))
    return cursor.rowcount > 0


# =====================================================================
# User CV Management
