"""Canonical platform identity repository for Telegram and Viber."""
from __future__ import annotations

from typing import Any, Optional

VALID_PROVIDERS = {"telegram", "viber"}


def upsert_platform_identity(
    conn: Any,
    provider: str,
    provider_user_id: str,
    *,
    provider_username: Optional[str] = None,
    display_name: Optional[str] = None,
    is_active: bool = True,
    user_id: Optional[int] = None,
    verified: bool = False,
) -> Optional[dict[str, Any]]:
    """Create/update one stable provider identity without overwriting an existing owner."""
    clean_provider = (provider or "").strip().lower()
    clean_id = str(provider_user_id or "").strip()
    if clean_provider not in VALID_PROVIDERS or not clean_id:
        raise ValueError("A supported provider and provider user ID are required")

    conn.execute(
        """
        INSERT INTO user_identities (
            user_id, provider, provider_user_id, provider_username, display_name,
            is_active, first_seen_at, last_seen_at, verified_at, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                CASE WHEN ? = 1 THEN CURRENT_TIMESTAMP ELSE NULL END,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(provider, provider_user_id) DO UPDATE SET
            provider_username = COALESCE(excluded.provider_username, user_identities.provider_username),
            display_name = COALESCE(excluded.display_name, user_identities.display_name),
            is_active = excluded.is_active,
            last_seen_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP,
            user_id = COALESCE(user_identities.user_id, excluded.user_id),
            verified_at = CASE
                WHEN excluded.verified_at IS NOT NULL THEN excluded.verified_at
                ELSE user_identities.verified_at
            END;
        """,
        (
            user_id, clean_provider, clean_id, provider_username, display_name,
            1 if is_active else 0, 1 if verified else 0,
        ),
    )
    row = conn.execute(
        """
        SELECT id, user_id, provider, provider_user_id, provider_username,
               display_name, is_active, first_seen_at, last_seen_at, verified_at
        FROM user_identities WHERE provider = ? AND provider_user_id = ?;
        """,
        (clean_provider, clean_id),
    ).fetchone()
    return dict(row) if row else None


def get_platform_identity(conn: Any, provider: str, provider_user_id: str) -> Optional[dict[str, Any]]:
    """Return a provider identity by its stable provider-scoped identifier."""
    row = conn.execute(
        """
        SELECT id, user_id, provider, provider_user_id, provider_username,
               display_name, is_active, first_seen_at, last_seen_at, verified_at
        FROM user_identities WHERE provider = ? AND provider_user_id = ?;
        """,
        ((provider or "").strip().lower(), str(provider_user_id or "").strip()),
    ).fetchone()
    return dict(row) if row else None


def link_platform_identity(
    conn: Any,
    provider: str,
    provider_user_id: str,
    user_id: int,
    *,
    provider_username: Optional[str] = None,
    display_name: Optional[str] = None,
) -> tuple[bool, str]:
    """Link a verified provider identity, refusing silent cross-account transfers."""
    identity = get_platform_identity(conn, provider, provider_user_id)
    if identity and identity.get("user_id") not in (None, user_id):
        return False, "This channel is already linked to another Khulaasaa account. Disconnect it there or contact support."

    upsert_platform_identity(
        conn, provider, provider_user_id,
        provider_username=provider_username,
        display_name=display_name,
        is_active=True,
        user_id=user_id,
        verified=True,
    )
    # Re-read after the unique-key upsert to close a concurrent linking race.
    final_identity = get_platform_identity(conn, provider, provider_user_id)
    if not final_identity or int(final_identity.get("user_id") or 0) != int(user_id):
        return False, "This channel was linked to another Khulaasaa account at the same time. Generate a new code and try again."
    return True, "Identity linked successfully."


def mark_platform_identity_inactive(conn: Any, provider: str, provider_user_id: str) -> None:
    """Record provider opt-out/unsubscription without deleting identity history."""
    conn.execute(
        """
        UPDATE user_identities
        SET is_active = 0, last_seen_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
        WHERE provider = ? AND provider_user_id = ?;
        """,
        ((provider or "").strip().lower(), str(provider_user_id or "").strip()),
    )



def get_platform_identity_stats(conn: Any) -> dict[str, int]:
    """Return exact account and channel-identity counts without guessing cross-channel matches."""
    def count(sql: str, params: tuple[Any, ...] = ()) -> int:
        row = conn.execute(sql, params).fetchone()
        if not row:
            return 0
        if hasattr(row, "keys"):
            return int(row[0] if not isinstance(row, dict) else next(iter(row.values())) or 0)
        return int(row[0] or 0)

    web_accounts = count("SELECT COUNT(*) FROM users;")
    telegram = count("SELECT COUNT(*) FROM user_identities WHERE provider = 'telegram';")
    viber = count("SELECT COUNT(*) FROM user_identities WHERE provider = 'viber';")
    unlinked_telegram = count(
        "SELECT COUNT(*) FROM user_identities WHERE provider = 'telegram' AND user_id IS NULL;"
    )
    unlinked_viber = count(
        "SELECT COUNT(*) FROM user_identities WHERE provider = 'viber' AND user_id IS NULL;"
    )
    linked_people = count(
        "SELECT COUNT(DISTINCT user_id) FROM user_identities WHERE user_id IS NOT NULL;"
    )
    multi_channel_people = count(
        """
        SELECT COUNT(*) FROM (
            SELECT user_id FROM user_identities
            WHERE user_id IS NOT NULL
            GROUP BY user_id HAVING COUNT(DISTINCT provider) >= 2
        ) AS multi_channel;
        """
    )
    return {
        "web_accounts": web_accounts,
        "telegram_identities": telegram,
        "viber_identities": viber,
        "linked_people_with_channels": linked_people,
        "people_with_multiple_linked_channels": multi_channel_people,
        "unlinked_telegram_identities": unlinked_telegram,
        "unlinked_viber_identities": unlinked_viber,
    }
