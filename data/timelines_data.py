"""
Historical Timelines and Tag Milestones for Khulaasaa stories.
"""
from typing import Any

TIMELINES: dict[str, dict[str, Any]] = {

    "ras-male-project": {
        "story_id": "ras-male-project",
        "title": "Ras Malé Land Reclamation & Eco-City",
        "tag": "ras-male",
        "milestones": [
            {
                "id": "m-rm-1",
                "date_raw": "14 Oct 2026",
                "date_iso": "2026-10-14",
                "headline": "Reclamation reaches major acreage milestone at Fushidhiggaru Falhu",
                "detail": (
                    "High-capacity trailing suction hopper dredgers accelerate sand pumping "
                    "operations at Fushidhiggaru Falhu to deliver over 1,150 hectares of land "
                    "for the national housing programme."
                ),
                "sources": ["standard", "sun", "psm"],
                "url": "https://standard.mv/ras-male-fushidhiggaru-falhu-land-reclamation-launch/",
            },
            {
                "id": "m-rm-2",
                "date_raw": "28 Sep 2026",
                "date_iso": "2026-09-28",
                "headline": "Government signs infrastructure agreements for zero-carbon transport corridors",
                "detail": (
                    "Agreements formalized with international engineering partners to develop "
                    "solar-powered rapid transit lines linking Ras Malé with Hulhumalé and Malé."
                ),
                "sources": ["atolltimes", "dhauru"],
                "url": "https://atolltimes.mv/post/business/17390",
            },
            {
                "id": "m-rm-3",
                "date_raw": "18 Dec 2023",
                "date_iso": "2023-12-18",
                "headline": "President Dr. Mohamed Muizzu officially inaugurates Ras Malé Project",
                "detail": (
                    "The flagship zero-carbon eco-city development is launched with a pledge "
                    "to provide 30,000 residential housing units raised 3 meters above sea level."
                ),
                "sources": ["psm", "sun", "adhadhu"],
                "url": "https://psmnews.mv/189204",
            },
        ],
    },
    "male-traffic-ban": {
        "story_id": "male-traffic-ban",
        "title": "Greater Malé Heavy Vehicle School & Peak Hour Ban",
        "tag": "traffic-reform",
        "milestones": [
            {
                "id": "m-tb-1",
                "date_raw": "15 Oct 2026",
                "date_iso": "2026-10-15",
                "headline": "Transport Ministry prohibits heavy vehicles during school & peak hours",
                "detail": (
                    "Heavy trucks above C1 classification and goods vehicles are strictly prohibited "
                    "from operating in Malé and Hulhumalé arterial corridors during school start and "
                    "dismissal windows to enhance child pedestrian safety."
                ),
                "sources": ["standard", "sun", "dhauru"],
                "url": "https://standard.mv/heavy-vehicles-and-goods-transport-restricted-during-peak-hours-in-greater-male/",
            },
            {
                "id": "m-tb-2",
                "date_raw": "12 Oct 2026",
                "date_iso": "2026-10-12",
                "headline": "Police Traffic Management Department deploys speed & weight checkpoints",
                "detail": (
                    "Maldives Police Service sets up continuous surveillance points along the Sinamalé "
                    "Bridge Highway and Boduthakurufaanu Magu to curb speeding commercial vehicles."
                ),
                "sources": ["mvcrisis", "sun"],
                "url": "https://t.me/MvCrisis/114537",
            },
            {
                "id": "m-tb-3",
                "date_raw": "02 Oct 2026",
                "date_iso": "2026-10-02",
                "headline": "Logistics and wholesale merchants consulted on designated night delivery slots",
                "detail": (
                    "Transport authorities hold stakeholder sessions with the business community "
                    "to establish clear night-time offloading windows for commercial goods."
                ),
                "sources": ["standard", "haftha"],
                "url": "https://haftha.mv/48190/",
            },
        ],
    },
    "fenaka-stelco-merger": {
        "story_id": "fenaka-stelco-merger",
        "title": "Utility Restructuring: STELCO & Fenaka",
        "tag": "utility-merger",
        "milestones": [
            {
                "id": "m-fs-1",
                "date_raw": "15 Oct 2026",
                "date_iso": "2026-10-15",
                "headline": "Fenaka management officially handed over to STELCO MD Dr. Ali Azwar",
                "detail": (
                    "Operational administration of Fenaka Corporation is handed over to STELCO MD "
                    "Dr. Ali Azwar as the government accelerates the merger of island power grids."
                ),
                "sources": ["standard", "sun", "psm", "atolltimes"],
                "url": "https://standard.mv/fenaka-management-handed-over-to-stelco-md-dr-ali-azwar/",
            },
            {
                "id": "m-fs-2",
                "date_raw": "28 Aug 2026",
                "date_iso": "2026-08-28",
                "headline": "Cabinet approves formal absorption of Fenaka Corporation under STELCO",
                "detail": (
                    "In a major state-owned enterprise (SOE) reform drive, the Cabinet resolves "
                    "to eliminate redundant administrative expenditures and modernize fuel distribution."
                ),
                "sources": ["sun", "dhauru", "psm"],
                "url": "https://sun.mv/228940",
            },
        ],
    },
    "sultan-park-project": {
        "story_id": "sultan-park-project",
        "title": "Sultan Park & Historic Usgekolhu Redevelopment",
        "tag": "sultan-park",
        "milestones": [
            {
                "id": "m-sp-1",
                "date_raw": "15 Oct 2026",
                "date_iso": "2026-10-15",
                "headline": "Male' City Council and Ministry unveil comprehensive Sultan Park restoration plan",
                "detail": (
                    "A joint initiative is launched to restore Sultan Park's historical botanical gardens "
                    "and the royal Usgekolhu palace wing with upgraded child play zones and heritage trails."
                ),
                "sources": ["standard", "sun", "dhauru"],
                "url": "https://standard.mv/male-city-council-and-ministry-unveil-sultan-park-restoration-plan/",
            },
            {
                "id": "m-sp-2",
                "date_raw": "22 Sep 2026",
                "date_iso": "2026-09-22",
                "headline": "Heritage Department completes architectural survey of ancient palace grounds",
                "detail": (
                    "Archaeological and conservation teams complete 3D laser scans of the remaining "
                    "sultanate pavilion to safeguard original wood carvings prior to civil enhancements."
                ),
                "sources": ["psm", "atolltimes"],
                "url": "https://psmnews.mv/189450",
            },
        ],
    },
    "tgst-tax-reform": {
        "story_id": "tgst-tax-reform",
        "title": "TGST Rate Revision & Tourism Sector Tax Adjustments",
        "tag": "tgst-tax",
        "milestones": [
            {
                "id": "m-tg-1",
                "date_raw": "14 Oct 2026",
                "date_iso": "2026-10-14",
                "headline": "Finance Ministry tables Tourism Goods and Services Tax amendment in Parliament",
                "detail": (
                    "Legislation is introduced to adjust the TGST rate to 17% for high-end resort "
                    "accommodations, aligning state revenue targets with national debt amortization."
                ),
                "sources": ["standard", "atolltimes", "sun"],
                "url": "https://standard.mv/finance-ministry-tables-tourism-goods-and-services-tax-amendment/",
            },
            {
                "id": "m-tg-2",
                "date_raw": "05 Sep 2026",
                "date_iso": "2026-09-05",
                "headline": "MATI and Ministry of Tourism conduct joint consultation on tax harmonization",
                "detail": (
                    "Tourism stakeholders review draft tax schedules, emphasizing advance booking windows "
                    "and price competitiveness across European travel markets."
                ),
                "sources": ["dhauru", "haftha"],
                "url": "https://dhauru.com/post/news/46210",
            },
        ],
    },
    "green-tax-reform": {
        "story_id": "green-tax-reform",
        "title": "Green Tax Revision & Coral Conservation Levies",
        "tag": "green-tax",
        "milestones": [
            {
                "id": "m-gt-1",
                "date_raw": "13 Oct 2026",
                "date_iso": "2026-10-13",
                "headline": "Cabinet proposes revised Green Tax framework to fund island coastal defense",
                "detail": (
                    "A revised daily Green Tax tariff is submitted to parliament to accelerate "
                    "island climate adaptation, sea-wall defense, and renewable energy conversion."
                ),
                "sources": ["standard", "psm", "sun"],
                "url": "https://standard.mv/cabinet-proposes-revised-green-tax-framework-for-coastal-defense/",
            },
            {
                "id": "m-gt-2",
                "date_raw": "18 Aug 2026",
                "date_iso": "2026-08-18",
                "headline": "MIRA reports total Green Fund disbursements for atoll solar mini-grids",
                "detail": (
                    "Maldives Inland Revenue Authority publishes fiscal records confirming $45 million "
                    "in Green Tax proceeds directed toward outer island hybrid electricity generation."
                ),
                "sources": ["atolltimes", "dhauru"],
                "url": "https://atolltimes.mv/post/business/17450",
            },
        ],
    },
    "sinamale-bridge-incidents": {
        "story_id": "sinamale-bridge-incidents",
        "title": "Sinamalé Bridge & Highway Traffic Safety Track",
        "tag": "bridge-safety",
        "milestones": [
            {
                "id": "m-br-1",
                "date_raw": "15 Oct 2026",
                "date_iso": "2026-10-15",
                "headline": "Transport Ministry deploys automated speed enforcement on Sinamalé Bridge Highway",
                "detail": (
                    "High-speed radar cameras and median barrier reinforcements are activated "
                    "following recurring collisions during peak commuter hours."
                ),
                "sources": ["standard", "sun", "mvcrisis"],
                "url": "https://standard.mv/transport-ministry-deploys-automated-speed-enforcement-sinamale-bridge/",
            },
            {
                "id": "m-br-2",
                "date_raw": "11 Oct 2026",
                "date_iso": "2026-10-11",
                "headline": "Multi-car collision on bridge highway causes traffic diversion into Hulhumalé",
                "detail": (
                    "Police Traffic Command cordons two lanes on the bridge approach as emergency "
                    "services assist injured commuters and clear wreckage."
                ),
                "sources": ["mvcrisis", "atolltimes", "dhauru"],
                "url": "https://t.me/MvCrisis/114512",
            },
        ],
    },
    "presidential-speeches": {
        "story_id": "presidential-speeches",
        "title": "President Dr. Mohamed Muizzu National Statements & Directives",
        "tag": "presidential-speeches",
        "milestones": [
            {
                "id": "m-pm-1",
                "date_raw": "15 Oct 2026",
                "date_iso": "2026-10-15",
                "headline": "President Dr. Muizzu affirms commitment to housing rights and economic self-reliance",
                "detail": (
                    "In a major national address, President Dr. Mohamed Muizzu underscores housing delivery "
                    "in Ras Malé and Hulhumalé while outlining ongoing state fiscal governance reforms."
                ),
                "sources": ["psm", "sun", "standard", "dhauru"],
                "url": "https://psmnews.mv/189720",
            },
            {
                "id": "m-pm-2",
                "date_raw": "02 Oct 2026",
                "date_iso": "2026-10-02",
                "headline": "President pledges completion of regional healthcare hubs across northern atolls",
                "detail": (
                    "President announces the upgrading of Kulhudhuffushi and Ungoofaaru regional hospitals "
                    "into tertiary-tier diagnostic and surgical centers."
                ),
                "sources": ["standard", "haftha"],
                "url": "https://standard.mv/president-pledges-completion-of-regional-healthcare-hubs/",
            },
        ],
    },
}

# --- Baseline Verified Events (Used for Initial Feed / Fallback) --------------