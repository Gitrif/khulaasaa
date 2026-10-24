"""
Database schema SQL and DDL definitions for Khulaasaa.
"""

# ---------------------------------------------------------------------
# Database Schema
# ---------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    name_en TEXT NOT NULL,
    name_dv TEXT,
    entity_type TEXT NOT NULL, -- 'SOE', 'Ministry', 'Council', 'Healthcare', 'Education', 'Independent'
    location TEXT,
    website TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notice_id TEXT UNIQUE NOT NULL,
    entity_id INTEGER REFERENCES entities(id) ON DELETE SET NULL,
    reference_number TEXT,
    title TEXT NOT NULL,
    title_en TEXT,
    gazette_type TEXT NOT NULL DEFAULT 'Bid',
    discipline TEXT NOT NULL DEFAULT 'Other',
    procurement_nature TEXT NOT NULL DEFAULT 'Supply', -- 'Service', 'Supply', 'Lease'
    published_date TEXT,
    submission_date TEXT,
    submission_location TEXT,
    info_date TEXT,
    info_location TEXT,
    source_url TEXT NOT NULL,
    sources TEXT DEFAULT '["gazette.gov.mv"]', -- JSON string array of publishing portals
    document_urls TEXT, -- JSON string array
    raw_details TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS telegram_subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT UNIQUE NOT NULL,
    name TEXT,
    disciplines TEXT, -- JSON string array e.g. ["IT", "Construction"]
    keywords TEXT,    -- JSON string array e.g. ["harbour", "generator"]
    is_paid INTEGER DEFAULT 0, -- 0 for Free tier (normal feed), 1 for Pro tier (MVR 50/mo custom alerts)
    is_active INTEGER DEFAULT 1,
    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS viber_subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    viber_user_id TEXT UNIQUE NOT NULL,
    name TEXT,
    avatar TEXT,
    subscribed_categories TEXT DEFAULT '["all"]', -- JSON string array e.g. ["news", "janaza", "bids"]
    is_paid INTEGER DEFAULT 0, -- 0 for Free tier (normal feed), 1 for Pro tier (MVR 50/mo custom alerts)
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS sent_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notice_id TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(notice_id, chat_id)
);

CREATE TABLE IF NOT EXISTS articles (
    id TEXT PRIMARY KEY,
    headline TEXT NOT NULL,
    summary TEXT,
    published_raw TEXT,
    published_iso TEXT,
    minutes_ago INTEGER DEFAULT 60,
    source_key TEXT NOT NULL,
    url TEXT,
    section TEXT DEFAULT 'general',
    topic TEXT DEFAULT 'policy',
    tags TEXT DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sponsored_ads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_name TEXT UNIQUE NOT NULL,
    sponsor_name TEXT NOT NULL,
    text_html TEXT NOT NULL,
    target_category TEXT NOT NULL DEFAULT 'all', -- 'all', 'bids', 'news'
    link_url TEXT,
    is_active INTEGER DEFAULT 1,
    impressions INTEGER DEFAULT 0,
    max_impressions INTEGER DEFAULT NULL,
    expires_at TIMESTAMP DEFAULT NULL,
    pricing_tier TEXT DEFAULT 'custom',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hooks85_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    island_atoll TEXT,
    plan_tier TEXT DEFAULT 'tender_erp',
    interested_modules TEXT,
    notice_id TEXT,
    notes TEXT,
    status TEXT DEFAULT 'new',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_hooks85_sub_phone ON hooks85_subscriptions(phone);

CREATE TABLE IF NOT EXISTS obituaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    name_dv TEXT NOT NULL,
    name_en TEXT,
    address_dv TEXT,
    address_en TEXT,
    age INTEGER,
    funeral_mosque_dv TEXT,
    funeral_mosque_en TEXT,
    prayer_time_dv TEXT,
    prayer_time_en TEXT,
    funeral_date TEXT,
    death_date TEXT,
    photo_url TEXT,
    contact_numbers TEXT,
    source_channel TEXT DEFAULT 'KashunamaadhuMV',
    announcement_type TEXT DEFAULT 'Janaza',
    atoll_code TEXT DEFAULT 'K-MALE',
    atoll_name_dv TEXT DEFAULT 'މާލެ / ހުޅުމާލެ',
    island_name TEXT DEFAULT 'މާލެ',
    region_group TEXT DEFAULT 'male',
    sort_order INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    phone TEXT,
    telegram_chat_id TEXT,
    viber_user_id TEXT,
    job_alert_categories TEXT DEFAULT '["all"]', -- JSON array of disciplines e.g. ["IT", "Administration"]
    job_alert_sources TEXT DEFAULT '["all"]', -- JSON array of sources e.g. ["Gazette", "SOE", "Private"]
    tender_alert_disciplines TEXT DEFAULT '["All"]', -- JSON array e.g. ["Construction", "IT"]
    tender_alert_sources TEXT DEFAULT '["all"]', -- JSON array e.g. ["Gazette", "HDC", "STO"]
    alerts_enabled INTEGER DEFAULT 1,
    is_paid INTEGER DEFAULT 0, -- 0 for Free tier, 1 for Pro/Paid tier
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_cvs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT DEFAULT 'Maldivian Curriculum Vitae',
    template TEXT DEFAULT 'standard', -- 'standard' (Free Maldivian), 'executive', 'slate', 'navy' (Paid)
    data_json TEXT NOT NULL,
    photo_data TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notice_id TEXT UNIQUE,
    title TEXT NOT NULL,
    title_en TEXT,
    agency TEXT NOT NULL,
    agency_name_en TEXT,
    discipline TEXT NOT NULL DEFAULT 'Other',
    location TEXT DEFAULT "Male'",
    salary_raw TEXT,
    deadline_iso TEXT,
    published_date TEXT,
    source_url TEXT,
    source_portal TEXT DEFAULT 'gazette.gov.mv',
    requirements TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS company_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    company_name TEXT NOT NULL,
    entity_type TEXT DEFAULT 'maldivian',
    country_of_origin TEXT DEFAULT 'Maldives',
    registration_number TEXT,
    registration_date TEXT,
    tin_number TEXT,
    foreign_reg_no TEXT DEFAULT '',
    foreign_tax_id TEXT DEFAULT '',
    local_agent_name TEXT DEFAULT '',
    local_agent_reg TEXT DEFAULT '',
    local_agent_phone TEXT DEFAULT '',
    local_agent_email TEXT DEFAULT '',
    registered_address TEXT,
    phone TEXT,
    email TEXT,
    website TEXT,
    philosophy TEXT,
    mission TEXT,
    managing_director_name TEXT,
    managing_director_message TEXT,
    directors_json TEXT,
    core_business_json TEXT,
    values_json TEXT,
    clients_json TEXT,
    logo_data TEXT,
    cover_image_url TEXT,
    template TEXT DEFAULT 'corporate',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_entities_slug ON entities(slug);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_bids_entity_id ON bids(entity_id);
CREATE INDEX IF NOT EXISTS idx_bids_discipline ON bids(discipline);
CREATE INDEX IF NOT EXISTS idx_bids_submission_date ON bids(submission_date);
CREATE INDEX IF NOT EXISTS idx_sent_alerts_lookup ON sent_alerts(notice_id, chat_id);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published_iso DESC);
CREATE INDEX IF NOT EXISTS idx_sponsored_ads_target ON sponsored_ads(target_category, is_active);
CREATE INDEX IF NOT EXISTS idx_obituaries_date ON obituaries(funeral_date DESC, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_discipline ON jobs(discipline);
CREATE INDEX IF NOT EXISTS idx_jobs_deadline ON jobs(deadline_iso DESC);
CREATE INDEX IF NOT EXISTS idx_user_cvs_user_id ON user_cvs(user_id);
CREATE INDEX IF NOT EXISTS idx_company_profiles_user_id ON company_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(token);

CREATE VIEW IF NOT EXISTS v_bids_enriched AS
SELECT
    b.id,
    b.notice_id,
    b.reference_number,
    b.title,
    COALESCE(b.title_en, b.title) AS title_en,
    b.gazette_type,
    b.discipline,
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

