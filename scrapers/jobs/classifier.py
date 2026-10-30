"""
Maldivian Job Discipline Classifier and Dhivehi-to-English Job Title Translator.
Pure classification and translation functions with zero database or network side effects.
"""
from __future__ import annotations

import re

from scrapers.translator import clean_dhivehi_markers, clean_residual_thaana

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

DISCIPLINE_TAXONOMY = ROLE_TAXONOMY


def classify_job_discipline(title: str, agency: str = "", body: str = "") -> str:
    """Classify job into a standardized Maldivian employment sector."""
    clean_title = (title or "").lower().strip()
    clean_agency = (agency or "").lower().strip()
    clean_body = (body or "").lower().strip()

    for disc, keywords in ROLE_TAXONOMY.items():
        sorted_kws = sorted(keywords, key=len, reverse=True)
        for kw in sorted_kws:
            pattern = r"(?:^|\W)" + re.escape(kw) + r"(?:$|\W)"
            if re.search(pattern, clean_title) or kw in clean_title:
                return disc

    combined_context = f"{clean_agency} {clean_body}"
    for disc, keywords in CONTEXT_TAXONOMY.items():
        sorted_kws = sorted(keywords, key=len, reverse=True)
        for kw in sorted_kws:
            pattern = r"(?:^|\W)" + re.escape(kw) + r"(?:$|\W)"
            if re.search(pattern, combined_context) or kw in combined_context:
                return disc

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
    text = clean_dhivehi_markers(title_dv)
    for dv, en in JOB_TITLE_PHRASE_TRANSLATIONS:
        text = text.replace(dv, en)
    cleaned = clean_residual_thaana(text)
    return cleaned if cleaned else title_dv
