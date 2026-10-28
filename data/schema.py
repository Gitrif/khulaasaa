"""
Database schema SQL and DDL definitions for Khulaasaa.
"""

SCHEMA_SQL = """
-- 1. Canonical Sources Registry (Single Source of Truth for Portals, Media, and Marketplaces)
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    domain TEXT,
    source_type TEXT NOT NULL DEFAULT 'press', -- 'press', 'official', 'wire', 'portal', 'marketplace'
    logo_url TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Canonical Atolls & Islands Directory
CREATE TABLE IF NOT EXISTS atolls (
    code TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    name_dv TEXT NOT NULL,
    traditional_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS islands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    atoll_code TEXT REFERENCES atolls(code) ON DELETE CASCADE,
    name_en TEXT NOT NULL,
    name_dv TEXT,
    is_inhabited INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Reference Tables: Days of the Week
CREATE TABLE IF NOT EXISTS ref_days (
    day_number INTEGER PRIMARY KEY, -- 1=Sunday, 2=Monday, ..., 7=Saturday
    code TEXT UNIQUE NOT NULL,       -- 'SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'
    name_en TEXT UNIQUE NOT NULL,   -- 'Sunday', 'Monday', ...
    name_dv TEXT UNIQUE NOT NULL,   -- 'އާދީއްތަ', 'ހޯމަ', ...
    is_weekend INTEGER NOT NULL DEFAULT 0 -- 1 for Friday and Saturday
);

-- Reference Tables: Gregorian Months
CREATE TABLE IF NOT EXISTS ref_months (
    month_number INTEGER PRIMARY KEY, -- 1 to 12
    code TEXT UNIQUE NOT NULL,        -- 'JAN', 'FEB', ...
    name_en TEXT UNIQUE NOT NULL,    -- 'January', 'February', ...
    name_dv TEXT UNIQUE NOT NULL,    -- 'ޖެނުއަރީ', 'ފެބްރުއަރީ', ...
    abbr_en TEXT UNIQUE NOT NULL,    -- 'Jan', 'Feb', ...
    days_count INTEGER NOT NULL      -- 31, 28, 31, 30, ...
);

-- Reference Tables: Islamic Hijri Months
CREATE TABLE IF NOT EXISTS ref_hijri_months (
    month_number INTEGER PRIMARY KEY, -- 1 to 12
    name_en TEXT UNIQUE NOT NULL,    -- 'Muharram', 'Safar', ...
    name_dv TEXT UNIQUE NOT NULL,    -- 'މުޙައްރަމް', 'ޞަފަރު', ...
    name_ar TEXT NOT NULL            -- 'محرم', 'صفر', ...
);

-- Reference Tables: Prayer Times / Janaza Times
CREATE TABLE IF NOT EXISTS ref_prayer_times (
    id INTEGER PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,       -- 'fajr', 'dhuhr', 'asr', 'maghrib', 'isha'
    name_en TEXT NOT NULL,           -- 'Fajr', 'Dhuhr', ...
    name_dv TEXT NOT NULL,           -- 'ފަތިސް', 'މެންދުރު', ...
    sort_order INTEGER NOT NULL
);

-- Reference Tables: Maldivian Districts / Wards
CREATE TABLE IF NOT EXISTS ref_districts (
    code TEXT PRIMARY KEY,           -- 'H', 'G', 'M', 'MA', 'V', 'H1', 'H2'
    name_en TEXT NOT NULL,           -- 'Henveiru', 'Galolhu', ...
    name_dv TEXT NOT NULL,           -- 'ހެންވޭރު', 'ގަލޮޅު', ...
    island_name_en TEXT NOT NULL DEFAULT 'Male'
);

-- 3. Canonical Addresses Registry (Single Source of Truth for Maldivian Geography)
CREATE TABLE IF NOT EXISTS addresses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code TEXT NOT NULL DEFAULT 'MDV',
    atoll_code TEXT,
    atoll_name_en TEXT,
    atoll_name_dv TEXT,
    island_name_en TEXT,
    island_name_dv TEXT,
    district TEXT,
    road TEXT,
    building_name TEXT,
    floor TEXT,
    unit TEXT,
    postal_code TEXT,
    latitude REAL,
    longitude REAL,
    formatted_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Canonical People Registry (Single Source of Truth for Individuals)
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nid_number TEXT UNIQUE,
    full_name_en TEXT NOT NULL,
    full_name_dv TEXT,
    gender TEXT,
    phone TEXT,
    email TEXT,
    permanent_address_id INTEGER REFERENCES addresses(id) ON DELETE SET NULL,
    current_address_id INTEGER REFERENCES addresses(id) ON DELETE SET NULL,
    date_of_birth TEXT,
    date_of_death TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Entities Dictionary (Ministries, SOEs, Councils, Companies, Institutions)
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
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    entity_id INTEGER REFERENCES entities(id) ON DELETE SET NULL,
    reference_number TEXT,
    title TEXT NOT NULL,
    title_en TEXT,
    gazette_type TEXT NOT NULL DEFAULT 'Bid',
    discipline TEXT NOT NULL DEFAULT 'Other',
    procurement_nature TEXT NOT NULL DEFAULT 'Supply', -- 'Service', 'Supply', 'Lease'
    published_date TEXT,
    posted_date TEXT,
    posted_time TEXT,
    published_at TIMESTAMP,
    submission_date TEXT,
    submission_deadline TIMESTAMP,
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
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    headline TEXT NOT NULL,
    summary TEXT,
    published_raw TEXT,
    published_iso TEXT,
    posted_date TEXT,
    posted_time TEXT,
    published_at TIMESTAMP,
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
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    person_id INTEGER REFERENCES people(id) ON DELETE SET NULL,
    residence_address_id INTEGER REFERENCES addresses(id) ON DELETE SET NULL,
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
    funeral_time TEXT,
    death_date TEXT,
    funeral_datetime TIMESTAMP,
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
    telegram_verified INTEGER DEFAULT 0,
    viber_verified INTEGER DEFAULT 0,
    reset_token_hash TEXT,
    reset_token_expires TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_follows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_type TEXT NOT NULL, -- 'story', 'topic', 'section', 'source'
    target_id TEXT NOT NULL,   -- canonical slug / id
    target_title TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, target_type, target_id)
);
CREATE INDEX IF NOT EXISTS idx_user_follows_lookup ON user_follows(user_id, target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_user_follows_target ON user_follows(target_type, target_id);

CREATE TABLE IF NOT EXISTS user_notification_preferences (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    news_alerts INTEGER NOT NULL DEFAULT 1,
    tender_alerts INTEGER NOT NULL DEFAULT 1,
    job_alerts INTEGER NOT NULL DEFAULT 1,
    rental_alerts INTEGER NOT NULL DEFAULT 1,
    breaking_alerts INTEGER NOT NULL DEFAULT 1,
    followed_content_alerts INTEGER NOT NULL DEFAULT 1,
    telegram_enabled INTEGER NOT NULL DEFAULT 1,
    viber_enabled INTEGER NOT NULL DEFAULT 1,
    frequency TEXT NOT NULL DEFAULT 'instant', -- 'instant', 'digest'
    quiet_hours_enabled INTEGER NOT NULL DEFAULT 0,
    quiet_hours_start TEXT DEFAULT '23:00',
    quiet_hours_end TEXT DEFAULT '07:00',
    timezone TEXT NOT NULL DEFAULT 'Indian/Maldives',
    is_paused INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS channel_link_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT UNIQUE NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel TEXT NOT NULL, -- 'telegram', 'viber'
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Stable cross-channel identity registry. Unlinked bot users have NULL user_id.
CREATE TABLE IF NOT EXISTS user_identities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    provider TEXT NOT NULL CHECK (provider IN ('telegram', 'viber')),
    provider_user_id TEXT NOT NULL,
    provider_username TEXT,
    display_name TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    first_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, provider_user_id)
);
CREATE INDEX IF NOT EXISTS idx_user_identities_user ON user_identities(user_id);
CREATE INDEX IF NOT EXISTS idx_user_identities_provider_seen ON user_identities(provider, last_seen_at);
CREATE INDEX IF NOT EXISTS idx_channel_link_tokens_token ON channel_link_tokens(token);
CREATE INDEX IF NOT EXISTS idx_channel_link_tokens_user ON channel_link_tokens(user_id, channel);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_key TEXT NOT NULL,
    content_type TEXT NOT NULL, -- 'news', 'tender', 'job', 'obituary'
    content_id TEXT NOT NULL,
    event_version INTEGER NOT NULL DEFAULT 1,
    reason TEXT NOT NULL, -- 'breaking', 'followed_story', 'followed_topic', 'followed_section', 'followed_source'
    reason_target TEXT,
    title TEXT NOT NULL,
    summary TEXT,
    url TEXT,
    is_urgent INTEGER NOT NULL DEFAULT 0,
    frequency TEXT NOT NULL DEFAULT 'instant', -- 'instant', 'digest'
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, event_key)
);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notifications_event ON notifications(event_key);

CREATE TABLE IF NOT EXISTS notification_deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    notification_id INTEGER NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    channel TEXT NOT NULL, -- 'telegram', 'viber'
    destination TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'delivered', 'failed', 'dead_letter', 'queued_quiet_hours', 'queued_digest', 'claiming'
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    claim_token TEXT,
    claimed_at TIMESTAMP,
    error_message TEXT,
    last_attempt_at TIMESTAMP,
    delivered_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(notification_id, channel)
);
CREATE INDEX IF NOT EXISTS idx_deliveries_status ON notification_deliveries(status, channel);
CREATE INDEX IF NOT EXISTS idx_deliveries_user ON notification_deliveries(user_id);

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
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    entity_id INTEGER REFERENCES entities(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    title_en TEXT,
    agency TEXT NOT NULL,
    agency_name_en TEXT,
    discipline TEXT NOT NULL DEFAULT 'Other',
    location TEXT DEFAULT "Male'",
    salary_raw TEXT,
    deadline_iso TEXT,
    deadline_at TIMESTAMP,
    published_date TEXT,
    posted_date TEXT,
    posted_time TEXT,
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

