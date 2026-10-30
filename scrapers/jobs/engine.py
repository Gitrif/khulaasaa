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
    fetched: list[dict[str, Any]] = []
    try:
        gazette_jobs = fetch_gazette_job_vacancies(pages=pages)
        if gazette_jobs:
            fetched.extend(gazette_jobs)
    except Exception as exc:
        logger.warning("Error fetching Gazette jobs: %s", exc)

    try:
        mycareer_jobs = fetch_mycareer_jobs()
        if mycareer_jobs:
            fetched.extend(mycareer_jobs)
    except Exception as exc:
        logger.warning("Error fetching MyCareer jobs: %s", exc)
    return fetched
