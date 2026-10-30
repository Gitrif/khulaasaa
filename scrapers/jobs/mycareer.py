"""
National Careers Service Portal Scraper (mycareer.gov.mv).
Pure scraper module: fetches and parses job listings without database writes.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from bs4 import BeautifulSoup
import requests

from scrapers.jobs.classifier import classify_job_discipline

logger = logging.getLogger("khulaasaa.jobs.mycareer")


def fetch_mycareer_jobs() -> list[dict[str, Any]]:
    """Scrape live vacancies from the official National Careers Service portal (mycareer.gov.mv)."""
    url = "https://mycareer.gov.mv/en/jobs"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    jobs = []
    try:
        req = requests.get(url, headers=headers, timeout=12)
        if req.status_code != 200:
            return jobs
        soup = BeautifulSoup(req.text, "html.parser")
        job_links = soup.select("a[href*='/en/jobs/']")
        seen_slugs = set()

        for a in job_links:
            href = a.get("href", "")
            if href.rstrip("/") == "https://mycareer.gov.mv/en/jobs":
                continue
            slug = href.split("/jobs/")[-1]
            if not slug or slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            card_text = a.get_text("\n", strip=True)
            lines = [l.strip() for l in card_text.splitlines() if l.strip()]
            clean_lines = [l for l in lines if l.lower() not in ("new", "expiring soon", "urgent", "featured")]

            title = clean_lines[0] if clean_lines else slug.replace("-", " ").title()
            employer = clean_lines[1] if len(clean_lines) > 1 else "Maldivian Employer"

            salary = "Competitive Remuneration"
            location = "Male'"
            for l in clean_lines[2:]:
                if "MVR" in l or "Negotiable" in l or "Salary" in l:
                    salary = l
                elif any(loc in l for loc in ("City", "Hulhumale", "Male", "Addu", "Atoll")):
                    location = l

            discipline = classify_job_discipline(title, employer)
            deadline_iso = (datetime.now() + timedelta(days=12)).strftime("%Y-%m-%dT14:00:00")

            jobs.append({
                "notice_id": f"mycareer-{slug}",
                "title": title,
                "title_en": title,
                "agency": employer,
                "agency_name_en": employer,
                "discipline": discipline,
                "location": location,
                "salary_raw": salary,
                "deadline_iso": deadline_iso,
                "published_date": datetime.now().strftime("%Y-%m-%d"),
                "source_url": href,
                "source_portal": "mycareer.gov.mv",
                "is_active": 1,
            })
    except Exception as exc:
        logger.warning("Failed to fetch MyCareer jobs: %s", exc)

    return jobs
