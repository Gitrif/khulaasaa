"""
Subscriber Repository for Telegram and Viber alerts.
"""
from __future__ import annotations
import json
import sqlite3
from typing import Any, Optional
import logging

logger = logging.getLogger("khulaasaa.subscribers")

def baseline_mark_existing_alerts_for_subscriber(conn: sqlite3.Connection, chat_id: str) -> None:
    """
    Mark all current articles, bids, and obituaries in the database as already sent
    for a subscriber so they only receive notifications for items that arrive after subscribing.
    """
    chat_str = str(chat_id).strip()
    from data.database import log_db_error
    try:
        conn.execute('SAVEPOINT baseline_mark_sp;')
        conn.execute(
            """
            INSERT OR IGNORE INTO sent_alerts (notice_id, chat_id)
            SELECT 'news-' || id, ? FROM articles;
            """,
            (chat_str,),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO sent_alerts (notice_id, chat_id)
            SELECT notice_id, ? FROM bids WHERE notice_id IS NOT NULL;
            """,
            (chat_str,),
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO sent_alerts (notice_id, chat_id)
            SELECT 'janaza-' || slug, ? FROM obituaries WHERE slug IS NOT NULL;
            """,
            (chat_str,),
        )
        conn.execute('RELEASE SAVEPOINT baseline_mark_sp;')
    except Exception as exc:
        try:
            conn.execute('ROLLBACK TO SAVEPOINT baseline_mark_sp;')
        except Exception:
            pass
        log_db_error(logger, 'baseline_mark_alerts', 'data.repos.subscribers', exc)


def register_or_update_telegram_subscriber(
    conn: sqlite3.Connection,
    chat_id: str,
    name: Optional[str] = None,
    disciplines: Optional[list[str]] = None,
    keywords: Optional[list[str]] = None,
    is_paid: Optional[int] = None,
    is_active: int = 1,
    baseline_existing: bool = True,
    reset_start_time: bool = False,
) -> int:
    """Register or update a Telegram subscriber's alert preferences."""
    disc_json = json.dumps(disciplines or [])
    kw_json = json.dumps(keywords or [])
    paid_val = is_paid if is_paid is not None else 0
    if reset_start_time:
        cursor = conn.execute(
            """
            INSERT INTO telegram_subscribers (chat_id, name, disciplines, keywords, is_paid, is_active, subscribed_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(chat_id) DO UPDATE SET
                name = COALESCE(excluded.name, telegram_subscribers.name),
                disciplines = excluded.disciplines,
                keywords = excluded.keywords,
                is_paid = COALESCE(?, telegram_subscribers.is_paid),
                is_active = excluded.is_active,
                subscribed_at = CURRENT_TIMESTAMP,
                created_at = CURRENT_TIMESTAMP
            RETURNING id;
            """,
            (str(chat_id).strip(), name, disc_json, kw_json, paid_val, is_active, is_paid),
        )
    else:
        cursor = conn.execute(
            """
            INSERT INTO telegram_subscribers (chat_id, name, disciplines, keywords, is_paid, is_active, subscribed_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(chat_id) DO UPDATE SET
                name = COALESCE(excluded.name, telegram_subscribers.name),
                disciplines = excluded.disciplines,
                keywords = excluded.keywords,
                is_paid = COALESCE(?, telegram_subscribers.is_paid),
                is_active = excluded.is_active,
                subscribed_at = CURRENT_TIMESTAMP
            RETURNING id;
            """,
            (str(chat_id).strip(), name, disc_json, kw_json, paid_val, is_active, is_paid),
        )
    row = cursor.fetchone()
    sub_id = row[0] if row else 0

    if baseline_existing:
        baseline_mark_existing_alerts_for_subscriber(conn, chat_id)

    return sub_id


def is_subscriber_paid(conn: sqlite3.Connection, chat_id: str) -> bool:
    """
    Check if a Telegram subscriber is on the Pro / Paid tier (MVR 50/month).
    Pro subscribers receive customized alerts filtered by disciplines and keywords.
    Free subscribers receive the normal broadcast feed.
    """
    cid = str(chat_id).strip()
    # 1. Check if an associated registered user account is paid
    user_row = conn.execute("SELECT is_paid FROM users WHERE telegram_chat_id = ? LIMIT 1;", (cid,)).fetchone()
    if user_row and user_row["is_paid"]:
        return True

    # 2. Check subscriber row
    sub_row = conn.execute("SELECT is_paid FROM telegram_subscribers WHERE chat_id = ? LIMIT 1;", (cid,)).fetchone()
    if sub_row:
        try:
            return bool(sub_row["is_paid"])
        except (KeyError, IndexError):
            pass
    return False


def update_telegram_subscriber_plan(conn: sqlite3.Connection, chat_id: str, is_paid: int) -> bool:
    """Set the plan status of a Telegram subscriber (0 for Free, 1 for Pro MVR 50/mo)."""
    conn.execute("UPDATE telegram_subscribers SET is_paid = ? WHERE chat_id = ?;", (is_paid, str(chat_id).strip()))
    return True



def get_telegram_subscribers(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """List all registered Telegram subscribers."""
    rows = conn.execute("SELECT * FROM telegram_subscribers ORDER BY created_at DESC;").fetchall()
    results = []
    for r in rows:
        d = dict(r)
        try:
            d["disciplines"] = json.loads(d["disciplines"]) if d.get("disciplines") else []
        except Exception:
            d["disciplines"] = []
        try:
            d["keywords"] = json.loads(d["keywords"]) if d.get("keywords") else []
        except Exception:
            d["keywords"] = []
        results.append(d)
    return results


def get_telegram_subscriber(conn: sqlite3.Connection, chat_id: str) -> Optional[dict[str, Any]]:
    """Get subscriber details by Telegram chat_id."""
    row = conn.execute("SELECT * FROM telegram_subscribers WHERE chat_id = ? LIMIT 1;", (str(chat_id).strip(),)).fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        d["disciplines"] = json.loads(d["disciplines"]) if d.get("disciplines") else []
    except Exception:
        d["disciplines"] = []
    try:
        d["keywords"] = json.loads(d["keywords"]) if d.get("keywords") else []
    except Exception:
        d["keywords"] = []
    return d


# ---------------------------------------------------------------------
# Viber Subscriber Operations
# ---------------------------------------------------------------------

def register_or_update_viber_subscriber(
    conn: sqlite3.Connection,
    viber_user_id: str,
    name: Optional[str] = None,
    avatar: Optional[str] = None,
    categories: Optional[list[str]] = None,
    is_paid: Optional[int] = None,
    is_active: int = 1,
) -> int:
    """Register or update a Viber subscriber."""
    cat_json = json.dumps(categories or ["all"])
    paid_val = is_paid if is_paid is not None else 0
    cursor = conn.execute(
        """
        INSERT INTO viber_subscribers (viber_user_id, name, avatar, subscribed_categories, is_paid, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(viber_user_id) DO UPDATE SET
            name = COALESCE(excluded.name, viber_subscribers.name),
            avatar = COALESCE(excluded.avatar, viber_subscribers.avatar),
            subscribed_categories = excluded.subscribed_categories,
            is_paid = COALESCE(?, viber_subscribers.is_paid),
            is_active = excluded.is_active
        RETURNING id;
        """,
        (str(viber_user_id).strip(), name, avatar, cat_json, paid_val, is_active, is_paid),
    )
    row = cursor.fetchone()
    return row[0] if row else 0


def is_viber_subscriber_paid(conn: sqlite3.Connection, viber_user_id: str) -> bool:
    """Check if a Viber subscriber is on the Pro / Paid tier (MVR 50/month)."""
    vid = str(viber_user_id).strip()
    user_row = conn.execute("SELECT is_paid FROM users WHERE viber_user_id = ? LIMIT 1;", (vid,)).fetchone()
    if user_row and user_row["is_paid"]:
        return True
    sub_row = conn.execute("SELECT is_paid FROM viber_subscribers WHERE viber_user_id = ? LIMIT 1;", (vid,)).fetchone()
    if sub_row:
        try:
            return bool(sub_row["is_paid"])
        except (KeyError, IndexError):
            pass
    return False


def update_viber_subscriber_plan(conn: sqlite3.Connection, viber_user_id: str, is_paid: int) -> bool:
    """Set the plan status of a Viber subscriber (0 for Free, 1 for Pro MVR 50/mo)."""
    conn.execute("UPDATE viber_subscribers SET is_paid = ? WHERE viber_user_id = ?;", (is_paid, str(viber_user_id).strip()))
    return True



def get_viber_subscribers(conn: sqlite3.Connection, active_only: bool = True) -> list[dict[str, Any]]:
    """List registered Viber subscribers."""
    sql = "SELECT * FROM viber_subscribers WHERE is_active = 1 ORDER BY created_at DESC;" if active_only else "SELECT * FROM viber_subscribers ORDER BY created_at DESC;"
    rows = conn.execute(sql).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        try:
            d["subscribed_categories"] = json.loads(d["subscribed_categories"]) if d.get("subscribed_categories") else ["all"]
        except Exception:
            d["subscribed_categories"] = ["all"]
        results.append(d)
    return results


def get_viber_subscriber(conn: sqlite3.Connection, viber_user_id: str) -> Optional[dict[str, Any]]:
    """Retrieve a single Viber subscriber by their Viber User ID."""
    row = conn.execute(
        "SELECT * FROM viber_subscribers WHERE viber_user_id = ?;",
        (str(viber_user_id).strip(),),
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    try:
        d["subscribed_categories"] = json.loads(d["subscribed_categories"]) if d.get("subscribed_categories") else ["all"]
    except Exception:
        d["subscribed_categories"] = ["all"]
    return d


def unsubscribe_viber_subscriber(conn: sqlite3.Connection, viber_user_id: str) -> bool:
    """Mark a Viber user as unsubscribed."""
    cursor = conn.execute("UPDATE viber_subscribers SET is_active = 0 WHERE viber_user_id = ?;", (str(viber_user_id).strip(),))
    return cursor.rowcount > 0


# ---------------------------------------------------------------------
# Notice Milestone & Venue Extraction
# ---------------------------------------------------------------------

