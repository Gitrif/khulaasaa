from __future__ import annotations

"""
Telegram HTML Message Formatters and Interactive Keyboards for Khulaasaa.
"""

import html
import re
from typing import Any, Optional

import json
import os
from datetime import datetime
from scrapers.translator import is_dhivehi, translate_dhivehi_title, translate_agency
from data.database import get_db, get_active_sponsored_ad
from alerts.telegram_client import DISCIPLINE_KEYS

def matches_interest(
    bid: dict[str, Any],
    subscriber: dict[str, Any],
    is_paid: Optional[bool] = None,
) -> bool:
    """
    Check if a bid notice matches a subscriber's registered interests.
    
    Subscription Tiers:
    - Paid Pro Subscribers (MVR 50/month, is_paid=True): Receive customized alerts based on
      their registered trade disciplines & keywords.
    - Free Subscribers (is_paid=False): Receive the normal feed (all active tender notices).
    """
    # If is_paid not explicitly specified, check subscriber dict (default True for test compatibility)
    paid = is_paid if is_paid is not None else subscriber.get("is_paid", True)

    disciplines = subscriber.get("disciplines") or []
    keywords = subscriber.get("keywords") or []

    # Free users receive the normal feed (all active tenders)
    if not paid:
        # If user explicitly muted tenders by deselecting all, respect mute
        if disciplines == [] and "tenders" not in keywords:
            return False
        return True

    # Pro tier: precision customization
    # If subscriber specified neither, alert matches everything
    if not disciplines and not keywords:
        return True

    bid_discipline = (bid.get("discipline") or "").strip()
    discipline_match = False
    if disciplines:
        if any(d.lower() in ("all", "any") for d in disciplines):
            discipline_match = True
        else:
            discipline_match = any(d.lower() == bid_discipline.lower() for d in disciplines)

    keyword_match = False
    if keywords:
        searchable_text = " ".join([
            bid.get("title") or "",
            bid.get("title_en") or "",
            bid.get("agency") or "",
            bid.get("agency_name_en") or "",
            bid.get("reference_number") or bid.get("ref") or "",
            bid.get("submission_location") or "",
            bid.get("info_location") or "",
        ]).lower()

        # Filter out general channel tags so they don't falsely match inside tender text
        bid_keywords = [k for k in keywords if k.strip() and k.lower() not in {"breaking", "jobs", "rentals", "all_news"}]
        keyword_match = any(k.lower() in searchable_text for k in bid_keywords)

    # If both are specified, match if either condition is satisfied
    if disciplines and keywords:
        return discipline_match or keyword_match
    elif disciplines:
        return discipline_match
    else:
        return keyword_match



def format_tender_alert_html(bid: dict[str, Any], ad_footer: Optional[str] = None) -> str:
    """
    Format a tender notice into a rich, bilingual HTML message suitable for Telegram.
    Optionally appends a verified sponsor/partner footer.
    """
    raw_title = bid.get("title") or "Tender Notice"
    ref = bid.get("reference_number") or bid.get("ref") or "N/A"
    agency = bid.get("agency_name_en") or bid.get("agency") or "Unknown Agency"
    entity_type = bid.get("entity_type") or ""
    discipline = bid.get("discipline") or "Other"
    gazette_type = bid.get("gazette_type") or "Bid"
    url = bid.get("source_url") or "https://gazette.gov.mv"

    # Bilingual title handling
    if is_dhivehi(raw_title):
        title_dv = raw_title
        title_en = bid.get("title_en") or translate_dhivehi_title(raw_title)
    else:
        title_en = raw_title
        title_dv = bid.get("title_dv") or ""

    # Agency translation if in Thaana
    if is_dhivehi(agency):
        agency = translate_agency(agency)

    agency_badge = f"({entity_type})" if entity_type and entity_type != "Other" else ""

    # Milestone dates and locations
    sub_date = bid.get("submission_date") or bid.get("deadline_iso") or "Not specified"
    sub_loc = bid.get("submission_location") or "Refer to gazette announcement"
    info_date = bid.get("info_date") or "None announced"
    info_loc = bid.get("info_location") or "N/A"

    # Build Telegram HTML
    lines = [
        "<b>NEW TENDER ALERT — Khulaasaa Dispatch</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"<b>Title (EN):</b> {html.escape(title_en)}",
    ]

    if title_dv:
        lines.append(f"<b>Original (DV):</b> {html.escape(title_dv)}")

    lines.extend([
        f"<b>Agency:</b> {html.escape(agency)} {html.escape(agency_badge)}".strip(),
        f"<b>Discipline:</b> {html.escape(discipline)} | <b>Type:</b> {html.escape(gazette_type)}",
        f"<b>Reference:</b> <code>{html.escape(ref)}</code>",
        "",
        "<b>TENDER MILESTONES:</b>",
        f"<b>Bid Submission:</b> {html.escape(sub_date)}",
        f"<b>Submission Venue:</b> {html.escape(sub_loc)}",
    ])

    if info_date != "None announced" or info_loc != "N/A":
        lines.extend([
            f"<b>Info Session / Queries:</b> {html.escape(info_date)}",
            f"<b>Info Venue:</b> {html.escape(info_loc)}",
        ])

    lines.extend([
        "",
        f"<a href=\"{html.escape(url)}\">Open Announcement on Gazette →</a>",
    ])

    if ad_footer:
        lines.extend([
            "",
            "━━━━━━━━━━━━━━━━━━━━━━",
            ad_footer,
        ])

    return "\n".join(lines)


def format_sponsored_block(ad: dict[str, Any]) -> str:
    """Format an active sponsor campaign into a simple inline text link."""
    sponsor = html.escape(ad.get("sponsor_name") or "Khulaasaa Partner")
    link = ad.get("link_url") or "https://khulaasaa.tech"
    text = (ad.get("text_html") or "").strip()
    clean_text = re.sub(r"<[^>]+>", "", text)
    clean_text = clean_text.replace("&bull;", "•").replace("&mdash;", "—").replace("&rarr;", "→").strip()
    if len(clean_text) > 75:
        clean_text = clean_text[:72] + "..."
    return f'Ad: <a href="{html.escape(link)}">{sponsor} — {html.escape(clean_text)}</a>'


def format_standalone_ad_post(ad: dict[str, Any]) -> str:
    """Format an actual standalone sponsor ad served between news batches by our ad engine."""
    sponsor = html.escape(ad.get("sponsor_name") or "Khulaasaa Partner")
    body = (ad.get("text_html") or "").strip()
    body = body.replace("&bull;", "•").replace("&mdash;", "—").replace("&rarr;", "→")
    link = ad.get("link_url") or ""
    lines = [
        f"<b>SPONSORED DISPATCH — {sponsor}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        body,
    ]
    if link:
        lines.extend([
            "",
            f'<a href="{html.escape(link)}">Explore {sponsor} →</a>',
        ])
    return "\n".join(lines)


def build_tender_keyboard(bid: dict[str, Any], is_paid: bool = True) -> Optional[dict[str, Any]]:
    """Build inline keyboard buttons for a tender alert."""
    buttons = []
    url = bid.get("source_url")
    if url:
        buttons.append([{"text": "Open Notice on Gazette", "url": url}])
    app_url = os.environ.get("APP_URL", "https://khulaasaa.tech").rstrip("/")
    if app_url:
        buttons.append([{"text": "Open Procurement App ↗", "url": f"{app_url}/bids"}])
    if not is_paid:
        buttons.append([{"text": "[PRO] Upgrade to Pro (MVR 50/mo)", "callback_data": "upgrade:pro"}])
    return {"inline_keyboard": buttons} if buttons else None


def build_news_keyboard(article: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Build single-line compact provider action buttons."""
    buttons = []
    source_row = []
    url = article.get("url")
    sources = article.get("sources") or []
    source_links = article.get("source_links") or {}

    if source_links:
        for s_id, s_url in list(source_links.items())[:3]:
            source_row.append({"text": f"{s_id.title()} ↗", "url": s_url})
    elif url:
        label = sources[0].title() if sources else "Story"
        source_row.append({"text": f"{label} ↗", "url": url})

    if source_row:
        buttons.append(source_row)

    app_url = os.environ.get("APP_URL", "https://khulaasaa.tech").rstrip("/")
    if app_url:
        buttons.append([{"text": "Open on Khulaasaa ↗", "url": app_url}])
    return {"inline_keyboard": buttons} if buttons else None


def format_news_alert_html(article: dict[str, Any], ad_footer: Optional[str] = None) -> str:
    """Format a news article into simple, clean text with who reported it."""
    raw_headline = (article.get("headline") or "News Alert").strip()
    sources = article.get("sources") or ["Khulaasaa"]
    url = article.get("url") or ""

    source_links = article.get("source_links") or {}
    source_items = []
    if source_links:
        for s_name, s_url in source_links.items():
            source_items.append(f'<a href="{html.escape(s_url)}">{html.escape(s_name.title())}</a>')
    elif url and sources:
        for s_name in sources:
            source_items.append(f'<a href="{html.escape(url)}">{html.escape(s_name.title())}</a>')
    else:
        for s_name in sources:
            source_items.append(html.escape(s_name.title()))

    sources_str = " • ".join(source_items)

    lines = [
        f"<b>{html.escape(raw_headline)}</b>",
        "",
        f"Reported by: {sources_str}",
    ]

    if ad_footer:
        lines.extend([
            "",
            ad_footer,
        ])

    return "\n".join(lines)


def matches_news_interest(
    article: dict[str, Any],
    keywords: list[str],
    is_paid: Optional[bool] = None,
) -> bool:
    """
    Determine if a news article matches a subscriber's keyword preferences.

    Subscription Tiers:
    - Paid Pro Subscribers (MVR 50/month, is_paid=True): Receive customized alerts
      filtered by precision storyline topics & custom keywords.
    - Free Subscribers (is_paid=False): Receive the normal feed (all general news & breaking news).
      Custom topic/keyword filtering requires Pro tier.
    """
    paid = is_paid if is_paid is not None else True

    if not paid:
        # Free users receive the normal feed (all news & breaking)
        # If user explicitly turned off news (empty keywords list), respect mute
        if keywords is not None and len(keywords) == 0:
            return False
        return True

    if not keywords or any(k.lower() in ("all", "all_news", "any", "news") for k in keywords):
        return True

    section = (article.get("section") or "general").lower()
    headline = (article.get("headline") or "").lower()
    summary = (article.get("summary") or "").lower()
    tags = [t.lower() for t in article.get("tags", [])]

    # 'breaking' receives breaking and major news alerts
    if "breaking" in keywords and section in ("breaking", "major"):
        return True

    # Topic/narrative matching (e.g. ras-male, sultan-park, tgst, bridge-safety)
    for kw in keywords:
        k = kw.lower().strip()
        if not k or k in {"all_news", "breaking", "jobs", "rentals"}:
            continue
        if k in tags or k in headline or k in summary:
            return True

    return False


def format_obituary_alert_html(ob: dict[str, Any]) -> str:
    """Format a respectful Islamic Janaza notice for Telegram."""
    name_dv = (ob.get("name_dv") or "މަރުޙޫމް").strip()
    age = f" ({ob['age']}އ)" if ob.get("age") else ""
    address = f" • {ob['address_dv']}" if ob.get("address_dv") else ""
    mosque = ob.get("funeral_mosque_dv") or "މަސްޖިދުލް ތަޢާވުން (އާސަހަރާ މިސްކިތް)"
    prayer_time = ob.get("prayer_time_dv") or "ޢަޞްރު ނަމާދަށްފަހު"
    contacts = f"\n<b>އާއިލާގެ ނަންބަރު:</b> {html.escape(ob['contact_numbers'])}" if ob.get("contact_numbers") else ""

    lines = [
        "<b>ކަށުނަމާދު — صلاة الجنازة</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "<b>إِنَّا لِلَّهِ وَإِنَّا إِلَيْهِ رَاجِعُونَ</b>",
        "",
        f"<b>{html.escape(name_dv)}</b>{html.escape(age)}{html.escape(address)}",
        f"<b>މިސްކިތް:</b> {html.escape(mosque)}",
        f"<b>ވަގުތު:</b> {html.escape(prayer_time)}",
    ]
    if contacts:
        lines.append(contacts)

    return "\n".join(lines)


def build_obituary_keyboard(ob: dict[str, Any]) -> Optional[dict[str, Any]]:
    app_url = os.environ.get("APP_URL", "https://khulaasaa.tech").rstrip("/")
    ob_url = f"{app_url}/obituaries" if app_url else "https://khulaasaa.tech/obituaries"
    buttons = [
        [
            {"text": "View Janaza Registry ↗", "url": ob_url}
        ]
    ]
    return {"inline_keyboard": buttons}


def format_job_alert_html(job: dict[str, Any], ad_footer: Optional[str] = None) -> str:
    """Format a job opening into a clean, compelling Telegram alert."""
    title = job.get("title_en") or job.get("title") or "Job Vacancy"
    title_dv = job.get("title") if job.get("title") != title else None
    agency = job.get("agency_name_en") or job.get("agency") or "Employer"
    discipline = job.get("discipline") or "Other"
    location = job.get("location") or "Male'"
    salary = job.get("salary_raw")
    deadline = job.get("deadline_iso") or "Open until filled"
    if "T" in str(deadline):
        try:
            dt = datetime.fromisoformat(str(deadline))
            deadline = dt.strftime("%d %b %Y, %I:%M %p")
        except Exception:
            deadline = str(deadline)[:16].replace("T", " ")
    url = job.get("source_url") or "https://gazette.gov.mv/iulaan/type/vazeefaa"
    portal = job.get("source_portal") or "gazette.gov.mv"

    lines = [
        "<b>NEW JOB VACANCY — Khulaasaa Jobs</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"<b>Title:</b> {html.escape(title)}",
    ]
    if title_dv:
        lines.append(f"<b>Dhivehi:</b> {html.escape(title_dv)}")

    lines.extend([
        f"<b>Employer:</b> {html.escape(agency)}",
        f"<b>Discipline:</b> {html.escape(discipline)}",
        f"<b>Location:</b> {html.escape(location)}",
    ])

    if salary and salary != "None":
        lines.append(f"<b>Remuneration:</b> {html.escape(salary)}")

    lines.extend([
        f"<b>Deadline:</b> {html.escape(deadline)}",
        f"<b>Source:</b> {html.escape(portal)}",
        "",
        f"<a href=\"{html.escape(url)}\">View Vacancy & Apply Online →</a>",
    ])

    if ad_footer:
        lines.extend([
            "",
            "━━━━━━━━━━━━━━━━━━━━━━",
            ad_footer,
        ])

    return "\n".join(lines)
from alerts.telegram_keyboards import (
    format_pro_tier_message,
    build_settings_keyboard_and_text,
)
