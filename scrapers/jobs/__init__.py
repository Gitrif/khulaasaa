"""
Khulaasaa Jobs Scraper Package.
Provides pure job scraping, enrichment, classification, and translation functions.
Database persistence and alert dispatch live in services.ingestion.jobs_ingestion.
"""
from __future__ import annotations

from scrapers.jobs.classifier import (
    CONTEXT_TAXONOMY,
    DISCIPLINE_TAXONOMY,
    JOB_DISCIPLINES,
    JOB_TITLE_PHRASE_TRANSLATIONS,
    ROLE_TAXONOMY,
    classify_job_discipline,
    translate_job_title,
)
from scrapers.jobs.engine import fetch_all_jobs
from scrapers.jobs.gazette import (
    GAZETTE_BASE,
    JOB_LISTING_URL,
    batch_enrich_gazette_jobs,
    clean_currency_amount,
    enrich_gazette_job_notice,
    extract_clean_location,
    fetch_gazette_job_vacancies,
    format_salary_package,
)
from scrapers.jobs.mycareer import fetch_mycareer_jobs

__all__ = [
    "CONTEXT_TAXONOMY",
    "DISCIPLINE_TAXONOMY",
    "GAZETTE_BASE",
    "JOB_DISCIPLINES",
    "JOB_LISTING_URL",
    "JOB_TITLE_PHRASE_TRANSLATIONS",
    "ROLE_TAXONOMY",
    "batch_enrich_gazette_jobs",
    "classify_job_discipline",
    "clean_currency_amount",
    "enrich_gazette_job_notice",
    "extract_clean_location",
    "fetch_all_jobs",
    "fetch_gazette_job_vacancies",
    "fetch_mycareer_jobs",
    "format_salary_package",
    "translate_job_title",
]
