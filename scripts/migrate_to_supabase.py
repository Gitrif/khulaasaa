"""
Khulaasaa SQLite to Supabase Migration Utility.

Exports all data from local SQLite (khulaasaa.db) and synchronizes it
directly to Supabase PostgreSQL in the cloud.

Usage:
    python scripts/migrate_to_supabase.py
    python scripts/migrate_to_supabase.py --sqlite-path ./data/khulaasaa.db --db-url "postgresql://postgres:pass@db.xyz.supabase.co:5432/postgres"
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.postgres_adapter import get_postgres_url, PostgresConnectionWrapper
import psycopg2
import psycopg2.extras


def get_sqlite_conn(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"SQLite database not found at {db_path}")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def get_supabase_conn(db_url: str) -> Any:
    # Ensure sslmode=require for cloud Supabase if not specified
    if "supabase." in db_url and "sslmode" not in db_url:
        sep = "&" if "?" in db_url else "?"
        db_url = f"{db_url}{sep}sslmode=require"
    return psycopg2.connect(db_url, cursor_factory=psycopg2.extras.DictCursor)


def migrate_entities(sqlite_conn: sqlite3.Connection, pg_conn: Any) -> int:
    cursor = sqlite_conn.execute("SELECT id, slug, name_en, name_dv, entity_type, location, website FROM entities;")
    rows = cursor.fetchall()
    if not rows:
        return 0

    with pg_conn.cursor() as pg_cur:
        for r in rows:
            pg_cur.execute(
                """
                INSERT INTO entities (id, slug, name_en, name_dv, entity_type, location, website)
                VALUES (%(id)s, %(slug)s, %(name_en)s, %(name_dv)s, %(entity_type)s, %(location)s, %(website)s)
                ON CONFLICT (slug) DO UPDATE SET
                    name_en = excluded.name_en,
                    name_dv = COALESCE(excluded.name_dv, entities.name_dv),
                    entity_type = excluded.entity_type,
                    location = COALESCE(excluded.location, entities.location),
                    website = COALESCE(excluded.website, entities.website);
                """,
                dict(r),
            )
        # Advance identity sequence to avoid collision
        pg_cur.execute("SELECT setval(pg_get_serial_sequence('entities', 'id'), COALESCE(MAX(id), 1)) FROM entities;")
    pg_conn.commit()
    return len(rows)


def migrate_bids(sqlite_conn: sqlite3.Connection, pg_conn: Any) -> int:
    cursor = sqlite_conn.execute(
        """
        SELECT notice_id, entity_id, reference_number, title, title_en, gazette_type,
               discipline, procurement_nature, published_date, submission_date,
               submission_location, info_date, info_location, source_url,
               sources, document_urls, raw_details, is_active
        FROM bids;
        """
    )
    rows = cursor.fetchall()
    if not rows:
        return 0

    with pg_conn.cursor() as pg_cur:
        for r in rows:
            d = dict(r)
            # Ensure JSONB fields are valid json
            sources = d.get("sources")
            if isinstance(sources, str):
                try:
                    sources = json.loads(sources)
                except Exception:
                    sources = ["gazette.gov.mv"]
            d["sources"] = json.dumps(sources or ["gazette.gov.mv"])

            doc_urls = d.get("document_urls")
            if isinstance(doc_urls, str):
                try:
                    doc_urls = json.loads(doc_urls)
                except Exception:
                    doc_urls = []
            d["document_urls"] = json.dumps(doc_urls or [])

            pg_cur.execute(
                """
                INSERT INTO bids (
                    notice_id, entity_id, reference_number, title, title_en,
                    gazette_type, discipline, procurement_nature, published_date,
                    submission_date, submission_location, info_date, info_location,
                    source_url, sources, document_urls, raw_details, is_active
                ) VALUES (
                    %(notice_id)s, %(entity_id)s, %(reference_number)s, %(title)s, %(title_en)s,
                    %(gazette_type)s, %(discipline)s, %(procurement_nature)s, %(published_date)s,
                    %(submission_date)s, %(submission_location)s, %(info_date)s, %(info_location)s,
                    %(source_url)s, %(sources)s::jsonb, %(document_urls)s::jsonb, %(raw_details)s, %(is_active)s
                )
                ON CONFLICT (notice_id) DO UPDATE SET
                    entity_id = excluded.entity_id,
                    reference_number = COALESCE(excluded.reference_number, bids.reference_number),
                    title = excluded.title,
                    title_en = COALESCE(excluded.title_en, bids.title_en),
                    gazette_type = excluded.gazette_type,
                    discipline = excluded.discipline,
                    procurement_nature = excluded.procurement_nature,
                    published_date = COALESCE(excluded.published_date, bids.published_date),
                    submission_date = COALESCE(excluded.submission_date, bids.submission_date),
                    submission_location = COALESCE(excluded.submission_location, bids.submission_location),
                    info_date = COALESCE(excluded.info_date, bids.info_date),
                    info_location = COALESCE(excluded.info_location, bids.info_location),
                    source_url = excluded.source_url,
                    sources = excluded.sources,
                    document_urls = excluded.document_urls,
                    raw_details = COALESCE(excluded.raw_details, bids.raw_details),
                    is_active = excluded.is_active,
                    updated_at = NOW();
                """,
                d,
            )
        pg_cur.execute("SELECT setval(pg_get_serial_sequence('bids', 'id'), COALESCE(MAX(id), 1)) FROM bids;")
    pg_conn.commit()
    return len(rows)


def migrate_articles(sqlite_conn: sqlite3.Connection, pg_conn: Any) -> int:
    cursor = sqlite_conn.execute("SELECT id, headline, summary, published_raw, published_iso, minutes_ago, source_key, url, section, topic, tags FROM articles;")
    rows = cursor.fetchall()
    if not rows:
        return 0

    with pg_conn.cursor() as pg_cur:
        for r in rows:
            d = dict(r)
            tags = d.get("tags")
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except Exception:
                    tags = []
            d["tags"] = json.dumps(tags or [])

            pg_cur.execute(
                """
                INSERT INTO articles (
                    id, headline, summary, published_raw, published_iso,
                    minutes_ago, source_key, url, section, topic, tags
                ) VALUES (
                    %(id)s, %(headline)s, %(summary)s, %(published_raw)s, %(published_iso)s,
                    %(minutes_ago)s, %(source_key)s, %(url)s, %(section)s, %(topic)s, %(tags)s::jsonb
                )
                ON CONFLICT (id) DO UPDATE SET
                    headline = excluded.headline,
                    summary = excluded.summary,
                    published_raw = excluded.published_raw,
                    published_iso = excluded.published_iso,
                    minutes_ago = excluded.minutes_ago,
                    source_key = excluded.source_key,
                    url = excluded.url,
                    section = excluded.section,
                    topic = excluded.topic,
                    tags = excluded.tags;
                """,
                d,
            )
    pg_conn.commit()
    return len(rows)


def migrate_obituaries(sqlite_conn: sqlite3.Connection, pg_conn: Any) -> int:
    cursor = sqlite_conn.execute("SELECT * FROM obituaries;")
    rows = cursor.fetchall()
    if not rows:
        return 0

    with pg_conn.cursor() as pg_cur:
        for r in rows:
            d = dict(r)
            d.pop("created_at", None)
            cols = [c for c in d.keys() if c != "id"]
            cols_str = ", ".join(cols)
            vals_str = ", ".join([f"%({c})s" for c in cols])
            pg_cur.execute(
                f"""
                INSERT INTO obituaries ({cols_str})
                VALUES ({vals_str})
                ON CONFLICT (slug) DO UPDATE SET
                    name_dv = excluded.name_dv,
                    name_en = excluded.name_en,
                    address_dv = excluded.address_dv,
                    address_en = excluded.address_en,
                    age = excluded.age,
                    funeral_mosque_dv = excluded.funeral_mosque_dv,
                    prayer_time_dv = excluded.prayer_time_dv,
                    funeral_date = excluded.funeral_date,
                    is_active = excluded.is_active;
                """,
                d,
            )
        pg_cur.execute("SELECT setval(pg_get_serial_sequence('obituaries', 'id'), COALESCE(MAX(id), 1)) FROM obituaries;")
    pg_conn.commit()
    return len(rows)


def migrate_jobs(sqlite_conn: sqlite3.Connection, pg_conn: Any) -> int:
    cursor = sqlite_conn.execute("SELECT * FROM jobs;")
    rows = cursor.fetchall()
    if not rows:
        return 0

    with pg_conn.cursor() as pg_cur:
        for r in rows:
            d = dict(r)
            d.pop("created_at", None)
            cols = [c for c in d.keys() if c != "id"]
            cols_str = ", ".join(cols)
            vals_str = ", ".join([f"%({c})s" for c in cols])
            pg_cur.execute(
                f"""
                INSERT INTO jobs ({cols_str})
                VALUES ({vals_str})
                ON CONFLICT (notice_id) DO UPDATE SET
                    title = excluded.title,
                    title_en = excluded.title_en,
                    agency = excluded.agency,
                    discipline = excluded.discipline,
                    deadline_iso = excluded.deadline_iso,
                    is_active = excluded.is_active;
                """,
                d,
            )
        pg_cur.execute("SELECT setval(pg_get_serial_sequence('jobs', 'id'), COALESCE(MAX(id), 1)) FROM jobs;")
    pg_conn.commit()
    return len(rows)


def migrate_sponsored_ads(sqlite_conn: sqlite3.Connection, pg_conn: Any) -> int:
    cursor = sqlite_conn.execute("SELECT * FROM sponsored_ads;")
    rows = cursor.fetchall()
    if not rows:
        return 0

    with pg_conn.cursor() as pg_cur:
        for r in rows:
            d = dict(r)
            d.pop("created_at", None)
            cols = [c for c in d.keys() if c != "id"]
            cols_str = ", ".join(cols)
            vals_str = ", ".join([f"%({c})s" for c in cols])
            pg_cur.execute(
                f"""
                INSERT INTO sponsored_ads ({cols_str})
                VALUES ({vals_str})
                ON CONFLICT (campaign_name) DO UPDATE SET
                    sponsor_name = excluded.sponsor_name,
                    text_html = excluded.text_html,
                    target_category = excluded.target_category,
                    link_url = excluded.link_url,
                    is_active = excluded.is_active;
                """,
                d,
            )
        pg_cur.execute("SELECT setval(pg_get_serial_sequence('sponsored_ads', 'id'), COALESCE(MAX(id), 1)) FROM sponsored_ads;")
    pg_conn.commit()
    return len(rows)


def migrate_subscribers(sqlite_conn: sqlite3.Connection, pg_conn: Any) -> tuple[int, int]:
    # Telegram
    t_rows = sqlite_conn.execute("SELECT * FROM telegram_subscribers;").fetchall()
    with pg_conn.cursor() as pg_cur:
        for r in t_rows:
            d = dict(r)
            for jf in ["disciplines", "keywords"]:
                v = d.get(jf)
                if isinstance(v, str):
                    try:
                        v = json.loads(v)
                    except Exception:
                        v = []
                d[jf] = json.dumps(v or [])
            pg_cur.execute(
                """
                INSERT INTO telegram_subscribers (chat_id, name, disciplines, keywords, is_active)
                VALUES (%(chat_id)s, %(name)s, %(disciplines)s::jsonb, %(keywords)s::jsonb, %(is_active)s)
                ON CONFLICT (chat_id) DO UPDATE SET
                    name = excluded.name,
                    disciplines = excluded.disciplines,
                    keywords = excluded.keywords,
                    is_active = excluded.is_active;
                """,
                d,
            )
        pg_cur.execute("SELECT setval(pg_get_serial_sequence('telegram_subscribers', 'id'), COALESCE(MAX(id), 1)) FROM telegram_subscribers;")

    # Viber
    v_rows = sqlite_conn.execute("SELECT * FROM viber_subscribers;").fetchall()
    with pg_conn.cursor() as pg_cur:
        for r in v_rows:
            d = dict(r)
            cat = d.get("subscribed_categories")
            if isinstance(cat, str):
                try:
                    cat = json.loads(cat)
                except Exception:
                    cat = ["all"]
            d["subscribed_categories"] = json.dumps(cat or ["all"])
            pg_cur.execute(
                """
                INSERT INTO viber_subscribers (viber_user_id, name, avatar, subscribed_categories, is_active)
                VALUES (%(viber_user_id)s, %(name)s, %(avatar)s, %(subscribed_categories)s::jsonb, %(is_active)s)
                ON CONFLICT (viber_user_id) DO UPDATE SET
                    name = excluded.name,
                    avatar = excluded.avatar,
                    subscribed_categories = excluded.subscribed_categories,
                    is_active = excluded.is_active;
                """,
                d,
            )
        pg_cur.execute("SELECT setval(pg_get_serial_sequence('viber_subscribers', 'id'), COALESCE(MAX(id), 1)) FROM viber_subscribers;")
    pg_conn.commit()
    return len(t_rows), len(v_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate Khulaasaa SQLite database to Supabase PostgreSQL.")
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "khulaasaa.db",
        help="Path to local SQLite file (default: data/khulaasaa.db)",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Supabase PostgreSQL connection URL (or set DATABASE_URL/SUPABASE_DB_URL env var)",
    )
    args = parser.parse_args()

    db_url = args.db_url or get_postgres_url()
    if not db_url:
        print("[ERROR] No Supabase PostgreSQL URL specified.")
        print("Provide --db-url or set the DATABASE_URL environment variable.")
        sys.exit(1)

    print(f"[*] Opening SQLite database: {args.sqlite_path}")
    sqlite_conn = get_sqlite_conn(args.sqlite_path)

    print("[*] Connecting to Supabase PostgreSQL...")
    pg_conn = get_supabase_conn(db_url)

    print("\nStarting migration into Supabase:")
    print("--------------------------------------------------")

    n_entities = migrate_entities(sqlite_conn, pg_conn)
    print(f" [+] Entities:            {n_entities:>5} migrated/synced")

    n_bids = migrate_bids(sqlite_conn, pg_conn)
    print(f" [+] Bids & Tenders:      {n_bids:>5} migrated/synced")

    n_articles = migrate_articles(sqlite_conn, pg_conn)
    print(f" [+] News Articles:       {n_articles:>5} migrated/synced")

    n_jobs = migrate_jobs(sqlite_conn, pg_conn)
    print(f" [+] Job Postings:        {n_jobs:>5} migrated/synced")

    n_obits = migrate_obituaries(sqlite_conn, pg_conn)
    print(f" [+] Obituaries/Janaza:   {n_obits:>5} migrated/synced")

    n_ads = migrate_sponsored_ads(sqlite_conn, pg_conn)
    print(f" [+] Sponsored Ads:       {n_ads:>5} migrated/synced")

    n_tg, n_vb = migrate_subscribers(sqlite_conn, pg_conn)
    print(f" [+] Subscribers:         {n_tg:>5} Telegram, {n_vb} Viber")

    print("--------------------------------------------------")
    print("[SUCCESS] All scraped data successfully synchronized to Supabase!\n")

    sqlite_conn.close()
    pg_conn.close()


if __name__ == "__main__":
    main()
