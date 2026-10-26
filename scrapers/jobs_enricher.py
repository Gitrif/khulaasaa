"""
Gazette Job Vacancy Detail & Salary Enricher for Khulaasaa Jobs.
Fetches official Gazette print views to extract actual remuneration,
allowances, and specific workplace locations across Maldivian atolls.
"""
from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

from data.taxonomy import extract_atoll_and_island
from scrapers.translator import _translate_phrase_elements, clean_residual_thaana

logger = logging.getLogger("khulaasaa.jobs.enricher")


def clean_currency_amount(text: Optional[str]) -> Optional[str]:
    """Extract standard numeric amount like 16,975 or 11,620.00 or 7,700."""
    if not text:
        return None
    # Match numbers with existing commas first (e.g. 16,975), or contiguous digit strings (e.g. 11620.00 or 7700)
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
