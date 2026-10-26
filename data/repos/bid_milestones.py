"""
Tender Milestones & Venues Extractor from HTML notices.
"""
from __future__ import annotations
import re
from typing import Optional
from bs4 import BeautifulSoup

def extract_milestones_and_venues(html: str) -> dict[str, Optional[str]]:
    """
    Extract key tender milestones from notice HTML:
    - info_date: pre-bid meeting / inquiry date or registration window
    - info_location: location / link to visit or contact for information
    - submission_date: date and time for bid submission
    - submission_location: physical venue or portal to submit the bid
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)

    info_date: Optional[str] = None
    info_location: Optional[str] = None
    submission_date: Optional[str] = None
    submission_location: Optional[str] = None

    # 1. Parse structured tables if present (common in SOE and Ministry tenders)
    for tr in soup.find_all("tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
        if len(cells) >= 2:
            for idx, c in enumerate(cells):
                c_low = c.lower()
                if c_low in ["step", "#", "no", "no.", "ނަންބަރު", "process", "މަރުޙަލާ", "date", "venue", "th"]:
                    continue

                is_info = any(k in c_low for k in [
                    "pre-bid", "pre bid", "inquiry", "inquiries", "clarification",
                    "information", "register", "registration", "މަޢުލޫމާތު", "މައުލޫމާތު", "ރަޖިސްޓްރީ"
                ])
                is_sub = any(k in c_low for k in [
                    "submission", "proposal opening", "bid opening", "submit", "opening",
                    "ބީލަން ހުށަހެޅުން", "ބީލަން ހުޅުވުން", "ހުށަހެޅުން", "އަންދާސީ ހިސާބު"
                ])

                if is_info and not info_date:
                    if idx + 1 < len(cells):
                        info_date = cells[idx + 1]
                    if idx + 2 < len(cells):
                        info_location = cells[idx + 2]
                    break
                elif is_sub and not submission_location:
                    if idx + 1 < len(cells):
                        submission_date = cells[idx + 1]
                    if idx + 2 < len(cells):
                        submission_location = cells[idx + 2]
                    break

    # 2. Extract from English prose
    if not submission_location:
        sub_p = re.search(
            r"(?:submitted|delivered)\s+to\s+([^,\.\n]+(?:office|reception|building|ministry|council|floor|national tender)[^\.\n]*)",
            text,
            re.IGNORECASE,
        )
        if sub_p:
            submission_location = sub_p.group(1).strip()

    if not info_location:
        info_p = re.search(
            r"(?:further information|obtain|inquiries|questions)[^\.\n]*?(?:at|via|from)\s+([^,\.\n]+(?:office|reception|building|ministry|council|link|email)[^\.\n]*)",
            text,
            re.IGNORECASE,
        )
        if info_p:
            info_location = info_p.group(1).strip()

    # 3. Extract from Dhivehi prose
    clean_text = " ".join(re.sub(r"[\u200E\u200F\u200B]", "", text).split())

    # Prose Pattern A (with އޮންނާނީ ... ގައި ... ގައެވެ)
    mA = re.search(
        r"(?:ބީލަންތައް\s+ބަލައިގަތުމާއި[^\.\d]*?ބީލަން\s+ހުޅުވުން|ބީލަން\s+ހުށަ?ހެޅު[މު|ން][^\.\d]*?|އަންދާސީ\s+ހިސާބު\s+ހުށަ?ހެޅު[މު|ން][^\.\d]*?)\s*އޮންނާނީ\s+([^\.]+?)\s+ގައި\s+([^\.]+?)(?:ގައެވެ|އެވެ|\.)",
        clean_text,
    )
    if mA:
        if not submission_date:
            submission_date = mA.group(1).strip()
        if not submission_location:
            submission_location = mA.group(2).strip()
    else:
        # Prose Pattern B (with ހުށަހަޅައްވާނީ ... ށް ... އަށެވެ)
        mB = re.search(
            r"(?:ހުށަހަޅައްވާނީ|ހުށަހަޅުއްވާނީ|ހުށަހެޅުން)\s+([^\.]+?)\s*ށް\s*([^\.]+?)(?:އަށެވެ|ގައެވެ|އެވެ|\.)",
            clean_text,
        )
        if mB:
            if not submission_date:
                submission_date = mB.group(1).strip()
            if not submission_location:
                submission_location = mB.group(2).strip()
        else:
            # Prose Pattern C (with ބީލަން ހުށައެޅުމާއި ... ދުރުވެ)
            mC = re.search(
                r"ބީލަން\s+ހުށަ?އެޅު[މު|ން].*?((?:\d{1,5}\s+[^\d\s]+\s+\d{1,4}|\d{1,2}\s+[^\d\s]+\s+\d{4})[^\.]*?(?:\d{1,2}:\d{2})?)\s*ށް\s*(މި\s*އިދާރާއަށް|ކައުންސިލް\s*އިދާރާއަށް|[^\.]+?)\s*(?:ދުރުވެ|ވަޑައިގެން)",
                clean_text,
            )
            if mC:
                if not submission_date:
                    submission_date = mC.group(1).strip()
                if not submission_location:
                    submission_location = mC.group(2).strip()

    # Fallback venue search in Dhivehi prose
    if not submission_location:
        sub_m = re.search(
            r"([^\.\n]*(?:މާލަމު|ކޮންފަރެންސް\s*ހޯލް|މީޓިންގ\s*ރޫމް|ކައުންސިލް\s*އިދާރާ)[^\.\n]*)",
            clean_text,
        )
        if sub_m:
            submission_location = sub_m.group(1).strip()

    # Pre-bid / info window and inquiries in Dhivehi
    if not info_date:
        info_m = re.search(
            r"(?:މަޢުލޫމާތު\s+ސާފުކުރުން|މަޢުލޫމާތު\s+ދިނު[މު|ން]|ޕްރީ\s*ބިޑް|ޕްރީ-ބިޑް)\s*([^\.]+?)\s*(?:ގައި|އޮންނާނީ)\s*([^\.]+?)(?:ގައެވެ|އެވެ|\.)",
            clean_text,
        )
        if info_m:
            info_date = info_m.group(1).strip()
            if not info_location:
                info_location = info_m.group(2).strip()

    if not info_date:
        reg_m = re.search(
            r"(\d{1,2}\s+[^\d\s]+\s+\d{4}\s+އިން\s+(?:ފެށިގެން\s+)?\d{1,2}\s+[^\d\s]+\s+\d{4}[^\n\.]*)",
            clean_text,
        )
        if reg_m:
            info_date = reg_m.group(1).strip()
            if not info_location:
                info_location = "މިއިދާރާއަށް ވަޑައިގެން / އޮންލައިން ފޯމު"

    # Extract inquiries contact emails & phone numbers if not already populated
    emails = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    phones = re.findall(r"\b(?:6\d{6}|7\d{6}|9\d{6}|3\d{6})\b", text)
    if not info_location and emails:
        info_location = f"Email: {emails[0]}" + (f" / Tel: {phones[0]}" if phones else "")

    return {
        "info_date": info_date,
        "info_location": info_location,
        "submission_date": submission_date,
        "submission_location": submission_location,
    }


def purge_expired_bids(conn: sqlite3.Connection, retention_days: int = 30) -> int:
    """
    Purge bids that expired more than `retention_days` (default 30 days) ago.
    Also removes legacy placeholder notices (notice-%).
    Explicitly preserves news articles and tracked story timelines.
    """
    from datetime import datetime, timedelta
    cutoff_dt = datetime.now() - timedelta(days=retention_days)
    cutoff_date = cutoff_dt.strftime("%Y-%m-%d")

    try:
        cursor = conn.execute(
            """
            DELETE FROM bids
            WHERE (submission_date IS NOT NULL AND submission_date < ?)
               OR (submission_date IS NULL AND published_date IS NOT NULL AND published_date < ?)
               OR notice_id LIKE ?;
            """,
            (cutoff_date, cutoff_date, "notice-%"),
        )
        return cursor.rowcount or 0
    except Exception:
        return 0


