"""
Default and fallback events, and seed job postings for offline/initial state.
"""
from datetime import datetime, timezone
from typing import Any

DEFAULT_EVENTS: list[dict[str, Any]] = [
{
        "id": "evt-live-1",
        "headline": "Heavy vehicles and goods transport restricted during peak hours in Greater Malé",
        "summary": (
            "The Ministry of Transport and Civil Aviation has restricted the operation of heavy "
            "vehicles and goods transport vehicles in the Greater Malé area during peak hours, "
            "particularly around school opening and closing times."
        ),
        "published_raw": "15 Oct 2026, 14:30",
        "published_iso": "2026-10-15T14:30:00Z",
        "minutes_ago": 45,
        "sources": ["standard", "sun", "dhauru"],
        "source_links": {
            "standard": "https://standard.mv/heavy-vehicles-and-goods-transport-restricted-during-peak-hours-in-greater-male/",
            "sun": "https://sun.mv/229015",
            "dhauru": "https://dhauru.com/post/news/46380",
        },
        "url": "https://standard.mv/heavy-vehicles-and-goods-transport-restricted-during-peak-hours-in-greater-male/",
        "tags": ["traffic-reform"],
        "section": "major",
        "story_id": "male-traffic-ban",
        "topic": "policy",
    },
    {
        "id": "evt-live-2",
        "headline": "Fenaka management officially handed over to STELCO MD Dr. Ali Azwar",
        "summary": (
            "The operational leadership of Fenaka Corporation has been officially transferred to "
            "STELCO Managing Director Dr. Ali Azwar following Cabinet approval to merge the two "
            "primary state electricity and utility providers."
        ),
        "published_raw": "15 Oct 2026, 12:15",
        "published_iso": "2026-10-15T12:15:00Z",
        "minutes_ago": 180,
        "sources": ["standard", "sun", "psm", "atolltimes", "dhauru", "haftha"],
        "source_links": {
            "standard": "https://standard.mv/fenaka-management-handed-over-to-stelco-md-dr-ali-azwar/",
            "sun": "https://sun.mv/229143",
            "psm": "https://psmnews.mv/190258",
            "atolltimes": "https://atolltimes.mv/post/business/17422",
            "dhauru": "https://dhauru.com/post/news/46444",
            "haftha": "https://haftha.mv/48347/",
        },
        "url": "https://standard.mv/fenaka-management-handed-over-to-stelco-md-dr-ali-azwar/",
        "tags": ["utility-merger"],
        "section": "major",
        "story_id": "fenaka-stelco-merger",
        "topic": "economy",
    },
    {
        "id": "evt-live-3",
        "headline": "Police arrest Maldivian kingpin heading major alcohol supply network in Malé",
        "summary": (
            "Maldives Police Service has apprehended the Maldivian ringleader heading an extensive "
            "illicit alcohol distribution network across the capital city, seizing substantial stock."
        ),
        "published_raw": "15 Oct 2026, 11:20",
        "published_iso": "2026-10-15T11:20:00Z",
        "minutes_ago": 230,
        "sources": ["atolltimes", "dhauru", "haftha", "mvcrisis"],
        "source_links": {
            "atolltimes": "https://atolltimes.mv/post/news/17425",
            "dhauru": "https://dhauru.com/post/news/46448",
            "haftha": "https://haftha.mv/48365/",
            "mvcrisis": "https://t.me/MvCrisis/114537",
        },
        "url": "https://atolltimes.mv/post/news/17425",
        "tags": ["atoll-operations"],
        "section": "major",
        "topic": "crime",
    },
    {
        "id": "evt-live-4",
        "headline": "Ras Malé land reclamation accelerates with international dredger fleet",
        "summary": (
            "High-capacity trailing suction hopper dredgers are operating around the clock at "
            "Fushidhiggaru Falhu to deliver the core reclamation targets for the Ras Malé eco-city."
        ),
        "published_raw": "14 Oct 2026, 18:40",
        "published_iso": "2026-10-14T18:40:00Z",
        "minutes_ago": 1200,
        "sources": ["standard", "haftha", "psm"],
        "source_links": {
            "standard": "https://standard.mv/fushidhiggaru-falhu-ras-male-milestone-deep-sea-dredging/",
            "haftha": "https://haftha.mv/48318/",
            "psm": "https://psmnews.mv/190112",
        },
        "url": "https://standard.mv/fushidhiggaru-falhu-ras-male-milestone-deep-sea-dredging/",
        "tags": ["ras-male"],
        "section": "major",
        "story_id": "ras-male-project",
        "topic": "infrastructure",
    },
    {
        "id": "evt-live-5",
        "headline": "President Dr. Muizzu announces official bilateral state visit to Pakistan",
        "summary": (
            "President Dr. Mohamed Muizzu will undertake an official visit to Islamabad next week "
            "to strengthen bilateral trade, civil aviation agreements, and regional cooperation."
        ),
        "published_raw": "15 Oct 2026, 10:05",
        "published_iso": "2026-10-15T10:05:00Z",
        "minutes_ago": 300,
        "sources": ["dhauru", "standard"],
        "source_links": {
            "dhauru": "https://dhauru.com/post/news/46446",
            "standard": "https://standard.mv/president-dr-muizzu-announces-bilateral-state-visit-pakistan/",
        },
        "url": "https://dhauru.com/post/news/46446",
        "tags": ["diplomacy"],
        "section": "major",
        "topic": "policy",
    },
    {
        "id": "evt-live-6",
        "headline": "Three arrested with 13 rubber packets of suspected drugs in Lh. Atoll operation",
        "summary": (
            "Police counter-narcotics division has detained three individuals in possession of 13 "
            "rubber packets filled with suspected illicit substances during a search in Lhaviyani Atoll."
        ),
        "published_raw": "15 Oct 2026, 13:45",
        "published_iso": "2026-10-15T13:45:00Z",
        "minutes_ago": 80,
        "sources": ["mvcrisis"],
        "source_links": {
            "mvcrisis": "https://t.me/MvCrisis/114543",
        },
        "url": "https://t.me/MvCrisis/114543",
        "tags": ["atoll-operations"],
        "section": "breaking",
        "topic": "crime",
    },
    {
        "id": "evt-live-7",
        "headline": "White alert issued for torrential rain and squally winds from Lhaviyani to Addu Atoll",
        "summary": (
            "Maldives Meteorological Service has issued a white alert advising sea travelers and "
            "islanders across central and southern atolls to exercise heightened caution."
        ),
        "published_raw": "15 Oct 2026, 12:30",
        "published_iso": "2026-10-15T12:30:00Z",
        "minutes_ago": 150,
        "sources": ["mvcrisis", "atolltimes"],
        "source_links": {
            "mvcrisis": "https://t.me/MvCrisis/114526",
            "atolltimes": "https://atolltimes.mv/post/news/17420",
        },
        "url": "https://t.me/MvCrisis/114526",
        "tags": [],
        "section": "breaking",
        "topic": "weather",
    },
    {
        "id": "evt-live-8",
        "headline": "Ooredoo Maldives launches nationwide mosque restoration programme ahead of Ramadan",
        "summary": (
            "Partnering with the Ministry of Islamic Affairs, Ooredoo Maldives initiates an extensive "
            "restoration and maintenance drive covering community mosques throughout the islands."
        ),
        "published_raw": "15 Oct 2026, 09:15",
        "published_iso": "2026-10-15T09:15:00Z",
        "minutes_ago": 360,
        "sources": ["standard", "dhauru"],
        "source_links": {
            "standard": "https://standard.mv/ooredoo-launches-nationwide-mosque-renovation-initiative-ahead-of-ramadan/",
            "dhauru": "https://dhauru.com/post/news/46453",
        },
        "url": "https://standard.mv/ooredoo-launches-nationwide-mosque-renovation-initiative-ahead-of-ramadan/",
        "tags": [],
        "section": "general",
        "topic": "policy",
    },
    {
        "id": "evt-sultan-park-1",
        "headline": "Male' City Council and Ministry unveil comprehensive Sultan Park restoration plan",
        "summary": (
            "A joint initiative is launched to restore Sultan Park's historical botanical gardens "
            "and the royal Usgekolhu palace wing with upgraded child play zones and heritage trails."
        ),
        "published_raw": "15 Oct 2026, 11:00",
        "published_iso": "2026-10-15T11:00:00Z",
        "minutes_ago": 180,
        "sources": ["standard", "sun", "dhauru"],
        "source_links": {
            "standard": "https://standard.mv/male-city-council-and-ministry-unveil-sultan-park-restoration-plan/",
            "sun": "https://sun.mv/229330",
            "dhauru": "https://dhauru.com/post/news/46510",
        },
        "url": "https://standard.mv/male-city-council-and-ministry-unveil-sultan-park-restoration-plan/",
        "tags": ["sultan-park"],
        "section": "general",
        "topic": "infrastructure",
    },
]

# Aliased for backward compatibility with existing code
EVENTS = DEFAULT_EVENTS

# --- Public & SOE Job Openings -----------------------------------------------
JOBS: list[dict[str, Any]] = [
    {
        "id": "job-1",
        "title": "Civil Engineer (Infrastructure)",
        "agency": "Ministry of Construction and Infrastructure",
        "discipline": "Construction",
        "location": "Male'",
        "deadline_iso": "2026-10-25T14:00:00",
        "published_raw": "14 Oct 2026",
    },
    {
        "id": "job-2",
        "title": "Senior Network Security Engineer",
        "agency": "Maldives Inland Revenue Authority",
        "discipline": "IT",
        "location": "Male'",
        "deadline_iso": "2026-10-22T13:00:00",
        "published_raw": "13 Oct 2026",
    },
    {
        "id": "job-3",
        "title": "Specialist Medical Officer (Pediatrics)",
        "agency": "Indira Gandhi Memorial Hospital",
        "discipline": "Medical",
        "location": "Male'",
        "deadline_iso": "2026-10-30T13:00:00",
        "published_raw": "12 Oct 2026",
    },
    {
        "id": "job-4",
        "title": "Electrical Power Systems Project Manager",
        "agency": "State Electric Company Limited (STELCO)",
        "discipline": "Power & Electrical",
        "location": "Male'",
        "deadline_iso": "2026-10-28T14:00:00",
        "published_raw": "11 Oct 2026",
    },
    {
        "id": "job-5",
        "title": "Senior Procurement Officer",
        "agency": "Housing Development Corporation",
        "discipline": "Finance",
        "location": "Hulhumale'",
        "deadline_iso": "2026-10-20T13:00:00",
        "published_raw": "10 Oct 2026",
    },
    {
        "id": "job-6",
        "title": "Marine Biologist & Environmental Surveyor",
        "agency": "Environmental Protection Agency (EPA)",
        "discipline": "Environment",
        "location": "Male'",
        "deadline_iso": "2026-10-24T14:00:00",
        "published_raw": "09 Oct 2026",
    },
]

# --- Editorial Moderation Queue for Story Clusters ---------------------------
PENDING_CLUSTERS: list[dict[str, Any]] = [
    {
        "id": "cluster-601",
        "draft_headline": "Transport Ministry introduces rush-hour commercial vehicle restrictions",
        "article_count": 3,
        "sources": ["standard", "sun", "dhauru"],
        "suggested_tags": ["traffic-reform"],
        "confidence": 0.94,
        "received_raw": "15 Oct 2026, 14:35",
    },
    {
        "id": "cluster-602",
        "draft_headline": "Fenaka Corporation executive operations transferred to STELCO management",
        "article_count": 5,
        "sources": ["standard", "sun", "psm", "atolltimes", "dhauru"],
        "suggested_tags": ["utility-merger"],
        "confidence": 0.96,
        "received_raw": "15 Oct 2026, 12:25",
    },
    {
        "id": "cluster-603",
        "draft_headline": "Police crack down on illicit capital supply network with major arrests",
        "article_count": 4,
        "sources": ["atolltimes", "dhauru", "haftha", "mvcrisis"],
        "suggested_tags": ["atoll-operations"],
        "confidence": 0.89,
        "received_raw": "15 Oct 2026, 11:30",
    },
]

APPROVAL_LOG: list[dict[str, Any]] = []


def approve_cluster(cluster_id: str, tag_ids: list[str]) -> dict[str, Any]:
    """Approve a proposed cluster in the editorial queue."""
    entry = {
        "cluster_id": cluster_id,
        "tags": tag_ids,
        "approved_at": datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z",
    }
    APPROVAL_LOG.append(entry)
    global PENDING_CLUSTERS
    PENDING_CLUSTERS = [c for c in PENDING_CLUSTERS if c["id"] != cluster_id]
    return entry