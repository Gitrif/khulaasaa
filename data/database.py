"""
Khulaasaa Core Database Gateway & Repositories Facade.
Provides backward-compatible imports for all modularized repositories.
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Generator, Optional

from data.connection import DEFAULT_DB_PATH, get_db, get_db_path
from data.init_db import init_db
from data.utils import slugify, detect_entity_type
from data.taxonomy import ATOLL_TAXONOMY, extract_atoll_and_island
from data.repos.entities import resolve_or_create_entity, list_entities

# Re-exported Domain Repositories (< 500 lines per module)
from data.repos.bids import (
    upsert_bid,
    query_bids,
    get_bids_filter_options,
    get_agency_portal_statistics,
)
from data.repos.bid_milestones import (
    extract_milestones_and_venues,
    purge_expired_bids,
)
from data.repos.subscribers import (
    baseline_mark_existing_alerts_for_subscriber,
    register_or_update_telegram_subscriber,
    is_subscriber_paid,
    update_telegram_subscriber_plan,
    get_telegram_subscribers,
    get_telegram_subscriber,
    register_or_update_viber_subscriber,
    is_viber_subscriber_paid,
    update_viber_subscriber_plan,
    get_viber_subscribers,
    get_viber_subscriber,
    unsubscribe_viber_subscriber,
)
from data.repos.ads import (
    get_active_sponsored_ad,
    record_ad_impression,
    list_sponsored_ads,
    upsert_sponsored_ad,
    extend_sponsored_ad,
    get_sponsored_ad,
    toggle_sponsored_ad,
    delete_sponsored_ad,
    save_hooks85_subscription,
    list_hooks85_subscriptions,
)
from data.repos.obituaries import (
    parse_obituary_text,
    upsert_scraped_obituary,
    list_obituaries,
    get_obituary,
    get_obituary_by_slug,
    upsert_obituary,
    toggle_obituary,
    delete_obituary,
    purge_expired_obituaries,
)
from data.repos.users import (
    hash_password,
    verify_password,
    create_user,
    authenticate_user,
    get_user_by_id,
    get_user_by_email,
    get_user_by_telegram_id,
    get_user_by_viber_id,
    update_user_plan,
    update_user_job_alerts,
    create_user_session,
    get_user_from_session,
    delete_user_session,
)
from data.repos.cvs import (
    save_user_cv,
    get_user_cv,
)
from data.repos.company_profiles import (
    save_company_profile,
    get_company_profile,
)
from data.repos.jobs import (
    upsert_job,
    query_jobs,
    get_job_disciplines,
    get_job_by_id,
    STANDARD_LANGUAGES,
    LANGUAGE_PROFICIENCIES,
    EDUCATION_LEVELS,
    STANDARD_INSTITUTIONS,
)
from data.repos.stories import (
    upsert_article,
    query_articles,
)

logger = logging.getLogger(__name__)
