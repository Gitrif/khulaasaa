"""
Gazette Job Vacancy Scraper & Detail Enricher (gazette.gov.mv/iulaan?type=vazeefaa).
Pure scraper/parser module: fetches and enriches job notices without database writes or alerts.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import logging
import re
from typing import Any, Optional

from bs4 import BeautifulSoup
import requests

from data.taxonomy import extract_atoll_and_island
from scrapers.jobs.classifier import classify_job_discipline, translate_job_title
from scrapers.tenders.gazette import (
    notice_id_from_url,
    parse_deadline,
    parse_published,
)
from scrapers.translator import (
    _translate_phrase_elements,
    clean_residual_thaana,
    is_dhivehi,
    translate_agency,
)

logger = logging.getLogger("khulaasaa.jobs.gazette")

GAZETTE_BASE = "https://gazette.gov.mv"
JOB_LISTING_URL = f"{GAZETTE_BASE}/iulaan?type=vazeefaa"


def clean_currency_amount(text: Optional[str]) -> Optional[str]:
    """Extract standard numeric amount like 16,975 or 11,620.00 or 7,700."""
    if not text:
        return None
    m = re.search(r"([0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)", text)
    if not m:
        return None
    raw = m.group(1)
    try:
        val = float(raw.replace(",", ""))
        if "." in raw:
            return f"{val:,.2f}"
        return f"{int(val):,}"
    except Exception:
        return raw


def format_salary_package(salary_str: Optional[str], allowance_str: Optional[str] = None) -> str:
    """Format clear, human-readable Maldivian remuneration string."""
    if not salary_str:
        return "Pay not listed"

    sal = clean_currency_amount(salary_str)
    if not sal:
        return "Pay not listed"

    is_daily = "ދުވާލަކަށް" in salary_str or "daily" in salary_str.lower()
    period = "day" if is_daily else "mo"

    allow = clean_currency_amount(allowance_str) if allowance_str else None
    if allow:
        return f"MVR {sal} (+ MVR {allow} Allowance)"
    return f"MVR {sal} / {period}"


def extract_clean_location(workplace_raw: Optional[str]) -> str:
    """Resolve specific atoll and island location from workplace text."""
    if not workplace_raw:
        return "Male'"

    w_lower = workplace_raw.lower()
    if "ހުޅުމާލެ" in workplace_raw or "hulhumale" in w_lower:
        return "Hulhumale'"
    if "ވިލިމާލެ" in workplace_raw or "vilimale" in w_lower:
        return "Vilimale'"

    geo = extract_atoll_and_island(workplace_raw)
    atoll = geo.get("atoll_code")
    island_dv = geo.get("island_name")

    island_en = clean_residual_thaana(_translate_phrase_elements(island_dv or "")).strip() if island_dv else ""

    if atoll and atoll != "K-MALE":
        loc_island = island_en if island_en else (island_dv or "")
        return f"{atoll}. {loc_island}".strip(". ")
    if island_en and island_en.lower() != "male":
        return island_en
    return "Male'"


def enrich_gazette_job_notice(notice_id: str, timeout: int = 8) -> dict[str, Any]:
    """Fetch official print view for a single gazette vacancy notice."""
    url = f"https://gazette.gov.mv/iulaan/print/{notice_id}"
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=timeout,
        )
        if resp.status_code != 200:
            return {}

        soup = BeautifulSoup(resp.text, "html.parser")
        raw_sal, raw_allow, raw_work = "", "", ""

        for tr in soup.select("table tr"):
            tds = [td.get_text(" ", strip=True) for td in tr.select("td, th")]
            if len(tds) >= 2:
                key = tds[0].strip(": ")
                val = " ".join(tds[1:]).strip(": ")
                if ("މުސާރަ" in key or "އުޖޫރަ" in key) and not raw_sal:
                    raw_sal = val
                elif "އެލަވަންސް" in key and not raw_allow:
                    raw_allow = val
                elif "ވަޒީފާ އަދާކުރަން ޖެހޭ ތަން" in key and not raw_work:
                    raw_work = val

        return {
            "notice_id": notice_id,
            "salary_raw": format_salary_package(raw_sal, raw_allow),
            "location": extract_clean_location(raw_work),
            "workplace": raw_work,
        }
    except Exception as exc:
        logger.debug("Failed to enrich job notice %s: %s", notice_id, exc)
        return {}


def batch_enrich_gazette_jobs(jobs: list[dict[str, Any]], max_workers: int = 5) -> list[dict[str, Any]]:
    """Concurrently enrich a list of gazette jobs with accurate salary and location data."""
    gazette_jobs = [j for j in jobs if j.get("source_portal") == "gazette.gov.mv" and j.get("notice_id", "").isdigit()]
    if not gazette_jobs:
        return jobs

    notice_ids = [j["notice_id"] for j in gazette_jobs]
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        enriched_results = list(executor.map(enrich_gazette_job_notice, notice_ids))

    enriched_map = {r["notice_id"]: r for r in enriched_results if r and "salary_raw" in r}

    for j in jobs:
        nid = j.get("notice_id")
        if nid in enriched_map:
            enr = enriched_map[nid]
            if enr.get("salary_raw") and enr["salary_raw"] != "Pay not listed":
                j["salary_raw"] = enr["salary_raw"]
            if enr.get("location"):
                j["location"] = enr["location"]
            if enr.get("workplace"):
                j["workplace"] = enr["workplace"]

    return jobs


def fetch_gazette_job_vacancies(pages: int = 1, session: Optional[requests.Session] = None) -> list[dict[str, Any]]:
    """Fetch recent live job vacancies from gazette.gov.mv."""
    session = session or requests.Session()
    session.headers.setdefault(
        "User-Agent",
        "KhulaasaaJobs/1.0 (+https://khulaasaa.tech/jobs; contact@khulaasaa.tech)",
    )

    jobs: list[dict[str, Any]] = []

    for page in range(1, pages + 1):
        url = f"{JOB_LISTING_URL}&page={page}"
        try:
            resp = session.get(url, timeout=15)
            if resp.status_code != 200:
                logger.warning("Gazette returned HTTP %s for page %s", resp.status_code, page)
                continue
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select(".items-list .items")
            for card in cards:
                title_el = card.select_one(".iulaan-title")
                if not title_el:
                    continue
                raw_title = title_el.get_text(strip=True)
                href = title_el.get("href", "")
                notice_id = notice_id_from_url(href) or f"gazette-job-{abs(hash(raw_title))}"

                office_el = card.select_one(".iulaan-office")
                agency_raw = office_el.get_text(strip=True) if office_el else "Government Agency"

                published_raw = None
                deadline_iso = None
                for info in card.select(".info"):
                    itxt = info.get_text(" ", strip=True)
                    if "ތާރީޚު" in itxt or "Published" in itxt:
                        published_raw = parse_published(itxt)
                    elif "ސުންގަޑި" in itxt or "Deadline" in itxt:
                        deadline_iso = parse_deadline(itxt)

                title_en = raw_title
                agency_en = agency_raw
                if is_dhivehi(raw_title):
                    try:
                        title_en = translate_job_title(raw_title)
                    except Exception:
                        title_en = raw_title

                if is_dhivehi(agency_raw):
                    try:
                        translated_ag = translate_agency(agency_raw)
                        agency_en = clean_residual_thaana(translated_ag) or agency_raw
                    except Exception:
                        agency_en = agency_raw

                if not deadline_iso:
                    deadline_iso = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%dT14:00:00")

                discipline = classify_job_discipline(f"{raw_title} {title_en}", f"{agency_raw} {agency_en}")
                source_url = f"{GAZETTE_BASE}/iulaan/{notice_id}" if href.startswith("/") or notice_id.isdigit() else href

                jobs.append({
                    "notice_id": str(notice_id),
                    "title": raw_title,
                    "title_en": title_en,
                    "agency": agency_raw,
                    "agency_name_en": agency_en,
                    "discipline": discipline,
                    "location": "Male'",
                    "salary_raw": "Civil Service Remuneration Matrix",
                    "deadline_iso": deadline_iso,
                    "published_date": published_raw or datetime.now().strftime("%Y-%m-%d"),
                    "source_url": source_url,
                    "source_portal": "gazette.gov.mv",
                    "is_active": 1,
                })
        except Exception as exc:
            logger.error("Failed to fetch gazette jobs page %s: %s", page, exc)

    try:
        jobs = batch_enrich_gazette_jobs(jobs)
    except Exception as exc:
        logger.warning("Error enriching gazette jobs: %s", exc)

    return jobs
