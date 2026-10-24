"""
Sponsored Ads and hooks85 Subscriptions Repository.
"""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

def get_active_sponsored_ad(conn: sqlite3.Connection, target_category: str = "all") -> Optional[dict[str, Any]]:
    """Retrieve an active sponsored ad matching target_category ('all', 'bids', 'news') with quota & time expiration balancing."""
    row = conn.execute(
        """
        SELECT * FROM sponsored_ads
        WHERE is_active = 1 
          AND (target_category = 'all' OR target_category = ?)
          AND (max_impressions IS NULL OR impressions < max_impressions)
          AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
        ORDER BY impressions ASC, RANDOM()
        LIMIT 1;
        """,
        (target_category,),
    ).fetchone()
    return dict(row) if row else None


def record_ad_impression(conn: sqlite3.Connection, ad_id: int) -> None:
    """Increment the delivered impressions counter for an ad."""
    conn.execute(
        "UPDATE sponsored_ads SET impressions = impressions + 1 WHERE id = ?;",
        (ad_id,),
    )


def list_sponsored_ads(conn: sqlite3.Connection, active_only: bool = False) -> list[dict[str, Any]]:
    """List all configured sponsor campaigns and calculate quota & duration status."""
    from datetime import datetime

    rows = conn.execute("SELECT * FROM sponsored_ads ORDER BY created_at DESC;").fetchall()
    results = []

    for r in rows:
        d = dict(r)
        impressions = d.get("impressions") or 0
        max_imp = d.get("max_impressions")
        expires_at_str = d.get("expires_at")

        # Quota evaluation
        is_quota_filled = (max_imp is not None and impressions >= max_imp)
        quota_percent = min(100, int((impressions / max_imp) * 100)) if (max_imp and max_imp > 0) else None

        # Expiry evaluation
        is_expired = False
        days_remaining = None
        if expires_at_str:
            try:
                clean_ts = str(expires_at_str).replace("T", " ").split(".")[0]
                exp_dt = datetime.strptime(clean_ts, "%Y-%m-%d %H:%M:%S")
                diff = exp_dt - datetime.now()
                if diff.total_seconds() <= 0:
                    is_expired = True
                    days_remaining = 0
                else:
                    days_remaining = max(1, diff.days + (1 if diff.seconds > 0 else 0))
            except Exception:
                pass

        is_active_flag = bool(d.get("is_active", 1))
        is_serving = is_active_flag and (not is_quota_filled) and (not is_expired)

        if not is_active_flag:
            status_label = "Paused"
            status_color = "slate"
        elif is_quota_filled:
            status_label = "Quota Reached"
            status_color = "amber"
        elif is_expired:
            status_label = "Expired"
            status_color = "rose"
        else:
            status_label = "Active"
            status_color = "emerald"

        d["is_quota_filled"] = is_quota_filled
        d["quota_percent"] = quota_percent
        d["is_expired"] = is_expired
        d["days_remaining"] = days_remaining
        d["is_serving"] = is_serving
        d["status_label"] = status_label
        d["status_color"] = status_color

        if active_only and not is_serving:
            continue

        results.append(d)

    return results


def upsert_sponsored_ad(conn: sqlite3.Connection, ad: dict[str, Any]) -> int:
    """Insert or update a sponsored ad campaign with quota and time limits."""
    cursor = conn.execute(
        """
        INSERT INTO sponsored_ads (
            campaign_name, sponsor_name, text_html, target_category, link_url, is_active,
            max_impressions, expires_at, pricing_tier
        )
        VALUES (
            :campaign_name, :sponsor_name, :text_html, :target_category, :link_url, :is_active,
            :max_impressions, :expires_at, :pricing_tier
        )
        ON CONFLICT(campaign_name) DO UPDATE SET
            sponsor_name = excluded.sponsor_name,
            text_html = excluded.text_html,
            target_category = excluded.target_category,
            link_url = excluded.link_url,
            is_active = excluded.is_active,
            max_impressions = excluded.max_impressions,
            expires_at = excluded.expires_at,
            pricing_tier = excluded.pricing_tier
        RETURNING id;
        """,
        {
            "campaign_name": ad["campaign_name"],
            "sponsor_name": ad["sponsor_name"],
            "text_html": ad["text_html"],
            "target_category": ad.get("target_category", "all"),
            "link_url": ad.get("link_url"),
            "is_active": ad.get("is_active", 1),
            "max_impressions": ad.get("max_impressions"),
            "expires_at": ad.get("expires_at"),
            "pricing_tier": ad.get("pricing_tier", "custom"),
        },
    )
    row = cursor.fetchone()
    conn.commit()
    return row[0] if row else 0


def extend_sponsored_ad(
    conn: sqlite3.Connection,
    ad_id: int,
    add_impressions: Optional[int] = None,
    add_days: Optional[int] = None,
    reset_impressions: bool = False,
) -> bool:
    """Top-up quota or extend duration for an ad after advertiser renewal."""
    from datetime import datetime, timedelta

    row = conn.execute("SELECT * FROM sponsored_ads WHERE id = ?;", (ad_id,)).fetchone()
    if not row:
        return False

    ad = dict(row)
    curr_max = ad.get("max_impressions")
    curr_exp = ad.get("expires_at")
    new_max = curr_max
    new_exp = curr_exp

    if add_impressions and add_impressions > 0:
        base = max(ad.get("impressions", 0), curr_max or 0)
        new_max = base + add_impressions

    if add_days and add_days > 0:
        now = datetime.now()
        base_date = now
        if curr_exp:
            try:
                clean_exp = str(curr_exp).replace("T", " ").split(".")[0]
                parsed = datetime.strptime(clean_exp, "%Y-%m-%d %H:%M:%S")
                if parsed > now:
                    base_date = parsed
            except Exception:
                base_date = now
        new_exp = (base_date + timedelta(days=add_days)).strftime("%Y-%m-%d %H:%M:%S")

    reset_clause = "impressions = 0, " if reset_impressions else ""

    conn.execute(
        f"""
        UPDATE sponsored_ads 
        SET {reset_clause}max_impressions = ?, expires_at = ?, is_active = 1
        WHERE id = ?;
        """,
        (new_max, new_exp, ad_id),
    )
    conn.commit()
    return True


def get_sponsored_ad(conn: sqlite3.Connection, ad_id: int) -> Optional[dict[str, Any]]:
    """Retrieve a single ad by ID."""
    row = conn.execute("SELECT * FROM sponsored_ads WHERE id = ?;", (ad_id,)).fetchone()
    return dict(row) if row else None


def toggle_sponsored_ad(conn: sqlite3.Connection, ad_id: int) -> bool:
    """Toggle the active status of a sponsored campaign."""
    cursor = conn.execute(
        "UPDATE sponsored_ads SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?;",
        (ad_id,),
    )
    return cursor.rowcount > 0


def delete_sponsored_ad(conn: sqlite3.Connection, ad_id: int) -> bool:
    """Permanently delete an ad campaign."""
    cursor = conn.execute("DELETE FROM sponsored_ads WHERE id = ?;", (ad_id,))
    return cursor.rowcount > 0


# ---------------------------------------------------------------------
# hooks85 POS & ERP Subscription Leads
# ---------------------------------------------------------------------

def save_hooks85_subscription(conn: sqlite3.Connection, sub_data: dict[str, Any]) -> int:
    """Save an incoming subscription lead for hooks85 POS / ERP."""
    cursor = conn.execute(
        """
        INSERT INTO hooks85_subscriptions (
            company_name, contact_name, phone, email, island_atoll, plan_tier, interested_modules, notice_id, notes
        ) VALUES (
            :company_name, :contact_name, :phone, :email, :island_atoll, :plan_tier, :interested_modules, :notice_id, :notes
        )
        RETURNING id;
        """,
        {
            "company_name": (sub_data.get("company_name") or "").strip(),
            "contact_name": (sub_data.get("contact_name") or "").strip(),
            "phone": (sub_data.get("phone") or "").strip(),
            "email": (sub_data.get("email") or "").strip() or None,
            "island_atoll": (sub_data.get("island_atoll") or "").strip() or None,
            "plan_tier": (sub_data.get("plan_tier") or "pos_starter").strip(),
            "interested_modules": (sub_data.get("interested_modules") or "").strip() or None,
            "notice_id": str(sub_data.get("notice_id")) if sub_data.get("notice_id") else None,
            "notes": (sub_data.get("notes") or "").strip() or None,
        },
    )
    row = cursor.fetchone()
    conn.commit()
    return row[0] if row else cursor.lastrowid


def list_hooks85_subscriptions(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """List all hooks85 subscription inquiries."""
    rows = conn.execute("SELECT * FROM hooks85_subscriptions ORDER BY created_at DESC;").fetchall()
    return [dict(r) for r in rows]



# ---------------------------------------------------------------------
# Obituary & Funeral Announcement (Janaza) Functions
# ---------------------------------------------------------------------

