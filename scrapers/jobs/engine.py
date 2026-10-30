"""
Jobs Scraper Engine.
Orchestrates Gazette and National Careers Service (MyCareer.mv) job scrapers.
Pure scraper module: returns normalized job dicts without database writes.
"""
from __future__ import annotations

import logging
from typing import Any

from scrapers.jobs.gazette import fetch_gazette_job_vacancies
from scrapers.jobs.mycareer import fetch_mycareer_jobs

logger = logging.getLogger("khulaasaa.jobs.engine")


def fetch_all_jobs(pages: int = 1) -> list[dict[str, Any]]:
    """Fetch and enrich job listings from all configured job sources without DB persistence."""
    fetched = fetch_gazette_job_vacancies(pages=pages)
    try:
        mycareer_jobs = fetch_mycareer_jobs()
        fetched.extend(mycareer_jobs)
    except Exception as e:
        logger.warning("Error fetching MyCareer jobs: %s", e)
    return fetched
