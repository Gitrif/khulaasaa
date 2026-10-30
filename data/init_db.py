"""
Database initialization and schema migration runner for Khulaasaa.
"""
from __future__ import annotations

import logging
import os
import secrets
import sqlite3
from pathlib import Path
from typing import Optional

from data.schema import SCHEMA_SQL
from data.initial_entities import INITIAL_ENTITIES, INITIAL_SPONSORED_ADS, VERIFIED_HISTORIC_BIDS
from data.taxonomy import extract_atoll_and_island, INITIAL_OBITUARIES, INITIAL_JOBS
from data.connection import get_db
from data.utils import slugify
from data.repos.bid_milestones import purge_expired_bids
from data.repos.obituaries import purge_expired_obituaries
from data.repos.bids import upsert_bid
from data.repos.jobs import upsert_job

logger = logging.getLogger(__name__)


def _backfill_platform_identities(conn) -> None:
    """Backfill the identity registry from existing users and bot subscriber records."""
    from data.repos.identities import upsert_platform_identity

    try:
        rows = conn.execute(
            "SELECT id, full_name, telegram_chat_id, viber_user_id, telegram_verified, viber_verified FROM users;"
        ).fetchall()
        for row in rows:
            item = dict(row)
            if item.get("telegram_chat_id"):
                is_verified = bool(item.get("telegram_verified"))
                upsert_platform_identity(
                    conn, "telegram", item["telegram_chat_id"],
                    display_name=item.get("full_name"),
                    user_id=item["id"] if is_verified else None,
                    verified=is_verified,
                )
                if not is_verified:
                    conn.execute(
                        "UPDATE user_identities SET user_id = NULL, verified_at = NULL WHERE provider = 'telegram' AND provider_user_id = ? AND user_id = ?;",
                        (item["telegram_chat_id"], item["id"]),
                    )
            if item.get("viber_user_id"):
                is_verified = bool(item.get("viber_verified"))
                upsert_platform_identity(
                    conn, "viber", item["viber_user_id"],
                    display_name=item.get("full_name"),
                    user_id=item["id"] if is_verified else None,
                    verified=is_verified,
                )
                if not is_verified:
                    conn.execute(
                        "UPDATE user_identities SET user_id = NULL, verified_at = NULL WHERE provider = 'viber' AND provider_user_id = ? AND user_id = ?;",
                        (item["viber_user_id"], item["id"]),
                    )
    except Exception:
        logger.exception("Could not backfill linked platform identities from users")

    for provider, query, id_field in (
        ("telegram", "SELECT chat_id, name, is_active FROM telegram_subscribers;", "chat_id"),
        ("viber", "SELECT viber_user_id, name, is_active FROM viber_subscribers;", "viber_user_id"),
    ):
        try:
            for row in conn.execute(query).fetchall():
                item = dict(row)
                upsert_platform_identity(
                    conn, provider, item[id_field],
                    display_name=item.get("name"),
                    is_active=bool(item.get("is_active", 1)),
                )
        except Exception:
            logger.exception("Could not backfill %s subscriber identities", provider)

def _rotate_legacy_gateway_passwords(conn) -> None:
    """One-time invalidation of the historical, fixed password used for gateway-only accounts."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS auth_security_migrations (migration_key TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
    )
    marker = conn.execute(
        "SELECT migration_key FROM auth_security_migrations WHERE migration_key = ?;",
        ("rotate_fixed_gateway_password_v1",),
    ).fetchone()
    if marker:
        return

    from data.repos.users import hash_password, verify_password

    rows = conn.execute("SELECT id, password_hash FROM users;").fetchall()
    rotated = 0
    for row in rows:
        item = dict(row)
        if verify_password("sso_managed_by_hooks85", item.get("password_hash") or ""):
            conn.execute(
                "UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (hash_password(secrets.token_urlsafe(32)), item["id"]),
            )
            rotated += 1

    conn.execute(
        "INSERT INTO auth_security_migrations (migration_key) VALUES (?) ON CONFLICT(migration_key) DO NOTHING;",
        ("rotate_fixed_gateway_password_v1",),
    )
    if rotated:
        logger.warning("Rotated %s legacy gateway-managed accounts away from a fixed local password", rotated)


def init_db(db_path: Optional[Path] = None, seed_bids: bool = False) -> None:
    """Initialize SQLite schema and seed canonical entity dictionary."""
    if db_path is None and (os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")):
        schema_path = Path(__file__).resolve().parent.parent / "supabase" / "schema.sql"
        if schema_path.exists():
            try:
                from data.postgres_adapter import get_postgres_db
                with get_postgres_db() as pg_conn:
                    with pg_conn._conn.cursor() as cur:
                        cur.execute(schema_path.read_text(encoding="utf-8"))
                        for col in ["news_alerts", "tender_alerts", "job_alerts", "rental_alerts"]:
                            cur.execute(f"ALTER TABLE user_notification_preferences ADD COLUMN IF NOT EXISTS {col} INTEGER NOT NULL DEFAULT 1;")
                        for col in ["telegram_verified", "viber_verified"]:
                            cur.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} INTEGER DEFAULT 0;")
                        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS account_origin TEXT NOT NULL DEFAULT 'web';")
                        cur.execute("UPDATE users SET account_origin = 'telegram' WHERE account_origin = 'web' AND telegram_chat_id IS NOT NULL AND email LIKE 'telegram_%@khulaasaa.tech';")
                    _rotate_legacy_gateway_passwords(pg_conn)
                    _backfill_platform_identities(pg_conn)
                    pg_conn.commit()
            except Exception as e:
                logger.warning(f"Error applying Postgres schema: {e}")
        try:
            from data.modules import init_modules_table
            from data.postgres_adapter import get_postgres_db
            with get_postgres_db() as pg_conn:
                init_modules_table(pg_conn)
                pg_conn.commit()
        except Exception as e:
            logger.warning(f"Error initializing modules table on Postgres: {e}")

        # Seed initial rental listings, jobs, and obituaries on Postgres if tables are empty
        try:
            from data.postgres_adapter import get_postgres_db
            with get_postgres_db() as pg_conn:
                r_cnt = (pg_conn.execute("SELECT count(*) as cnt FROM rentals;").fetchone() or {}).get("cnt", 0)
                if r_cnt == 0:
                    from data.seed_rentals import seed_initial_rentals
                    seed_initial_rentals(pg_conn)
                j_cnt = (pg_conn.execute("SELECT count(*) as cnt FROM jobs;").fetchone() or {}).get("cnt", 0)
                if j_cnt == 0:
                    for j in INITIAL_JOBS:
                        upsert_job(pg_conn, j)
                ob_cnt = (pg_conn.execute("SELECT count(*) as cnt FROM obituaries;").fetchone() or {}).get("cnt", 0)
                if ob_cnt == 0:
                    from data.repos.obituaries import upsert_obituary
                    for ob in INITIAL_OBITUARIES:
                        upsert_obituary(pg_conn, ob)
                pg_conn.commit()
        except Exception as e:
            logger.warning(f"Error seeding initial Postgres records: {e}")
        return

    with get_db(db_path) as conn:
        conn.executescript(SCHEMA_SQL)

        # Migration: ensure columns exist across existing SQLite tables
        def _ensure_cols(table: str, specs: list[tuple[str, str]]) -> None:
            cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table});").fetchall()]
            if not cols:
                return
            for col_name, col_def in specs:
                if col_name not in cols:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def};")

        _ensure_cols("bids", [
            ("title_en", "TEXT"),
            ("sources", "TEXT DEFAULT '[\"gazette.gov.mv\"]'"),
            ("procurement_nature", "TEXT NOT NULL DEFAULT 'Supply'"),
            ("source_id", "INTEGER REFERENCES sources(id)"),
            ("posted_date", "TEXT"),
            ("posted_time", "TEXT"),
            ("published_at", "TIMESTAMP"),
            ("submission_deadline", "TIMESTAMP"),
        ])
        _ensure_cols("obituaries", [
            ("atoll_code", "TEXT DEFAULT 'K-MALE'"),
            ("atoll_name_dv", "TEXT DEFAULT 'މާލެ / ހުޅުމާލެ'"),
            ("island_name", "TEXT DEFAULT 'މާލެ'"),
            ("region_group", "TEXT DEFAULT 'male'"),
            ("sort_order", "INTEGER DEFAULT 0"),
            ("source_id", "INTEGER REFERENCES sources(id)"),
            ("person_id", "INTEGER REFERENCES people(id)"),
            ("residence_address_id", "INTEGER REFERENCES addresses(id)"),
            ("funeral_time", "TEXT"),
            ("funeral_datetime", "TIMESTAMP"),
        ])
        _ensure_cols("sponsored_ads", [
            ("max_impressions", "INTEGER DEFAULT NULL"),
            ("expires_at", "TIMESTAMP DEFAULT NULL"),
            ("pricing_tier", "TEXT DEFAULT 'custom'"),
        ])
        _ensure_cols("company_profiles", [
            ("entity_type", "TEXT DEFAULT 'maldivian'"),
            ("country_of_origin", "TEXT DEFAULT 'Maldives'"),
            ("foreign_reg_no", "TEXT DEFAULT ''"),
            ("foreign_tax_id", "TEXT DEFAULT ''"),
            ("local_agent_name", "TEXT DEFAULT ''"),
            ("local_agent_reg", "TEXT DEFAULT ''"),
            ("local_agent_phone", "TEXT DEFAULT ''"),
            ("local_agent_email", "TEXT DEFAULT ''"),
        ])
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_obituaries_atoll ON obituaries(sort_order, atoll_code, island_name, funeral_date DESC);"
        )

        sub_columns = [row[1] for row in conn.execute("PRAGMA table_info(telegram_subscribers);").fetchall()]
        if sub_columns and "subscribed_at" not in sub_columns:
            conn.execute("ALTER TABLE telegram_subscribers ADD COLUMN subscribed_at TIMESTAMP;")
            conn.execute("UPDATE telegram_subscribers SET subscribed_at = created_at WHERE subscribed_at IS NULL;")

        try:
            _ensure_cols("telegram_subscribers", [("is_paid", "INTEGER DEFAULT 0")])
            _ensure_cols("viber_subscribers", [("is_paid", "INTEGER DEFAULT 0")])
            _ensure_cols("articles", [
                ("source_id", "INTEGER REFERENCES sources(id)"),
                ("posted_date", "TEXT"),
                ("posted_time", "TEXT"),
                ("published_at", "TIMESTAMP"),
            ])
            _ensure_cols("jobs", [
                ("source_id", "INTEGER REFERENCES sources(id)"),
                ("entity_id", "INTEGER REFERENCES entities(id)"),
                ("posted_date", "TEXT"),
                ("posted_time", "TEXT"),
                ("deadline_at", "TIMESTAMP"),
            ])
            _ensure_cols("users", [
                ("reset_token_hash", "TEXT"),
                ("reset_token_expires", "TIMESTAMP"),
                ("telegram_verified", "INTEGER DEFAULT 0"),
                ("viber_verified", "INTEGER DEFAULT 0"),
                ("account_origin", "TEXT NOT NULL DEFAULT 'web'"),
                ("viber_user_id", "TEXT"),
                ("job_alert_sources", "TEXT DEFAULT '[\"all\"]'"),
                ("tender_alert_disciplines", "TEXT DEFAULT '[\"All\"]'"),
                ("tender_alert_sources", "TEXT DEFAULT '[\"all\"]'"),
                ("alerts_enabled", "INTEGER DEFAULT 1"),
            ])
            conn.execute(
                "UPDATE users SET account_origin = 'telegram' WHERE account_origin = 'web' AND telegram_chat_id IS NOT NULL AND email LIKE 'telegram_%@khulaasaa.tech';"
            )
            _ensure_cols("notification_deliveries", [
                ("claim_token", "TEXT"),
                ("claimed_at", "TIMESTAMP"),
            ])
            _ensure_cols("user_notification_preferences", [
                ("news_alerts", "INTEGER NOT NULL DEFAULT 1"),
                ("tender_alerts", "INTEGER NOT NULL DEFAULT 1"),
                ("job_alerts", "INTEGER NOT NULL DEFAULT 1"),
                ("rental_alerts", "INTEGER NOT NULL DEFAULT 1"),
            ])
        except Exception:
            pass

        # Seed canonical sources directory
        try:
            from data.sources_data import INITIAL_SOURCES
            for s in INITIAL_SOURCES:
                conn.execute(
                    """
                    INSERT INTO sources (slug, name, domain, source_type, logo_url, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                    ON CONFLICT(slug) DO UPDATE SET
                        name = excluded.name,
                        domain = excluded.domain,
                        source_type = excluded.source_type,
                        logo_url = excluded.logo_url;
                    """,
                    (s["slug"], s["name"], s.get("domain"), s.get("source_type", "press"), s.get("logo_url"))
                )
        except Exception as e:
            logger.warning("Could not seed sources: %s", e)

        # Seed canonical reference tables (Days, Months, Hijri Months, Prayer Times, Districts)
        try:
            from data.repos.reference import seed_reference_tables
            seed_reference_tables(conn)
        except Exception as e:
            logger.warning("Could not seed reference tables: %s", e)

        # Refresh v_bids_enriched view
        conn.execute("DROP VIEW IF EXISTS v_bids_enriched;")
        conn.execute(
            """
            CREATE VIEW v_bids_enriched AS
            SELECT
                b.id, b.notice_id, b.reference_number, b.title, COALESCE(b.title_en, b.title) AS title_en,
                b.gazette_type, b.discipline, COALESCE(b.procurement_nature, 'Supply') AS procurement_nature,
                b.published_date, b.submission_date, b.submission_location, b.info_date, b.info_location,
                b.source_url, b.sources, b.document_urls, b.is_active, e.id AS entity_id,
                COALESCE(e.name_en, 'Unknown Agency') AS agency_name_en, e.name_dv AS agency_name_dv,
                COALESCE(e.entity_type, 'Other') AS entity_type, e.slug AS entity_slug,
                e.location AS entity_location, e.website AS entity_website
            FROM bids b
            LEFT JOIN entities e ON b.entity_id = e.id;
            """
        )

        # Seed canonical entities (always ensure canonical items exist)
        for ent in INITIAL_ENTITIES:
            conn.execute(
                """
                INSERT OR IGNORE INTO entities (slug, name_en, name_dv, entity_type, location, website)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (ent["slug"], ent["name_en"], ent["name_dv"], ent["entity_type"], ent["location"], ent["website"]),
            )

        # Migration: Heal any entities where name_en or slug contains raw Thaana
        try:
            from scrapers.translator import is_dhivehi, translate_agency, clean_residual_thaana
            all_entities = conn.execute("SELECT id, slug, name_en, name_dv, entity_type FROM entities;").fetchall()
            for erow in all_entities:
                raw_name = erow["name_dv"] or erow["name_en"]
                if is_dhivehi(erow["name_en"]) or is_dhivehi(erow["slug"]):
                    clean_en = clean_residual_thaana(translate_agency(raw_name))
                    clean_slug = slugify(clean_en)
                    if erow["entity_type"] == "Council" and not clean_slug.startswith("council-"):
                        clean_slug = f"council-{clean_slug}"
                    cand_slug = clean_slug
                    s_idx = 1
                    while conn.execute("SELECT 1 FROM entities WHERE slug = ? AND id != ?", (cand_slug, erow["id"])).fetchone():
                        cand_slug = f"{clean_slug}-{s_idx}"
                        s_idx += 1
                    conn.execute(
                        "UPDATE entities SET name_en = ?, name_dv = COALESCE(name_dv, ?), slug = ? WHERE id = ?;",
                        (clean_en, raw_name if is_dhivehi(raw_name) else None, cand_slug, erow["id"]),
                    )
        except Exception:
            pass

        # Heal bids where title_en contains raw Thaana or needs upgraded translation
        try:
            from scrapers.translator import is_dhivehi, translate_dhivehi_title, clean_residual_thaana
            bids_to_heal = conn.execute(
                """
                SELECT b.id, b.title, b.title_en, b.reference_number, b.submission_location, e.name_en AS agency_name_en
                FROM bids b
                LEFT JOIN entities e ON b.entity_id = e.id;
                """
            ).fetchall()
            for brow in bids_to_heal:
                t_raw = brow["title"]
                if is_dhivehi(t_raw):
                    new_title_en = clean_residual_thaana(translate_dhivehi_title(t_raw))
                    conn.execute("UPDATE bids SET title_en = ? WHERE id = ?;", (new_title_en, brow["id"]))

                # Heal generic submission_location
                sub_loc = brow["submission_location"]
                agency_name = brow["agency_name_en"] or "Agency"
                ref_num = brow["reference_number"] or ""
                if not sub_loc or sub_loc in [
                    "This Office",
                    "Council Secretariat / Agency Office",
                    "Local Council Secretariat",
                    "Council Secretariat",
                ]:
                    if "13-K" in ref_num:
                        fixed_loc = "National Tender Board, Ministry of Finance, Ameenee Magu, Male'"
                    elif "HDC" in agency_name or "Housing Development Corporation" in agency_name:
                        fixed_loc = "HDC Building Reception, Hulhumale'"
                    elif "Council" in agency_name:
                        fixed_loc = f"{agency_name} Secretariat"
                    elif "Ministry" in agency_name:
                        fixed_loc = f"{agency_name}, Male'"
                    else:
                        fixed_loc = f"{agency_name} Office"
                    conn.execute("UPDATE bids SET submission_location = ? WHERE id = ?;", (fixed_loc, brow["id"]))
        except Exception:
            pass

        # Purge bids that expired more than 30 days ago and placeholder notices
        try:
            purge_expired_bids(conn, retention_days=30)
        except Exception:
            pass

        # Seed initial sponsored ads
        for ad in INITIAL_SPONSORED_ADS:
            conn.execute(
                """
                INSERT OR IGNORE INTO sponsored_ads (campaign_name, sponsor_name, text_html, target_category, link_url)
                VALUES (?, ?, ?, ?, ?);
                """,
                (ad["campaign_name"], ad["sponsor_name"], ad["text_html"], ad["target_category"], ad["link_url"]),
            )

        # Seed initial obituaries
        for ob in INITIAL_OBITUARIES:
            geo = extract_atoll_and_island(ob.get("address_dv"), ob.get("address_en"), ob.get("funeral_mosque_dv"), ob.get("funeral_mosque_en"))
            conn.execute(
                """
                INSERT OR IGNORE INTO obituaries (
                    slug, name_dv, name_en, address_dv, address_en, age,
                    funeral_mosque_dv, funeral_mosque_en, prayer_time_dv, prayer_time_en,
                    funeral_date, death_date, photo_url, contact_numbers, source_channel, announcement_type,
                    atoll_code, atoll_name_dv, island_name, region_group, sort_order
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    ob["slug"], ob["name_dv"], ob.get("name_en"), ob.get("address_dv"), ob.get("address_en"), ob.get("age"),
                    ob.get("funeral_mosque_dv"), ob.get("funeral_mosque_en"), ob.get("prayer_time_dv"), ob.get("prayer_time_en"),
                    ob.get("funeral_date"), ob.get("death_date"), ob.get("photo_url"), ob.get("contact_numbers"),
                    ob.get("source_channel", "KashunamaadhuMV"), ob.get("announcement_type", "Janaza"),
                    ob.get("atoll_code") or geo["atoll_code"], ob.get("atoll_name_dv") or geo["atoll_name_dv"],
                    ob.get("island_name") or geo["island_name"], ob.get("region_group") or geo["region_group"],
                    ob.get("sort_order", geo["sort_order"]),
                ),
            )

        # Heal existing obituaries with atoll & island extraction
        try:
            cur_obs = conn.execute("SELECT id, address_dv, address_en, funeral_mosque_dv, funeral_mosque_en FROM obituaries WHERE atoll_code IS NULL OR atoll_code = 'K-MALE';").fetchall()
            for erow in cur_obs:
                geo = extract_atoll_and_island(erow["address_dv"], erow["address_en"], erow["funeral_mosque_dv"], erow["funeral_mosque_en"])
                conn.execute(
                    "UPDATE obituaries SET atoll_code = ?, atoll_name_dv = ?, island_name = ?, region_group = ?, sort_order = ? WHERE id = ?;",
                    (geo["atoll_code"], geo["atoll_name_dv"], geo["island_name"], geo["region_group"], geo["sort_order"], erow["id"]),
                )
        except Exception:
            pass

        # Purge obituaries older than 7 days
        try:
            purge_expired_obituaries(conn, retention_days=7)
        except Exception:
            pass

        # Seed initial verified bids if requested
        if seed_bids:
            for b in VERIFIED_HISTORIC_BIDS:
                upsert_bid(conn, dict(b))

        # Seed / sync initial jobs
        try:
            for j in INITIAL_JOBS:
                upsert_job(conn, j)
        except Exception:
            pass

        # Initialize rentals schema and seed initial apartment listings
        try:
            from data.rentals import init_rentals_schema, seed_initial_rentals
            init_rentals_schema(conn)
            seed_initial_rentals(conn)
        except Exception:
            pass

        # Initialize service modules table
        try:
            from data.modules import init_modules_table
            init_modules_table(conn)
        except Exception:
            pass

        # Run one-time auth hardening and identity backfill after legacy migrations.
        _rotate_legacy_gateway_passwords(conn)
        _backfill_platform_identities(conn)


# ---------------------------------------------------------------------
# Entity Dictionary Functions
# ---------------------------------------------------------------------

