"""
Procurement Discipline and Nature Classifier for Gazette notices.
"""
from __future__ import annotations

import re
from typing import Optional


DISCIPLINE_KEYWORDS = {
    "Water & Sanitation": [
        "water system", "hdpe", "water tank", "storage tank", "water purifier",
        "sewerage", "ro plant", "purifier dispenser", "connection items",
        "water supply", "borehole drilling", "plumbing", "ފެނާއި ނަރުދަމާ", "ފެން",
    ],
    "Power & Electrical": [
        "powerhouse", "genset", "generator", "substation", "cable",
        "transformer", "solar", "battery", "forklift batteries", "electrical",
        "power", "lighting", "mv cable", "lv cable", "އިންޖީނު", "ކަރަންޓު",
    ],
    "Fire Safety & Security": [
        "fire", "fire safety", "fire extinguisher", "alarm", "security service",
        "security services", "cctv", "surveillance", "guarding", "ސެކިއުރިޓީ", "ސެކެއުރިޓީ",
    ],
    "Logistics & Transport": [
        "transportation", "transport", "cargo", "vessel", "dhoani",
        "boat", "forklift", "buggy", "logistics", "freight", "mobilization",
        "ދަތުރުފަތުރު", "އުޅަނދު",
    ],
    "Cleaning & Waste Management": [
        "waste", "thilafushi", "cleaning", "disposal", "waste dump",
        "garbage", "janitorial", "ކުނި", "ސާފުކުރުން",
    ],
    "Supplies & Consumables": [
        "stationery", "tissue", "paper", "cleaning materials", "consumables",
        "uniform", "uniforms", "trophy", "plaques", "ޔުނިފޯމް", "ސްޓޭޝަނަރީ",
    ],
    "Accounting & Legal": [
        "audit", "accounting", "financial", "insurance", "legal", "valuation",
        "tax", "އޮޑިޓް", "އިންޝުއަރަންސް",
    ],
    "Construction": [
        "construction", "build", "finishing work", "renovation", "harbour",
        "harbor", "road", "jetty", "building", "civil works", "infrastructure",
        "boundary fence", "asphalt", "reconstruction", "extension of", "fabrication",
        "ޢިމާރާތް", "ބަނދަރު", "މަގުހެދުން", "ފާރު",
    ],
    "IT": [
        "software", "network", "server", "it equipment", "information technology",
        "database", "website", "digital", "computer", "laptop",
        "e-signature", "contract management system", "fiber", "dark fiber",
        "cctv surveillance", "it hardware", "virtual booth",
        "ކޮމްޕިއުޓަރ", "ސޮފްޓްވެއަރ",
    ],
    "Medical": [
        "medical", "hospital", "health", "pharmaceutical", "ambulance",
        "clinic", "dialysis", "laboratory", "medicine", "pharmacy",
        "ޞިއްޙީ", "ސިއްހީ", "ހޮސްޕިޓަލް", "ބޭސް",
    ],
    "Real Estate & Leasing": [
        "lease", "leasing", "tourist resort", "guesthouse", "guest house",
        "island lease", "space leasing", "rent", "ކުއްޔަށް", "ދަނޑު", "ބިން",
    ],
}


def classify_discipline(title: str) -> str:
    t = title.lower()
    for discipline, keywords in DISCIPLINE_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return discipline
    return "Other"


def classify_procurement(title: str, body: Optional[str] = None) -> tuple[str, str]:
    """
    Two-tier taxonomy classification:
    Returns (procurement_nature, discipline)
    where procurement_nature is 'Service', 'Supply', or 'Lease',
    and discipline is the granular sector/category.
    """
    t = f"{title} {body or ''}".lower()

    # 1. Lease
    if re.search(r"\b(?:lease|leasing|rent|rental|sublease)\b", t) or re.search(r"\b(?:ކުއްޔަށް|ދަނޑު\s*ކުއްޔަށް)\b", t):
        return "Lease", "Real Estate & Leasing"

    # 2. Check granular signals for Service vs Supply
    # Uniforms & Apparel (Supply)
    if re.search(r"\b(?:uniforms?|activity uniforms?|clothing|tailoring)\b", t) or re.search(r"\b(?:ޔުނިފޯމް|ފަހައި)\b", t):
        return "Supply", "Uniforms & Apparel"

    # General Consumables (Tissue, Stationery, Cleaning Items) (Supply)
    if re.search(r"\b(?:tissue|stationery|paper|detergent|cleaning materials|consumables|toilet rolls?|toiletries|office supplies)\b", t) or re.search(r"\b(?:ސްޓޭޝަނަރީ|ކަރުދާސް|ސްޓޮކަށް)\b", t):
        return "Supply", "General Consumables & Office Supplies"

    # Cleaning & Waste Management (Service)
    if re.search(r"\b(?:waste|thilafushi|garbage|cleaning worksites|janitorial|waste transfer)\b", t) or re.search(r"\b(?:ކުނި|ސާފުކުރުން|ތިލަފުއްޓަށް)\b", t):
        return "Service", "Cleaning & Waste Management"

    # Security & Guarding (Service)
    if re.search(r"\b(?:security services?|guarding|security personnel)\b", t) or re.search(r"\b(?:ސެކިއުރިޓީ|ބެލެހެއްޓުން)\b", t):
        return "Service", "Fire Safety & Security"

    # Fire Safety & Security Gear (Supply)
    if re.search(r"\b(?:fire safety|fire extinguisher|fire alarm|safety shoes|gumboots|ppe|cctv equipment)\b", t) or re.search(r"\b(?:އަލިފާން|ސަލާމަތީ)\b", t):
        return "Supply", "Fire Safety & Security"

    # Vehicles & Heavy Machinery (Supply)
    if re.search(r"\b(?:buggy|electric buggy|forklift|excavator|heavy vehicle|tractor|truck)\b", t) or re.search(r"\b(?:ބަގީ|އުޅަނދު)\b", t):
        return "Supply", "Logistics & Transport"

    # Logistics & Transport (Service)
    if re.search(r"\b(?:transportation|ferry|freight|cargo|vessel charter|speedboat hire)\b", t) or re.search(r"\b(?:ދަތުރުފަތުރު)\b", t):
        return "Service", "Logistics & Transport"

    # Medical & Pharma (Supply)
    if re.search(r"\b(?:medical|medicine|pharmaceutical|hospital equipment|dialysis|lab reagents)\b", t) or re.search(r"\b(?:ޞިއްޙީ|ސިއްހީ|ބޭސް|ހޮސްޕިޓަލް)\b", t):
        return "Supply", "Medical"

    # Power & Electrical Equipment (Supply)
    if re.search(r"\b(?:transformers?|cables?|gensets?|substations?|switchgears?|solar panels?)\b", t) or re.search(r"\b(?:ކަރަންޓު|ޓްރާންސްފޯމަރ)\b", t):
        return "Supply", "Power & Electrical"

    # Repair & Maintenance (Service)
    if re.search(r"\b(?:repair|repairs|servicing|maintenance|overhaul|renovation works)\b", t) or re.search(r"\b(?:މަރާމާތު|ސަރވިސް|ބެލެހެއްޓުން)\b", t):
        return "Service", "Repair & Maintenance"

    # Construction Materials & Hardware (Supply)
    if re.search(r"\b(?:hdpe|pipes?|water tanks?|storage tanks?|cement|timber|asphalt|traffic signs?|traffic boards?)\b", t) or re.search(r"\b(?:ބޯޑު|ފެންޓޭންކް|ހޮޅި)\b", t):
        return "Supply", "Construction"

    # Construction & Infrastructure (Service)
    if re.search(r"\b(?:construction|civil works|harbour|harbor|jetty|roads?|building works?|masonry|fence)\b", t) or re.search(r"\b(?:ޢިމާރާތް|ބަނދަރު|މަގުހެދުން|ފާރު)\b", t):
        return "Service", "Construction"

    # IT & Digital Services vs Hardware
    if re.search(r"\b(?:sap|software development|ams|application management|network setup|dark fiber link)\b", t):
        return "Service", "IT"
    if re.search(r"\b(?:computers?|laptops?|servers?|it hardware|virtual booth|monitors?|printers?)\b", t) or re.search(r"\b(?:ކޮމްޕިއުޓަރ|ސޮފްޓްވެއަރ)\b", t):
        return "Supply", "IT"

    # Accounting, Audit & Legal (Service)
    if re.search(r"\b(?:audit|auditing|accounting|valuation|tax advisory|legal counsel|insurance coverage)\b", t) or re.search(r"\b(?:އޮޑިޓް|އިންޝުއަރަންސް)\b", t):
        return "Service", "Accounting & Legal"

    # Catering & Events (Service)
    if re.search(r"\b(?:catering|meals|event management|stage|lighting|sound system)\b", t) or re.search(r"\b(?:ކެއުން|ސްޓޭޖް)\b", t):
        return "Service", "Catering & Events"

    # Consultancy & Design (Service)
    if re.search(r"\b(?:consultancy|consultant|logo design|architectural design|eia)\b", t) or re.search(r"\b(?:ފަރުމާ)\b", t):
        return "Service", "Consultancy & Design"

    # Air conditioner logic
    if "އޭސީ" in t or "air conditioner" in t:
        if "ސަރވިސް" in t or "service" in t or "maintenance" in t:
            return "Service", "Repair & Maintenance"
        return "Supply", "Power & Electrical"

    # Fallback to dictionary
    disc = classify_discipline(title)
    is_service = bool(re.search(r"\b(?:services?|works?|maintenance|repair|cleaning|security|transport|audit|consultancy|މަސައްކަތް|ސަރވިސް)\b", t))
    nature = "Service" if is_service else "Supply"
    return nature, disc


# ---------------------------------------------------------------------
