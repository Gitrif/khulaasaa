"""
Job vacancy scraper and synchronization engine for Khulaasaa Jobs.

Supports:
1. Scraping official government, council, and SOE job vacancies from gazette.gov.mv/iulaan?type=vazeefaa.
2. Intelligent discipline classification across Maldivian employment sectors.
3. Translating / normalising agency and job titles.
4. Auto-dispatching job alerts to subscribed users and Telegram alerts.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Optional
import sqlite3
import time
import requests
from bs4 import BeautifulSoup

from data.database import (
    get_db,
    upsert_job,
    query_jobs,
    get_job_disciplines,
)

logger = logging.getLogger("khulaasaa.jobs")

GAZETTE_BASE = "https://gazette.gov.mv"
JOB_LISTING_URL = f"{GAZETTE_BASE}/iulaan?type=vazeefaa"

# Maldivian job market disciplines
JOB_DISCIPLINES = [
    "Administration & Management",
    "IT, Tech & Communications",
    "Medical & Healthcare",
    "Construction, Architecture & Engineering",
    "Finance, Accounting & Procurement",
    "Education & Teaching",
    "Hospitality, Tourism & Resorts",
    "Aviation",
    "Land Transport",
    "Sea Transport",
    "Customer Service, Retail & Operations",
    "Legal & Human Resources",
    "Other",
]

# Primary role-specific taxonomy evaluated directly against the JOB TITLE.
# Job seekers care first and foremost about their actual profession:
# e.g., Procurement in a pharmacy/hospital is Procurement, not Medicine.
# e.g., Doctor/Nurse at a resort is Medical, not Hospitality.
# e.g., Driver at a ministry is Land Transport, not Administration.
ROLE_TAXONOMY: dict[str, list[str]] = {
    "Medical & Healthcare": [
        "doctor", "medical officer", "specialist medical", "general practitioner", "physician",
        "surgeon", "nurse", "registered nurse", "clinical nurse", "staff nurse", "nursing",
        "dentist", "dental officer", "dental surgeon", "radiographer", "pharmacist",
        "pharmacy assistant", "paramedic", "physiotherapist", "lab technician",
        "laboratory technician", "technologist", "laboratory", "dietitian", "psychologist", "phlebotomist", "health officer",
        "community health", "medical",
        "ޑޮކްޓަރ", "ނަރުސް", "ޞިއްޙީ", "ފާމަސިސްޓް", "ދަތުގެ ޑޮކްޓަރ", "ލެބޯޓްރީ ޓެކްނިޝަން", "ލެބޯރެޓަރީ", "ލެބޯޓްރީ",
    ],
    "Finance, Accounting & Procurement": [
        "procurement", "purchasing", "supply chain", "buyer", "tender officer", "bid officer",
        "accountant", "accounting", "accounts officer", "audit", "auditor", "financial analyst",
        "finance officer", "tax officer", "billing officer", "budget officer", "credit control",
        "treasury", "payroll", "cost controller", "chief financial officer", "cfo", "banker",
        "loan officer", "teller", "billing", "finance",
        "އެކައުންޓެންޓް", "ފައިނޭންސް", "ޕްރޮކިއުމަންޓް", "އޮޑިޓަރ", "ބިލިންގ", "ފައިސާ", "ބަޖެޓް",
    ],
    "IT, Tech & Communications": [
        "software", "programmer", "developer", "web developer", "network engineer",
        "network administrator", "cybersecurity", "cyber security", "it officer", "it technician",
        "computer programmer", "database administrator", "systems administrator",
        "hardware technician", "devops", "fullstack", "frontend", "backend", "ui/ux",
        "security engineer", "data analyst", "data scientist", "solutions architect", "network",
        "it support", "computer",
        "ކޮމްޕިއުޓަރ", "ސޮފްޓްވެއަރ", "އައިޓީ", "ނެޓްވޯކް",
    ],
    "Sea Transport": [
        "boat captain", "launch captain", "ferry captain", "dhoni captain", "launch driver",
        "boat crew", "deckhand", "sailor", "marine crew", "marine engineer", "marine mechanic",
        "coxswain", "boatman", "speedboat captain", "speedboat driver", "seaman",
        "vessel traffic", "boat operator", "diver", "diving instructor", "marine pilot",
        "boat", "vessel", "maritime", "ferry", "launch",
        "ކެޕްޓަން", "ފަޅުވެރި", "ލޯންޗު", "ދޯނި", "ފެރީ", "މެރިން", "ކަނޑުދަތުރު",
    ],
    "Aviation": [
        "pilot", "first officer", "flight attendant", "cabin crew", "air traffic controller",
        "avionics", "ground handling", "ramp agent", "ramp coordinator", "baggage handler", "seaplane pilot",
        "flight dispatcher", "aviation security", "flight operations", "aircraft maintenance",
        "aeronautical", "airport manager", "airport coordinator", "airport operations", "airport", "ramp",
        "aircraft", "aviation", "airline", "seaplane",
        "ޕައިލެޓް", "ފްލައިޓް", "މަތިންދާބޯޓު", "ސީޕްލޭން", "ކެބިން ކްރޫ", "އޭވިއޭޝަން", "އެއާޕޯޓް",
    ],
    "Land Transport": [
        "bus driver", "taxi driver", "van driver", "car driver", "truck driver", "heavy vehicle",
        "lorry driver", "chauffeur", "driver", "fleet dispatcher", "automotive technician",
        "vehicle mechanic", "courier rider", "delivery rider", "traffic warden",
        "road transport", "transport officer",
        "ޑްރައިވަރ", "ޑްރައިވަރު", "ބަސް ޑްރައިވަރ", "ވެހިކަލް", "ކާރު ޑްރައިވަރ", "ޓެކްސީ", "ދަތުރުފަތުރު",
    ],
    "Education & Teaching": [
        "teacher", "lecturer", "instructor", "principal", "leading teacher", "tutor",
        "academic", "curriculum developer", "professor", "educator", "teaching",
        "ކިޔަވައިދިނުން", "މުދައްރިސް", "ޓީޗަރ", "ޕްރިންސިޕަލް",
    ],
    "Construction, Architecture & Engineering": [
        "civil engineer", "architect", "structural engineer", "mechanical engineer",
        "electrical engineer", "surveyor", "quantity surveyor", "draftsman", "site supervisor",
        "construction supervisor", "electrician", "plumber", "mason", "carpenter", "welder",
        "building inspector", "power systems", "engineer", "construction",
        "އިންޖިނޭރު", "އިލެކްޓްރީޝަން", "ޢިމާރާތް", "މަރާމާތު", "ވަޑާން",
    ],
    "Hospitality, Tourism & Resorts": [
        "guest relations", "concierge", "butler", "villa host", "front office", "f&b",
        "food and beverage", "chef", "cook", "waiter", "waitress", "bartender",
        "housekeeping", "room attendant", "spa therapist", "sommelier", "kitchen steward",
        "tour guide", "resort manager", "hotelier", "resort", "hotel",
        "ކައްކާ", "ވެއިޓަރ", "ގެސްޓް ރިލޭޝަންސް", "ރިސޯޓް",
    ],
    "Customer Service, Retail & Operations": [
        "customer service", "cashier", "retail assistant", "shop assistant", "storekeeper",
        "sales representative", "sales officer", "counter staff", "call center",
        "client service", "supermart", "store supervisor", "shop supervisor", "merchandiser",
        "retail",
        "ފިހާރަ", "ކަސްޓަމަރ", "ސޭލްސް",
    ],
    "Legal & Human Resources": [
        "legal", "lawyer", "counsel", "advocate", "attorney", "prosecutor", "hr officer",
        "human resource", "talent acquisition", "recruitment", "labour relations",
        "ޤާނޫނީ", "ވަކީލު",
    ],
    "Administration & Management": [
        "administrative", "admin officer", "administrative officer", "secretary",
        "executive assistant", "clerk", "council assistant", "receptionist",
        "coordinator", "supervisor", "manager", "director",
        "މަޤާމް", "ސެކްރެޓަރީ", "އެސިސްޓެންޓް", "ޑިރެކްޓަރ",
    ],
}

# Secondary context taxonomy: used ONLY when the job title itself is generic
# (e.g. "Officer", "Assistant", "Specialist", "Staff", "Consultant") and does not convey a profession.
CONTEXT_TAXONOMY: dict[str, list[str]] = {
    "Medical & Healthcare": ["hospital", "clinic", "health", "pharmaceutical", "igmh", "medical", "ހޮސްޕިޓަލް"],
    "Hospitality, Tourism & Resorts": ["resort", "hotel", "villas", "tourism", "hospitality", "ރިސޯޓް"],
    "Aviation": ["airline", "aviation", "airports", "macl", "air traffic", "seaplane", "tma", "maldivian aero"],
    "Sea Transport": ["mtcc ferry", "ferry network", "marine transport", "ports authority", "harbour", "shipping"],
    "Land Transport": ["bus operations", "transport ministry", "road transport", "taxi fleet"],
    "Finance, Accounting & Procurement": ["bank", "mira", "bml", "mma", "pension office", "finance ministry", "auditor general"],
    "Construction, Architecture & Engineering": ["construction", "infrastructure", "stelco", "fenaka", "mwsc", "hdc"],
    "Education & Teaching": ["school", "college", "university", "mnu", "islamic university", "education ministry", "polytechnic"],
}

# Backward compatibility alias
DISCIPLINE_TAXONOMY = ROLE_TAXONOMY


def classify_job_discipline(title: str, agency: str = "", body: str = "") -> str:
    """
    Classify job into a standardized Maldivian employment sector.
    
    IMPORTANT HIERARCHY:
    1. The applicant is seeking a specific profession/role — the Job Title is evaluated FIRST.
       e.g., Procurement in a pharmacy/hospital -> Finance, Accounting & Procurement.
       e.g., Doctor or Nurse in a luxury resort -> Medical & Healthcare.
       e.g., Van Driver in a Ministry -> Land Transport.
       e.g., Speedboat Captain at a resort -> Sea Transport.
    2. The hiring employer/agency/body is ONLY consulted if the title is generic
       (e.g., "Specialist", "Officer", "Staff", "Assistant") and does not specify a trade.
    """
    clean_title = (title or "").lower().strip()
    clean_agency = (agency or "").lower().strip()
    clean_body = (body or "").lower().strip()

    # Pass 1: Match against the Job Title directly (sorted by keyword length descending)
    for disc, keywords in ROLE_TAXONOMY.items():
        sorted_kws = sorted(keywords, key=len, reverse=True)
        for kw in sorted_kws:
            pattern = r"(?:^|\W)" + re.escape(kw) + r"(?:$|\W)"
            if re.search(pattern, clean_title) or kw in clean_title:
                return disc

    # Pass 2: Fallback for generic titles — consult agency & job context
    combined_context = f"{clean_agency} {clean_body}"
    for disc, keywords in CONTEXT_TAXONOMY.items():
        sorted_kws = sorted(keywords, key=len, reverse=True)
        for kw in sorted_kws:
            pattern = r"(?:^|\W)" + re.escape(kw) + r"(?:$|\W)"
            if re.search(pattern, combined_context) or kw in combined_context:
                return disc

    # Pass 3: Final fallback
    if "officer" in clean_title or "admin" in clean_title or "އޮފިސަރ" in clean_title:
        return "Administration & Management"
    return "Other"


JOB_TITLE_PHRASE_TRANSLATIONS: list[tuple[str, str]] = [
    ("ކޯޓު އެޑްމިނިސްޓްރޭޓަރ", "Court Administrator"),
    ("ކޯޓު އެޑްމިނިސްޓްރޭޓަރު", "Court Administrator"),
    ("ކޯޓު", "Court"),
    ("ވަޒީފާގެ ފުރުޞަތު -", "Job Vacancy -"),
    ("ވަޒީފާގެ ފުރުސަތު -", "Job Vacancy -"),
    ("ވަޒީފާގެ ފުރުޞަތު", "Job Vacancy:"),
    ("ވަޒީފާގެ ފުރުސަތު", "Job Vacancy:"),
    ("ސީނިއަރ", "Senior"),
    ("ޖޫނިއަރ", "Junior"),
    ("ހިއުމަން ރިސޯސް", "Human Resources"),
    ("އިންފްރާސްޓްރަކްޗަރ", "Infrastructure"),
    ("ޑިވެލޮޕްމަންޓް", "Development"),
    ("ސެކްޝަން", "Section"),
    ("މެނޭޖްމަންޓް", "Management"),
    ("ފެސިލިޓޭޝަން", "Facilitation"),
    ("ސެންޓަރ", "Center"),
    ("ކޮންޓްރެކްޓް", "Contract"),
    ("ޕްރޮޖެކްޓް", "Project"),
    ("އެސިސްޓެންޓް", "Assistant"),
    ("އޮފިސަރ", "Officer"),
    ("މެނޭޖަރ", "Manager"),
    ("ޑިރެކްޓަރ", "Director"),
    ("ކޯޑިނޭޓަރ", "Coordinator"),
    ("ސުޕަވައިޒަރ", "Supervisor"),
    ("އެޑްމިނިސްޓްރޭޓަރ", "Administrator"),
    ("ޑްރައިވަރ", "Driver"),
    ("ޑްރައިވަރު", "Driver"),
    ("ކެޕްޓަން", "Captain"),
    ("ފަޅުވެރި", "Deckhand / Crew"),
    ("ޓީޗަރ", "Teacher"),
    ("މުދައްރިސް", "Teacher"),
    ("ޑޮކްޓަރ", "Doctor"),
    ("ނަރުސް", "Nurse"),
    ("ފާމަސިސްޓް", "Pharmacist"),
    ("އެކައުންޓެންޓް", "Accountant"),
    ("އިންޖިނޭރު", "Engineer"),
    ("އިލެކްޓްރީޝަން", "Electrician"),
    ("ސެކިއުރިޓީ", "Security"),
    ("ހެލްތް", "Health"),
    ("ޞިއްޙީ", "Health"),
    ("ޓެކްސް", "Tax"),
    ("ކޮމްޕިއުޓަރ", "Computer"),
    ("ޕްރޮގްރާމަރ", "Programmer"),
    ("ކައުންސިލް", "Council"),
    ("ޔުނިޓް", "Unit"),
    ("ގްރޭޑް", "Grade"),
    ("މަޤާމް", "Position"),
    ("ވަކީލު", "Legal Counsel"),
    ("ޤާނޫނީ", "Legal"),
    ("ފައިނޭންސް", "Finance"),
    ("އޮޑިޓަރ", "Auditor"),
    ("ލެބޯރެޓަރީ", "Laboratory"),
    ("ލެބޯޓްރީ", "Laboratory"),
    ("ޓެކްނޯލޮޖިސްޓް", "Technologist"),
    ("ސްޕޯޓްސް", "Sports"),
    ("ޕްރިންސިޕަލް", "Principal"),
    ("ސްކޫލް", "School"),
    ("މިސްކިތް", "Mosque"),
    ("މިސްކިތު", "Mosque"),
    ("އިމާމު", "Imam"),
    ("މުދިމު", "Mudhim"),
]


def translate_job_title(title_dv: str) -> str:
    """Translate Maldivian civil service & corporate job titles into English without tender prefixes."""
    from scrapers.translator import clean_dhivehi_markers, clean_residual_thaana
    text = clean_dhivehi_markers(title_dv)
    for dv, en in JOB_TITLE_PHRASE_TRANSLATIONS:
        text = text.replace(dv, en)
    cleaned = clean_residual_thaana(text)
    return cleaned if cleaned else title_dv


def fetch_gazette_job_vacancies(pages: int = 1, session: Optional[requests.Session] = None) -> list[dict[str, Any]]:
    """Fetch recent live job vacancies from gazette.gov.mv."""
    from scrapers.gazette import parse_published, parse_deadline, notice_id_from_url
    from scrapers.translator import is_dhivehi, translate_agency, clean_residual_thaana

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
                logger.warning(f"Gazette returned HTTP {resp.status_code} for page {page}")
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

                # Parse dates
                published_raw = None
                deadline_iso = None
                for info in card.select(".info"):
                    itxt = info.get_text(" ", strip=True)
                    if "ތާރީޚު" in itxt or "Published" in itxt:
                        published_raw = parse_published(itxt)
                    elif "ސުންގަޑި" in itxt or "Deadline" in itxt:
                        deadline_iso = parse_deadline(itxt)

                # Translation / Normalization specifically for Employment Vacancies
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

                # Fallback deadline if missing (7 days from today)
                if not deadline_iso:
                    from datetime import timedelta
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
            logger.error(f"Failed to fetch gazette jobs page {page}: {exc}")

    try:
        from scrapers.jobs_enricher import batch_enrich_gazette_jobs
        jobs = batch_enrich_gazette_jobs(jobs)
    except Exception as exc:
        logger.warning(f"Error enriching gazette jobs: {exc}")

    return jobs


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
            from datetime import timedelta
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
        logger.warning(f"Failed to fetch MyCareer jobs: {exc}")

    return jobs


def sync_jobs(conn: Optional[Any] = None, pages: int = 1, trigger_alerts: bool = True) -> dict[str, Any]:
    """Sync recent jobs from Gazette & MyCareer to database and trigger subscriber alerts."""
    from alerts.telegram import dispatch_job_alerts
    from data.database import log_db_error, get_db

    # Fetch network data outside the database lock
    fetched = fetch_gazette_job_vacancies(pages=pages)
    try:
        mycareer_jobs = fetch_mycareer_jobs()
        fetched.extend(mycareer_jobs)
    except Exception as e:
        logger.warning(f"Error fetching MyCareer jobs: {e}")

    new_jobs = updated_jobs = alerts_sent = 0

    def _persist(db_conn):
        nonlocal new_jobs, updated_jobs, alerts_sent
        for j in fetched:
            notice_id = j["notice_id"]
            existing = None
            for attempt in range(4):
                try:
                    db_conn.execute("SAVEPOINT job_sp;")
                    existing = db_conn.execute("SELECT id FROM jobs WHERE notice_id = ?;", (notice_id,)).fetchone()
                    upsert_job(db_conn, j)
                    db_conn.execute("RELEASE SAVEPOINT job_sp;")
                    break
                except sqlite3.OperationalError as op_err:
                    try:
                        db_conn.execute("ROLLBACK TO SAVEPOINT job_sp;")
                    except Exception: pass
                    if "locked" in str(op_err).lower() and attempt < 3:
                        time.sleep(0.3 * (attempt + 1))
                        continue
                    log_db_error(logger, f"process_job_{notice_id}", "scrapers.jobs", op_err)
                    break
                except Exception as exc:
                    try:
                        db_conn.execute("ROLLBACK TO SAVEPOINT job_sp;")
                    except Exception: pass
                    log_db_error(logger, f"process_job_{notice_id}", "scrapers.jobs", exc)
                    break

            if existing is None:
                new_jobs += 1
                if trigger_alerts:
                    try:
                        res = dispatch_job_alerts(j, conn=db_conn)
                        alerts_sent += res.get("delivered", 0)
                    except Exception as exc:
                        log_db_error(logger, f"dispatch_job_alert_{notice_id}", "scrapers.jobs", exc)
                    try:
                        from alerts.viber import dispatch_viber_job_alerts
                        dispatch_viber_job_alerts([j])
                    except Exception as exc:
                        log_db_error(logger, f"dispatch_viber_job_{notice_id}", "scrapers.jobs", exc)
            else:
                updated_jobs += 1

    if conn is not None:
        _persist(conn)
    else:
        with get_db() as db_conn:
            _persist(db_conn)

    return {"status": "ok", "fetched": len(fetched), "new": new_jobs, "updated": updated_jobs, "alerts_sent": alerts_sent}
