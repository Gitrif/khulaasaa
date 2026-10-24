"""Initial baseline schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-19 02:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    is_postgres = conn.dialect.name == "postgresql"

    # Entities
    if not conn.dialect.has_table(conn, "entities"):
        op.create_table(
            "entities",
            sa.Column("id", sa.BigInteger() if is_postgres else sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("slug", sa.String(), nullable=False, unique=True),
            sa.Column("name_en", sa.String(), nullable=False),
            sa.Column("name_dv", sa.String(), nullable=True),
            sa.Column("entity_type", sa.String(), nullable=False),
            sa.Column("location", sa.String(), nullable=True),
            sa.Column("website", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("idx_entities_slug", "entities", ["slug"])
        op.create_index("idx_entities_type", "entities", ["entity_type"])

    # Bids
    if not conn.dialect.has_table(conn, "bids"):
        op.create_table(
            "bids",
            sa.Column("id", sa.BigInteger() if is_postgres else sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("notice_id", sa.String(), nullable=False, unique=True),
            sa.Column("entity_id", sa.BigInteger() if is_postgres else sa.Integer(), sa.ForeignKey("entities.id", ondelete="SET NULL"), nullable=True),
            sa.Column("reference_number", sa.String(), nullable=True),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("title_en", sa.String(), nullable=True),
            sa.Column("gazette_type", sa.String(), nullable=False, server_default="Bid"),
            sa.Column("discipline", sa.String(), nullable=False, server_default="Other"),
            sa.Column("procurement_nature", sa.String(), nullable=False, server_default="Supply"),
            sa.Column("published_date", sa.String(), nullable=True),
            sa.Column("submission_date", sa.String(), nullable=True),
            sa.Column("submission_location", sa.String(), nullable=True),
            sa.Column("info_date", sa.String(), nullable=True),
            sa.Column("info_location", sa.String(), nullable=True),
            sa.Column("source_url", sa.String(), nullable=False),
            sa.Column("sources", sa.JSON() if is_postgres else sa.String(), server_default='["gazette.gov.mv"]'),
            sa.Column("document_urls", sa.JSON() if is_postgres else sa.String(), server_default="[]"),
            sa.Column("raw_details", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Integer(), server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index("idx_bids_entity_id", "bids", ["entity_id"])
        op.create_index("idx_bids_discipline", "bids", ["discipline"])
        op.create_index("idx_bids_submission_date", "bids", ["submission_date"])

    # Telegram Subscribers
    if not conn.dialect.has_table(conn, "telegram_subscribers"):
        op.create_table(
            "telegram_subscribers",
            sa.Column("id", sa.BigInteger() if is_postgres else sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("chat_id", sa.String(), nullable=False, unique=True),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("disciplines", sa.JSON() if is_postgres else sa.String(), server_default="[]"),
            sa.Column("keywords", sa.JSON() if is_postgres else sa.String(), server_default="[]"),
            sa.Column("is_active", sa.Integer(), server_default="1"),
            sa.Column("subscribed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    # Viber Subscribers
    if not conn.dialect.has_table(conn, "viber_subscribers"):
        op.create_table(
            "viber_subscribers",
            sa.Column("id", sa.BigInteger() if is_postgres else sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("viber_user_id", sa.String(), nullable=False, unique=True),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("avatar", sa.String(), nullable=True),
            sa.Column("subscribed_categories", sa.JSON() if is_postgres else sa.String(), server_default='["all"]'),
            sa.Column("is_active", sa.Integer(), server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    # Sent Alerts
    if not conn.dialect.has_table(conn, "sent_alerts"):
        op.create_table(
            "sent_alerts",
            sa.Column("id", sa.BigInteger() if is_postgres else sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("notice_id", sa.String(), nullable=False),
            sa.Column("chat_id", sa.String(), nullable=False),
            sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("notice_id", "chat_id", name="uq_sent_alerts_notice_chat"),
        )
        op.create_index("idx_sent_alerts_lookup", "sent_alerts", ["notice_id", "chat_id"])

    # Articles
    if not conn.dialect.has_table(conn, "articles"):
        op.create_table(
            "articles",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("headline", sa.String(), nullable=False),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("published_raw", sa.String(), nullable=True),
            sa.Column("published_iso", sa.String(), nullable=True),
            sa.Column("minutes_ago", sa.Integer(), server_default="60"),
            sa.Column("source_key", sa.String(), nullable=False),
            sa.Column("url", sa.String(), nullable=True),
            sa.Column("section", sa.String(), server_default="general"),
            sa.Column("topic", sa.String(), server_default="policy"),
            sa.Column("tags", sa.JSON() if is_postgres else sa.String(), server_default="[]"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("idx_articles_published", "articles", ["published_iso"])

    # Sponsored Ads
    if not conn.dialect.has_table(conn, "sponsored_ads"):
        op.create_table(
            "sponsored_ads",
            sa.Column("id", sa.BigInteger() if is_postgres else sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("campaign_name", sa.String(), nullable=False, unique=True),
            sa.Column("sponsor_name", sa.String(), nullable=False),
            sa.Column("text_html", sa.Text(), nullable=False),
            sa.Column("target_category", sa.String(), nullable=False, server_default="all"),
            sa.Column("link_url", sa.String(), nullable=True),
            sa.Column("is_active", sa.Integer(), server_default="1"),
            sa.Column("impressions", sa.Integer(), server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("idx_sponsored_ads_target", "sponsored_ads", ["target_category", "is_active"])

    # Obituaries
    if not conn.dialect.has_table(conn, "obituaries"):
        op.create_table(
            "obituaries",
            sa.Column("id", sa.BigInteger() if is_postgres else sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("slug", sa.String(), nullable=False, unique=True),
            sa.Column("name_dv", sa.String(), nullable=False),
            sa.Column("name_en", sa.String(), nullable=True),
            sa.Column("address_dv", sa.String(), nullable=True),
            sa.Column("address_en", sa.String(), nullable=True),
            sa.Column("age", sa.Integer(), nullable=True),
            sa.Column("funeral_mosque_dv", sa.String(), nullable=True),
            sa.Column("funeral_mosque_en", sa.String(), nullable=True),
            sa.Column("prayer_time_dv", sa.String(), nullable=True),
            sa.Column("prayer_time_en", sa.String(), nullable=True),
            sa.Column("funeral_date", sa.String(), nullable=True),
            sa.Column("death_date", sa.String(), nullable=True),
            sa.Column("photo_url", sa.String(), nullable=True),
            sa.Column("contact_numbers", sa.String(), nullable=True),
            sa.Column("source_channel", sa.String(), server_default="KashunamaadhuMV"),
            sa.Column("announcement_type", sa.String(), server_default="Janaza"),
            sa.Column("atoll_code", sa.String(), server_default="K-MALE"),
            sa.Column("atoll_name_dv", sa.String(), server_default="މާލެ / ހުޅުމާލެ"),
            sa.Column("island_name", sa.String(), server_default="މާލެ"),
            sa.Column("region_group", sa.String(), server_default="male"),
            sa.Column("sort_order", sa.Integer(), server_default="0"),
            sa.Column("is_active", sa.Integer(), server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("idx_obituaries_slug", "obituaries", ["slug"])
        op.create_index("idx_obituaries_date", "obituaries", ["funeral_date", "created_at"])

    # Users
    if not conn.dialect.has_table(conn, "users"):
        op.create_table(
            "users",
            sa.Column("id", sa.BigInteger() if is_postgres else sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("email", sa.String(), nullable=False, unique=True),
            sa.Column("password_hash", sa.String(), nullable=False),
            sa.Column("full_name", sa.String(), nullable=False),
            sa.Column("phone", sa.String(), nullable=True),
            sa.Column("telegram_chat_id", sa.String(), nullable=True),
            sa.Column("viber_user_id", sa.String(), nullable=True),
            sa.Column("job_alert_categories", sa.JSON() if is_postgres else sa.String(), server_default='["all"]'),
            sa.Column("is_paid", sa.Integer(), server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index("idx_users_email", "users", ["email"])

    # User Sessions
    if not conn.dialect.has_table(conn, "user_sessions"):
        op.create_table(
            "user_sessions",
            sa.Column("token", sa.String(), primary_key=True),
            sa.Column("user_id", sa.BigInteger() if is_postgres else sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("idx_user_sessions_token", "user_sessions", ["token"])

    # User CVs
    if not conn.dialect.has_table(conn, "user_cvs"):
        op.create_table(
            "user_cvs",
            sa.Column("id", sa.BigInteger() if is_postgres else sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.BigInteger() if is_postgres else sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(), server_default="Maldivian Curriculum Vitae"),
            sa.Column("template", sa.String(), server_default="standard"),
            sa.Column("data_json", sa.JSON() if is_postgres else sa.Text(), nullable=False),
            sa.Column("photo_data", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index("idx_user_cvs_user_id", "user_cvs", ["user_id"])

    # Jobs
    if not conn.dialect.has_table(conn, "jobs"):
        op.create_table(
            "jobs",
            sa.Column("id", sa.BigInteger() if is_postgres else sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("notice_id", sa.String(), nullable=True, unique=True),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("title_en", sa.String(), nullable=True),
            sa.Column("agency", sa.String(), nullable=False),
            sa.Column("agency_name_en", sa.String(), nullable=True),
            sa.Column("discipline", sa.String(), nullable=False, server_default="Other"),
            sa.Column("location", sa.String(), server_default="Male'"),
            sa.Column("salary_raw", sa.String(), nullable=True),
            sa.Column("deadline_iso", sa.String(), nullable=True),
            sa.Column("published_date", sa.String(), nullable=True),
            sa.Column("source_url", sa.String(), nullable=True),
            sa.Column("source_portal", sa.String(), server_default="gazette.gov.mv"),
            sa.Column("requirements", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Integer(), server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("idx_jobs_discipline", "jobs", ["discipline"])
        op.create_index("idx_jobs_deadline", "jobs", ["deadline_iso"])

    # Company Profiles
    if not conn.dialect.has_table(conn, "company_profiles"):
        op.create_table(
            "company_profiles",
            sa.Column("id", sa.BigInteger() if is_postgres else sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.BigInteger() if is_postgres else sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
            sa.Column("company_name", sa.String(), nullable=False),
            sa.Column("registration_number", sa.String(), nullable=True),
            sa.Column("registration_date", sa.String(), nullable=True),
            sa.Column("tin_number", sa.String(), nullable=True),
            sa.Column("registered_address", sa.String(), nullable=True),
            sa.Column("phone", sa.String(), nullable=True),
            sa.Column("email", sa.String(), nullable=True),
            sa.Column("website", sa.String(), nullable=True),
            sa.Column("philosophy", sa.Text(), nullable=True),
            sa.Column("mission", sa.Text(), nullable=True),
            sa.Column("managing_director_name", sa.String(), nullable=True),
            sa.Column("managing_director_message", sa.Text(), nullable=True),
            sa.Column("directors_json", sa.JSON() if is_postgres else sa.Text(), nullable=True),
            sa.Column("core_business_json", sa.JSON() if is_postgres else sa.Text(), nullable=True),
            sa.Column("values_json", sa.JSON() if is_postgres else sa.Text(), nullable=True),
            sa.Column("clients_json", sa.JSON() if is_postgres else sa.Text(), nullable=True),
            sa.Column("logo_data", sa.Text(), nullable=True),
            sa.Column("cover_image_url", sa.String(), nullable=True),
            sa.Column("template", sa.String(), server_default="corporate"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index("idx_company_profiles_user_id", "company_profiles", ["user_id"])

    # View: v_bids_enriched
    op.execute(
        """
        CREATE VIEW IF NOT EXISTS v_bids_enriched AS
        SELECT
            b.id,
            b.notice_id,
            b.reference_number,
            b.title,
            COALESCE(b.title_en, b.title) AS title_en,
            b.gazette_type,
            b.discipline,
            COALESCE(b.procurement_nature, 'Supply') AS procurement_nature,
            b.published_date,
            b.submission_date,
            b.submission_location,
            b.info_date,
            b.info_location,
            b.source_url,
            b.sources,
            b.document_urls,
            b.is_active,
            e.id AS entity_id,
            COALESCE(e.name_en, 'Unknown Agency') AS agency_name_en,
            e.name_dv AS agency_name_dv,
            COALESCE(e.entity_type, 'Other') AS entity_type,
            e.slug AS entity_slug,
            e.location AS entity_location,
            e.website AS entity_website
        FROM bids b
        LEFT JOIN entities e ON b.entity_id = e.id;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_bids_enriched;")
    op.drop_table("company_profiles")
    op.drop_table("jobs")
    op.drop_table("user_cvs")
    op.drop_table("user_sessions")
    op.drop_table("users")
    op.drop_table("obituaries")
    op.drop_table("sponsored_ads")
    op.drop_table("articles")
    op.drop_table("sent_alerts")
    op.drop_table("viber_subscribers")
    op.drop_table("telegram_subscribers")
    op.drop_table("bids")
    op.drop_table("entities")
