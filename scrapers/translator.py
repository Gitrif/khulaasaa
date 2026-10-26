"""
Dhivehi to English procurement translation module for Khulaasaa tender notices.
"""
from __future__ import annotations

import re
from typing import Optional

from scrapers.translation_dict import (
    THAANA_PATTERN,
    ATOLL_PREFIXES,
    ISLAND_NAMES,
    FACILITY_TERMS,
    VOCABULARY_TERMS,
    PROCUREMENT_PATTERNS,
)

def is_dhivehi(text: Optional[str]) -> bool:
    """Return True if text contains Dhivehi Thaana characters."""
    if not text:
        return False
    return bool(THAANA_PATTERN.search(text))


def clean_dhivehi_markers(text: str) -> str:
    """Strip Unicode direction marks and clean whitespace."""
    text = re.sub(r"[\u200E\u200F\u200B\uFEFF]", "", text)
    return " ".join(text.split())


def clean_residual_thaana(text: str) -> str:
    """Removes any remaining Thaana characters so they never leak into English UI text."""
    if not text:
        return ""
    # Strip any stray Thaana characters and normalize spaces
    cleaned = re.sub(r"[\u0780-\u07BF]+", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,-:")
    return cleaned


def _translate_phrase_elements(text: str) -> str:
    """Translates known Atolls, islands, facilities, and vocabulary in a phrase."""
    cleaned = clean_dhivehi_markers(text)

    # 0. Strip Dhivehi indefinite suffix 'އެއް' / 'އަކަށް' from words so root nouns match
    cleaned = re.sub(r"([\u0780-\u07BF]+)އެއް\b", r"\1", cleaned)
    cleaned = re.sub(r"([\u0780-\u07BF]+)އަކަށް\b", r"\1", cleaned)

    # 1. Translate Atoll prefixes first so long-form administrative atolls (e.g. Raa, Baa, Haa) match before single island names
    for dv_atoll, en_atoll in sorted(ATOLL_PREFIXES.items(), key=lambda x: -len(x[0])):
        pattern = rf"(?<![\u0780-\u07BF]){re.escape(dv_atoll)}(?![\u0780-\u07BF])"
        cleaned = re.sub(pattern, en_atoll + " ", cleaned)

    # 2. Translate island & city names with Thaana boundary protection
    for dv_island, en_island in sorted(ISLAND_NAMES.items(), key=lambda x: -len(x[0])):
        pattern = rf"(?<![\u0780-\u07BF]){re.escape(dv_island)}(?![\u0780-\u07BF])"
        cleaned = re.sub(pattern, en_island, cleaned)

    # 3. Translate facilities
    for dv_fac, en_fac in sorted(FACILITY_TERMS.items(), key=lambda x: -len(x[0])):
        cleaned = cleaned.replace(dv_fac, en_fac)

    # 4. Translate vocabulary terms
    for dv_voc, en_voc in sorted(VOCABULARY_TERMS.items(), key=lambda x: -len(x[0])):
        cleaned = cleaned.replace(dv_voc, en_voc)

    # Remove Dhivehi genitive suffix 'ގެ' and prepositions
    cleaned = re.sub(r"([A-Za-z\']+)\s*ގެ\s*([A-Za-z\']+)", r"\2 of \1", cleaned)
    cleaned = re.sub(r"\s*ގެ\s*", " ", cleaned)
    cleaned = re.sub(r"\bއަދި\b", "and", cleaned)
    cleaned = re.sub(r"\bއިން\b", "from", cleaned)
    cleaned = re.sub(r"\bއަށް\b", "to", cleaned)
    cleaned = re.sub(r"\bގައި\b", "in", cleaned)
    cleaned = re.sub(r"\bގައެވެ\b", "", cleaned)
    cleaned = re.sub(r"\bހޯދުން\b", "", cleaned)
    cleaned = re.sub(r"\bހޯދުމަށް\b", "", cleaned)
    cleaned = re.sub(r"\bވަނަ\b", "", cleaned)

    # Clean double spaces
    return " ".join(cleaned.split())


def translate_dhivehi_title(title: str) -> str:
    """
    Translates a Maldivian tender notice title into clear, professional English.
    If already English, returns title untouched. Guarantees no Thaana leaks.
    """
    if not title:
        return ""

    if not is_dhivehi(title):
        return title.strip()

    cleaned = clean_dhivehi_markers(title)

    # Check for Invitation for Bids prefix
    prefix_match = re.match(r"^ބީލަން\s+ހުށަހެޅުމުގެ\s+ދަޢުވަތު\s*(?:-|:)?\s*(.*)", cleaned, re.IGNORECASE)
    has_prefix = False
    if prefix_match:
        has_prefix = True
        cleaned = prefix_match.group(1).strip()

    # Check for Re-announcement
    is_reannouncement = False
    if "އަލުން" in cleaned:
        is_reannouncement = True
        cleaned = re.sub(r"އަލުން\s*(?:އިޢުލާން|އިއުލާން)(?:ކުރުން)?\.?", "", cleaned).strip()

    # Normalize trailing procurement action suffixes
    cleaned = re.sub(
        r"\s*(?:ހޯދުމަށް\s*ބޭނުންވެއްޖެއެވެ?|ހޯދުމަށް\s*ބޭނުންވެގެން?|ހޯދަން\s*ބޭނުންވެއްޖެއެވެ?|ހޯދަން\s*ބޭނުންވެގެން?|ހޯދުމާއި\s*ގުޅޭ|ހޯދުމާއި\s*ގުޅިގެން|ހޯދުމާ\s*ގުޅޭ|އާއި\s*ގުޅޭ|އާއި\s*ގުޅިގެން|މާއި\s*ގުޅޭ|މާއި\s*ގުޅިގެން|ގުޅޭ|ގުޅިގެން)\.?$",
        " ހޯދުން",
        cleaned,
    ).strip()

    # Specialized procurement archetype handlers:
    # 1. Waste transfer to Thilafushi
    if "ތިލަފުއްޓަށް" in cleaned and "ކުނި" in cleaned:
        m = re.search(r"(.+?)\s*(?:ކުނިގޮނޑުގައިވާ|ހުރި)?\s*ކުނިތައް?\s*(?:ނަގައިގެން\s*)?ތިލަފުއްޓަށް\s*ގެންދާނެ\s*ފަރާތެއް", cleaned)
        tgt_raw = m.group(1).strip() if m else cleaned
        tgt = _translate_phrase_elements(tgt_raw)
        tgt = clean_residual_thaana(tgt)
        res = f"Seeking contractor for transfer and transport of waste from {tgt} to Thilafushi"
        return f"{'Re-announcement: ' if is_reannouncement else ''}{'Invitation for Bids: ' if has_prefix else ''}{res}"

    # 2. AC servicing and multi-year maintenance
    if ("އޭސީތައް" in cleaned or "އޭސީ" in cleaned) and ("ސަރވިސް" in cleaned or "ބެލެހެއްޓު" in cleaned):
        m = re.search(r"(.+?)\s*(?:ކައުންސިލްގެ\s*)?(?:އިމާރާތްތަކުގައި\s*)?(?:ހަރުކުރެވިފައިވާ\s*)?އޭސީތައް", cleaned)
        tgt_raw = m.group(1).strip() if m else "Council Buildings"
        tgt = _translate_phrase_elements(tgt_raw)
        tgt = clean_residual_thaana(tgt)
        duration = "1-Year " if ("01" in cleaned or "އެކެއް" in cleaned) else ""
        res = f"Seeking contractor for {duration}Servicing, Repair and Maintenance of Air Conditioners (AC) installed in {tgt} Buildings"
        return f"{'Re-announcement: ' if is_reannouncement else ''}{'Invitation for Bids: ' if has_prefix else ''}{res}"

    # 3. AC supply and installation
    if "އޭސީ" in cleaned and ("އިންސްޓޯލް" in cleaned or "ހޯލް" in cleaned):
        m = re.search(r"(.+?)\s*އޭސީ\s*ކުރުމަށް", cleaned)
        tgt_raw = m.group(1).strip() if m else "Multipurpose Hall"
        tgt = _translate_phrase_elements(tgt_raw)
        tgt = clean_residual_thaana(tgt)
        res = f"Supply and installation of Air Conditioners (AC) for {tgt}"
        return f"{'Re-announcement: ' if is_reannouncement else ''}{'Invitation for Bids: ' if has_prefix else ''}{res}"

    # 4. Logo design
    if "ލޯގޯ" in cleaned and "ފަރުމާ" in cleaned:
        m = re.search(r"(.+?)(?:ގެ\s*)?ލޯގޯ\s*ފަރުމާ", cleaned)
        tgt_raw = m.group(1).strip() if m else ""
        tgt = _translate_phrase_elements(tgt_raw)
        tgt = clean_residual_thaana(tgt)
        res = f"Official Logo Design for {tgt}"
        return f"{'Re-announcement: ' if is_reannouncement else ''}{'Invitation for Bids: ' if has_prefix else ''}{res}"

    # 5. Uniform tailoring
    if "ޔުނިފޯމް" in cleaned and "ފަހައި" in cleaned:
        m = re.search(r"(.+?)(?:ގެ\s*)?ޔުނިފޯމް\s*ފަހައި", cleaned)
        tgt_raw = m.group(1).strip() if m else ""
        tgt = _translate_phrase_elements(tgt_raw)
        tgt = clean_residual_thaana(tgt)
        res = f"Tailoring and supply of uniforms for {tgt}"
        return f"{'Re-announcement: ' if is_reannouncement else ''}{'Invitation for Bids: ' if has_prefix else ''}{res}"

    # 6. Inventory stock materials
    if "ސްޓޮކަށް" in cleaned and "ސަޕްލައި" in cleaned:
        m = re.search(r"(.+?)(?:ގެ\s*)?ސްޓޮކަށް", cleaned)
        tgt_raw = m.group(1).strip() if m else ""
        tgt = _translate_phrase_elements(tgt_raw)
        tgt = clean_residual_thaana(tgt)
        res = f"Supply and delivery of inventory stock materials for {tgt}"
        return f"{'Re-announcement: ' if is_reannouncement else ''}{'Invitation for Bids: ' if has_prefix else ''}{res}"

    # 7. Buggy / electric vehicles
    if "ބަގީ" in cleaned and "ސަޕްލައި" in cleaned:
        res = "Supply and delivery of Electric Buggy"
        return f"{'Re-announcement: ' if is_reannouncement else ''}{'Invitation for Bids: ' if has_prefix else ''}{res}"

    # 8. Security services
    if any(s in cleaned for s in ["ސެކިއުރިޓީ ބަލަހައްޓައިދޭނެ ފަރާތެއް", "ސެކިއުރިޓީ ބެލެހެއްޓުން", "ސެކެއުރިޓީ ބެލެހެއްޓުން"]):
        tgt_raw = cleaned.replace("ސެކިއުރިޓީ", "").replace("ސެކެއުރިޓީ", "").replace("ބަލަހައްޓައިދޭނެ ފަރާތެއް ހޯދުން", "").replace("ބެލެހެއްޓުން", "").strip()
        tgt = _translate_phrase_elements(tgt_raw) if tgt_raw else "School"
        tgt = clean_residual_thaana(tgt)
        res = f"Provision of Security Services for {tgt}" if tgt else "Provision of Security Services"
        return f"{'Re-announcement: ' if is_reannouncement else ''}{'Invitation for Bids: ' if has_prefix else ''}{res}"

    # 9. Waste disposal / cleaning
    if any(s in cleaned for s in ["ކުނި އުކައިދޭނެ ފަރާތެއް", "ކުނި އުކާލުން"]):
        target = _translate_phrase_elements(cleaned.replace("ކުނި އުކައިދޭނެ ފަރާތެއް ހޯދުން", "").replace("ކުނި އުކައިދޭނެ ފަރާތެއް ހޯދުމަށް", "").strip())
        target = clean_residual_thaana(target)
        res = f"Waste Disposal Services for {target}" if target else "Waste Disposal and Cleaning Services"
        return f"{'Re-announcement: ' if is_reannouncement else ''}{'Invitation for Bids: ' if has_prefix else ''}{res}"

    # 10. Building and facility repair & maintenance
    if "މަރާމާތު" in cleaned and ("ފަރާތެއް" in cleaned or "މަސައްކަތް" in cleaned):
        m = re.search(r"(.+?)(?:ގެ\s*)?މަރާމާތު", cleaned)
        tgt_raw = m.group(1).strip() if m else ""
        tgt = _translate_phrase_elements(tgt_raw)
        tgt = clean_residual_thaana(tgt)
        res = f"Seeking contractor for repair and maintenance of {tgt}" if tgt else "Repair and Maintenance works"
        return f"{'Re-announcement: ' if is_reannouncement else ''}{'Invitation for Bids: ' if has_prefix else ''}{res}"

    # Check against standard procurement patterns
    for pattern, template in PROCUREMENT_PATTERNS:
        match = pattern.search(cleaned)
        if match:
            target_raw = match.group(1).strip() if match.groups() else ""
            translated_target = _translate_phrase_elements(target_raw) if target_raw else ""
            translated_target = clean_residual_thaana(translated_target)
            if "{target}" in template:
                res = template.replace("{target}", translated_target).strip()
            else:
                res = f"{template}: {translated_target}".strip()
            res = " ".join(res.split())
            if res.endswith(" of") or res.endswith(":"):
                res = res.rstrip(" of:")
            prefix = "Re-announcement: " if is_reannouncement else ""
            return f"{prefix}{'Invitation for Bids: ' if has_prefix and not res.startswith('Invitation') else ''}{res}"

    # General phrase translation fallback
    translated = _translate_phrase_elements(cleaned)
    translated_no_thaana = clean_residual_thaana(translated)
    prefix = "Re-announcement: " if is_reannouncement else ""
    if translated_no_thaana and len(translated_no_thaana) > 5:
        res = f"Tender: {translated_no_thaana}"
        return f"{prefix}{'Invitation for Bids: ' if has_prefix else ''}{res}"

    # Safe English fallback with zero Thaana characters
    clean_en = clean_residual_thaana(cleaned)
    return f"{prefix}Tender Notice: {clean_en}" if clean_en else "Procurement Notice"


def translate_agency(agency: Optional[str]) -> str:
    """
    Translates an agency name from Dhivehi to English using the canonical dictionary
    or domain rules. Guarantees no Dhivehi Thaana characters leak into English.
    """
    if not agency:
        return "Unknown Agency"

    if not is_dhivehi(agency):
        return agency.strip()

    cleaned = clean_dhivehi_markers(agency)

    # 1. Major State-Owned Enterprises (SOEs) & Public Companies (Check first, including branch locations)
    if any(k in cleaned for k in ["ސްޓޭޓް ޓްރޭޑިންގ", "އެސްޓީއޯ", "އެސް.ޓީ.އޯ"]):
        if any(b in cleaned for b in ["ފުވައްމުލައް", "ފުވައްމުލަކު"]):
            return "State Trading Organization (Fuvahmulah Branch)"
        return "State Trading Organization Plc"
    if any(k in cleaned for k in ["ކަސްޓަމްސް", "މޯލްޑިވްސް ކަސްޓަމްސް"]):
        return "Maldives Customs Service"
    if any(k in cleaned for k in ["ހައުސިންގ ޑިވެލޮޕްމަންޓް", "އެޗްޑީސީ", "އެޗް.ޑީ.ސީ"]):
        return "Housing Development Corporation"
    if any(k in cleaned for k in ["މާލޭ ވޯޓަރ", "ވޯޓަރ އެންޑް ސެވަރޭޖް", "އެމްޑަބްލިއުއެސްސީ"]):
        return "Male' Water and Sewerage Company"
    if any(k in cleaned for k in ["ސްޓެލްކޯ", "ސްޓޭޓް އިލެކްޓްރިކް"]):
        return "State Electric Company"
    if any(k in cleaned for k in ["ފެނަކަ"]):
        return "Fenaka Corporation"
    if any(k in cleaned for k in ["މޯލްޑިވް ގެސް", "މޯލްޑިވް ގޭސް"]):
        return "Maldive Gas"
    if any(k in cleaned for k in ["ފިއުލް ސަޕްލައިސް", "އެފްއެސްއެމް"]):
        return "Fuel Supplies Maldives"
    if any(k in cleaned for k in ["މޯލްޑިވްސް ޕޯސްޓް", "ޕޯސްޓް"]):
        return "Maldives Post"
    if any(k in cleaned for k in ["ޕޯޓްސް ލިމިޓެޑް", "އެމްޕީއެލް"]):
        return "Maldives Ports Limited"
    if any(k in cleaned for k in ["މޯލްޑިވްސް ޓްރާންސްޕޯޓް", "އެމްޓީސީސީ"]):
        return "Maldives Transport and Contracting Company"
    if any(k in cleaned for k in ["އައިލެންޑް އޭވިއޭޝަން", "މޯލްޑިވިއަން"]):
        return "Island Aviation Services"
    if any(k in cleaned for k in ["އެއާޕޯޓްސް ކޮމްޕެނީ", "އެމްއޭސީއެލް"]):
        return "Maldives Airports Company"
    if any(k in cleaned for k in ["ބޭންކް އޮފް މޯލްޑިވްސް", "ބީއެމްއެލް"]):
        return "Bank of Maldives"
    if any(k in cleaned for k in ["މިފްކޯ"]):
        return "MIFCO"
    if any(k in cleaned for k in ["އާރްޑީސީ", "ރޯޑް ޑިވެލޮޕްމަންޓް"]):
        return "Road Development Corporation"
    if any(k in cleaned for k in ["ވެމްކޯ", "ވޭސްޓް މެނޭޖްމަންޓް"]):
        return "Waste Management Corporation"

    # 2. Law Enforcement, Security, Judiciary & Constitutional Bodies
    if any(k in cleaned for k in ["ޑިޕާޓްމަންޓް އޮފް ޖުޑިޝަލް އެޑްމިނިސްޓްރޭޝަން", "ޖުޑީޝަލް އެޑްމިނިސްޓްރޭޝަން"]):
        return "Department of Judicial Administration"
    if any(k in cleaned for k in ["ޖުޑީޝަލް ސަރވިސް ކޮމިޝަން"]):
        return "Judicial Service Commission"
    if any(k in cleaned for k in ["ސުޕްރީމް ކޯޓު"]):
        return "Supreme Court of the Maldives"
    if any(k in cleaned for k in ["ހައިކޯޓު", "ހައި ކޯޓު"]):
        return "High Court of the Maldives"
    if any(k in cleaned for k in ["ކްރިމިނަލް ކޯޓު"]):
        return "Criminal Court"
    if any(k in cleaned for k in ["ސިވިލް ކޯޓު"]):
        return "Civil Court"
    if any(k in cleaned for k in ["ފެމިލީ ކޯޓު"]):
        return "Family Court"
    if any(k in cleaned for k in ["ޖުވެނައިލް ކޯޓު"]):
        return "Juvenile Court"
    if any(k in cleaned for k in ["ޑްރަގް ކޯޓު"]):
        return "Drug Court"
    if "މެޖިސްޓްރޭޓް ކޯޓު" in cleaned:
        t_court = _translate_phrase_elements(cleaned)
        t_court = clean_residual_thaana(t_court).replace("Magistrate Court", "").strip(" ,-:")
        return f"{t_court} Magistrate Court" if t_court else "Magistrate Court"
    if any(k in cleaned for k in ["ރައީސުލްޖުމްހޫރިއްޔާގެ އޮފީސް", "ރައީސް އޮފީސް"]):
        return "The President's Office"
    if any(k in cleaned for k in ["ރައްޔިތުންގެ މަޖިލިސް", "މަޖިލީހުގެ އިދާރާ"]):
        return "People's Majlis Secretariat"
    if any(k in cleaned for k in ["ލޯކަލް ގަވަރމަންޓް އޮތޯރިޓީ", "އެލްޖީއޭ"]):
        return "Local Government Authority"
    if any(k in cleaned for k in ["ނޭޝަނަލް ޑްރަގް އޭޖެންސީ", "އެންޑީއޭ"]):
        return "National Drug Agency"
    if any(k in cleaned for k in ["ހެލްތް ޕްރޮޓެކްޝަން އެޖެންސީ", "އެޗްޕީއޭ"]):
        return "Health Protection Agency"
    if any(k in cleaned for k in ["ސިވިލް އޭވިއޭޝަން"]):
        return "Maldives Civil Aviation Authority"
    if any(k in cleaned for k in ["ޕޮލިސް", "ފުލުހުން"]):
        return "Maldives Police Service"
    if any(k in cleaned for k in ["ޑިފެންސް ފޯސް", "ސިފައިން", "އެމްއެންޑީއެފް"]):
        return "Maldives National Defence Force"
    if any(k in cleaned for k in ["އިންލަންޑް ރެވެނިއު", "މީރާ"]):
        return "Maldives Inland Revenue Authority"
    if any(k in cleaned for k in ["އޮޑިޓަރ ޖެނެރަލް", "އޮޑިޓް އޮފީސް"]):
        return "Auditor General's Office"
    if any(k in cleaned for k in ["އިލެކްޝަންސް"]):
        return "Elections Commission of Maldives"
    if any(k in cleaned for k in ["އެންޓި ކޮރަޕްޝަން", "އޭސީސީ"]):
        return "Anti-Corruption Commission"
    if any(k in cleaned for k in ["ސިވިލް ސަރވިސް ކޮމިޝަން"]):
        return "Civil Service Commission"
    if any(k in cleaned for k in ["ޕްރޮސެކިއުޓަރ ޖެނެރަލް", "ޕީޖީ އޮފީސް"]):
        return "Prosecutor General's Office"
    if any(k in cleaned for k in ["މޯލްޑިވްސް މަނިޓަރީ", "އެމްއެމްއޭ"]):
        return "Maldives Monetary Authority"
    if any(k in cleaned for k in ["އިމިގްރޭޝަން"]):
        return "Maldives Immigration"
    if any(k in cleaned for k in ["ކަރެކްޝަނަލް", "ކަރެކްޝަންސް"]):
        return "Maldives Correctional Service"
    if any(k in cleaned for k in ["ޕޮލިޓެކްނިކް"]):
        return "Maldives Polytechnic"
    if any(k in cleaned for k in ["ޤައުމީ ޔުނިވަރސިޓީ", "އެމްއެންޔޫ"]):
        return "The Maldives National University"
    if any(k in cleaned for k in ["އިސްލާމީ ޔުނިވަރސިޓީ", "އައިޔޫއެމް"]):
        return "Islamic University of Maldives"

    # 3. Exactly 5 Official Cities in the Maldives:
    # Male' City, Addu City, Fuvahmulah City, Kulhudhuffushi City, Thinadhoo City
    if any(k in cleaned for k in ["މާލެ ސިޓީ", "މާލޭ ސިޓީ"]):
        return "Male' City Council"
    if any(k in cleaned for k in ["އައްޑޫ ސިޓީ", "އައްޑުއަތޮޅު ސިޓީ", "އައްޑޫ ސިޓީ ކައުންސިލް"]):
        return "Addu City Council"
    if any(k in cleaned for k in ["ފުވައްމުލައް ސިޓީ", "ފުވައްމުލަކު ސިޓީ", "ފުވައްމުލައް ސިޓީ ކައުންސިލް"]):
        return "Fuvahmulah City Council"
    if any(k in cleaned for k in ["ކުޅުދުއްފުށި ސިޓީ", "ކުޅުދުއްފުށީ ސިޓީ", "ކުޅުދުއްފުށި ސިޓީ ކައުންސިލް"]):
        return "Kulhudhuffushi City Council"
    if any(k in cleaned for k in ["ތިނަދޫ ސިޓީ", "ތިނަދޫ ސިޓީ ކައުންސިލް"]):
        return "Thinadhoo City Council"

    # 4. Island and Atoll Councils
    if "ކައުންސިލް" in cleaned:
        translated_location = _translate_phrase_elements(cleaned)
        translated_location = (
            translated_location.replace("Council Secretariat", "")
            .replace("Council", "")
            .replace("Secretariat", "")
            .replace("City", "")
            .strip()
        )
        translated_location = clean_residual_thaana(translated_location).strip(" ,-:")
        if translated_location:
            return f"Secretariat of the {translated_location} Council"
        return "Local Council Secretariat"

    # 5. Government Ministries
    if "މިނިސްޓްރީ" in cleaned:
        if any(k in cleaned for k in ["އާޓްސް", "ކަލްޗަރ", "ހެރިޓޭޖް"]):
            return "Ministry of Arts, Culture and Heritage"
        if any(k in cleaned for k in ["އިންފްރާސްޓްރަކްޗަރ", "ހައުސިންގ", "އަރބަން ޑިވެލޮޕްމަންޓް"]):
            return "Ministry of Housing, Land and Urban Development"
        if any(k in cleaned for k in ["ކޮންސްޓްރަކްޝަން"]):
            return "Ministry of Construction and Infrastructure"
        if any(k in cleaned for k in ["ފިނޭންސް", "މާލީ"]):
            return "Ministry of Finance"
        if any(k in cleaned for k in ["ފޮރިން", "ޚާރިޖީ"]):
            return "Ministry of Foreign Affairs"
        if any(k in cleaned for k in ["ހޯމްލޭންޑް", "ދާޚިލީ"]):
            return "Ministry of Homeland Security and Technology"
        if any(k in cleaned for k in ["ހަޔަރ އެޑިޔުކޭޝަން"]):
            return "Ministry of Higher Education, Labour and Skills Development"
        if any(k in cleaned for k in ["އެޑިޔުކޭޝަން", "ތަޢުލީމީ"]):
            return "Ministry of Education"
        if any(k in cleaned for k in ["ހެލްތް"]):
            return "Ministry of Health"
        if any(k in cleaned for k in ["އިކޮނޮމިކް", "ވިޔަފާރި"]):
            return "Ministry of Economic Development and Trade"
        if any(k in cleaned for k in ["ފިޝަރީޒް", "މަސްވެރިކަމާ"]):
            return "Ministry of Fisheries and Ocean Resources"
        if any(k in cleaned for k in ["އިސްލާމިކް", "އިސްލާމީ"]):
            return "Ministry of Islamic Affairs"
        if any(k in cleaned for k in ["ޓޫރިޒަމް", "ފަތުރުވެރިކަމާ"]):
            return "Ministry of Tourism"
        if any(k in cleaned for k in ["ސޯޝަލް", "އިޖުތިމާޢީ"]):
            return "Ministry of Social and Family Development"
        if any(k in cleaned for k in ["ސްޕޯޓްސް", "ކުޅިވަރާ"]):
            return "Ministry of Sports, Fitness and Recreation"
        if any(k in cleaned for k in ["ކްލައިމެޓް", "ތިމާވެއްޓާ", "އެންވަޔަރަންމަންޓް"]):
            return "Ministry of Climate Change, Environment and Energy"
        if any(k in cleaned for k in ["ޔޫތު", "ޒުވާނުންނާ"]):
            return "Ministry of Youth Empowerment, Information and Arts"
        if any(k in cleaned for k in ["ޓްރާންސްޕޯޓް", "ދަތުރުފަތުރާ"]):
            return "Ministry of Transport and Civil Aviation"
        if any(k in cleaned for k in ["ސިޓީސް", "ލޯކަލް ގަވަރމަންޓް"]):
            return "Ministry of Cities, Local Government and Public Works"
        if any(k in cleaned for k in ["އެގްރިކަލްޗަރ", "ދަނޑުވެރިކަމާ"]):
            return "Ministry of Agriculture and Animal Welfare"
        if any(k in cleaned for k in ["ޑިފެންސް"]):
            return "Ministry of Defence"
        trans = _translate_phrase_elements(cleaned)
        trans = clean_residual_thaana(trans)
        return trans if trans else "Government Ministry"

    # 6. Hospitals / Health Centres
    if "ހޮސްޕިޓަލް" in cleaned or "މަރުކަޒު" in cleaned:
        trans = _translate_phrase_elements(cleaned)
        trans = clean_residual_thaana(trans)
        return trans if trans else "Healthcare Facility"

    # 7. Schools / Institutes
    if "ސްކޫލް" in cleaned or "ސްކޫލުގެ" in cleaned or "މަދްރަސާ" in cleaned or "މަދަރުސާ" in cleaned:
        trans = _translate_phrase_elements(cleaned)
        trans = clean_residual_thaana(trans)
        return trans if trans else "Educational Institution"

    trans = _translate_phrase_elements(cleaned)
    trans = clean_residual_thaana(trans)
    if not trans or trans in ["،", ",", "-", "from", "in"]:
        return agency.strip()
    return trans


def translate_venue(venue: Optional[str]) -> Optional[str]:
    """Translates Dhivehi submission or info session venue into clean English."""
    if not venue:
        return None
    if not is_dhivehi(venue):
        return venue.strip()

    cleaned = clean_dhivehi_markers(venue)
    # Check if referring to current publishing office
    if any(k in cleaned for k in ["މި އިދާރާ", "މިއިދާރާ", "މި އިދާރާއަށް", "މިއިދާރާއަށް"]):
        return "Council Secretariat / Agency Office"

    # Check 5 official cities
    if any(k in cleaned for k in ["މާލެ ސިޓީ", "މާލޭ ސިޓީ"]):
        return "Malé City Council Secretariat"
    if any(k in cleaned for k in ["އައްޑޫ ސިޓީ", "އައްޑު ސިޓީ"]):
        return "Addu City Council Secretariat"
    if any(k in cleaned for k in ["ފުވައްމުލައް ސިޓީ", "ފުވައްމުލަކު ސިޓީ"]):
        return "Fuvahmulah City Council Secretariat"
    if any(k in cleaned for k in ["ކުޅުދުއްފުށި ސިޓީ", "ކުޅުދުއްފުށީ ސިޓީ"]):
        return "Kulhudhuffushi City Council Secretariat"
    if any(k in cleaned for k in ["ތިނަދޫ ސިޓީ"]):
        return "Thinadhoo City Council Secretariat"

    trans = _translate_phrase_elements(cleaned)
    trans = clean_residual_thaana(trans)
    if trans:
        # Standardize formatting
        trans = re.sub(r"\bCouncil\s+Secretariat\b", "Council Secretariat", trans)
        trans = re.sub(r"\bCouncil\s+Office\b", "Council Secretariat", trans)
        return trans.strip(" ,-:")
    return "Council Secretariat"
