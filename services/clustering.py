"""
News Clustering & Semantic Grouping Service.
Handles editorial running story matching and dynamic cross-media n-gram semantic entity clustering.
"""
from __future__ import annotations

import re
from typing import Any

from core.time_utils import format_relative_time
from scrapers.transliterate import is_latin_dhivehi
from scrapers.translator import is_dhivehi, translate_dhivehi_title

KNOWN_STORY_CLUSTERS = [
    {
        "id": "cluster-male-traffic-ban",
        "tag": "traffic-reform",
        "story_id": "male-traffic-ban",
        "topic": "policy",
        "headline": "Heavy vehicles and goods transport restricted during peak hours in Greater Malé",
        "summary": "The Ministry of Transport has restricted heavy vehicle operations and commercial goods transport in Malé and Hulhumalé during morning and afternoon school hours to curb traffic congestion and enhance pedestrian safety.",
        "keywords": [
            "heavy vehicle", "heavy vehicles", "goods transport", "peak hours", "school hours", "rush hour",
            "traffic ban", "traffic restriction", "school time", "ބޮޑެތި އުޅަނދު", "ސްކޫލް ވަގުތު", "ގަޑިއަކު 106"
        ],
    },
    {
        "id": "cluster-fenaka-afeef",
        "tag": "utility-merger",
        "story_id": "fenaka-stelco-merger",
        "topic": "economy",
        "headline": "Fenaka MD Afeef appointed State Minister following restructuring",
        "summary": "Following the decision to restructure and consolidate island utility operations under STELCO, former Fenaka Managing Director Muaz Mohamed Rasheed / Afeef has been appointed as a State Minister at the Ministry of Climate Change, Environment and Energy.",
        "keywords": [
            "afeef", "އަފީފް", "އަފީފ", "state minister", "ސްޓޭޓް މިނިސްޓަރަކަށް", "އެމްޑީއަކަށް ހުންނެވި އަފީފް", "environment ge state minister"
        ],
    },
    {
        "id": "cluster-fenaka-merger",
        "tag": "utility-merger",
        "story_id": "fenaka-stelco-merger",
        "topic": "economy",
        "headline": "Fenaka management officially handed over to STELCO MD Dr. Ali Azwar",
        "summary": "Management and operational control of Fenaka Corporation has been transferred to STELCO Managing Director Dr. Ali Azwar following Cabinet decisions to restructure and consolidate island utility services.",
        "keywords": [
            "azwar", "އަޒުވަރު", "directorun ge board", "board ah nizam", "ހިންގުން ސްޓެލްކޯގެ އެމްޑީ", "management handed over"
        ],
    },
    {
        "id": "cluster-alcohol-network",
        "tag": "atoll-operations",
        "story_id": None,
        "topic": "crime",
        "headline": "Police arrest Maldivian kingpin heading major alcohol supply network in Malé",
        "summary": "Maldives Police Service has apprehended the Maldivian ringleader in charge of a widespread alcohol supply network across Malé, following multi-day surveillance by counter-narcotics teams.",
        "keywords": [
            "alcohol supply", "alcohol network", "banguraa", "ބަނގުރާ", "ސަޕްލައިކުރާ ނެޓްވޯކު"
        ],
    },
    {
        "id": "cluster-ras-male",
        "tag": "ras-male",
        "story_id": "ras-male-project",
        "topic": "infrastructure",
        "headline": "Ras Malé land reclamation and eco-city development progress",
        "summary": "Reclamation works at Fushidhiggaru Falhu accelerate to deliver key acreage milestones for the government's flagship Ras Malé residential and commercial expansion project.",
        "keywords": [
            "ras male", "rasmale", "fushidhiggaru", "ރަސްމާލެ", "ފުށިދިއްގަރު", "މެރީނާ މަޝްރޫއު"
        ],
    },
    {
        "id": "cluster-eagle-hills",
        "tag": "diplomacy",
        "story_id": None,
        "topic": "policy",
        "headline": "Calls mount for government transparency over Eagle Hills bilateral agreement",
        "summary": "Political parties and parliamentarians call on the administration to publish full terms of the development agreement signed with Abu Dhabi-based Eagle Hills.",
        "keywords": [
            "eagle hills", "އީގަލް ހިލްސް", "އީގަލްހިލްސް"
        ],
    },
    {
        "id": "cluster-ooredoo-mosque",
        "tag": None,
        "story_id": None,
        "topic": "policy",
        "headline": "Ooredoo Maldives partners with Islamic Ministry on nationwide mosque renovation drive",
        "summary": "Ooredoo Maldives launches an island-wide initiative alongside the Ministry of Islamic Affairs to restore and maintain community mosques prior to Ramadan.",
        "keywords": [
            "ooredoo", "mosque", "miskiy", "މިސްކިތް", "އުރީދޫ"
        ],
    },
    {
        "id": "cluster-rdc-mtcc",
        "tag": "utility-merger",
        "story_id": None,
        "topic": "policy",
        "headline": "RDC managing director removed as operations transition to MTCC under SOE reforms",
        "summary": "Road Development Corporation operations are being transferred to MTCC under the administration's state-owned enterprise consolidation policy.",
        "keywords": [
            "rdc", "nazeem", "mtcc", "އާރްޑީސީ"
        ],
    },
    {
        "id": "cluster-aman-towers",
        "tag": None,
        "story_id": None,
        "topic": "policy",
        "headline": "FDC issues eviction notices to Aman Towers flat tenants over rent arrears",
        "summary": "Fahi Dhiriulhun Corporation terminates agreements for social housing units in Hulhumalé Phase II following extended failure to settle monthly rental dues.",
        "keywords": [
            "aman towers", "އެފްޑީސީ", "ކުލި ނުދައްކާތީ"
        ],
    },
    {
        "id": "cluster-guraidhoo-assault",
        "tag": None,
        "story_id": None,
        "topic": "crime",
        "headline": "Violent altercation in K. Guraidhoo leads to stabbing and urgent medical evacuation",
        "summary": "A fight in a residential home on Kaafu Guraidhoo resulted in a severe stabbing injury, with the victim transferred to Malé for emergency medical attention.",
        "keywords": [
            "guraidhoo", "valhin", "stabbing", "ގުރައިދޫ", "ތޫނު"
        ],
    },
    {
        "id": "cluster-muizzu-pakistan",
        "tag": "diplomacy",
        "story_id": None,
        "topic": "policy",
        "headline": "President Dr. Muizzu announces official bilateral state visit to Pakistan",
        "summary": "President Dr. Mohamed Muizzu will undertake a historic state visit to Islamabad next week to review bilateral relations and sign trade and transit agreements.",
        "keywords": [
            "pakistan", "ޕާކިސްތާން"
        ],
    },
    {
        "id": "cluster-sultan-park",
        "tag": "sultan-park",
        "story_id": "sultan-park-project",
        "topic": "infrastructure",
        "headline": "Male' City Council and Ministry unveil comprehensive Sultan Park restoration plan",
        "summary": "A joint initiative is launched to restore Sultan Park's historical botanical grounds and royal Usgekolhu pavilion with upgraded heritage walkways and green public recreation zones.",
        "keywords": [
            "sultan park", "sultanpark", "usgekolhu", "ސަލްޠާން ޕާކް", "ސަލްތާން ޕާކް", "އުސްގެކޮޅު", "sultan faaku"
        ],
    },
    {
        "id": "cluster-tgst-tax",
        "tag": "tgst-tax",
        "story_id": "tgst-tax-reform",
        "topic": "economy",
        "headline": "Finance Ministry tables Tourism Goods and Services Tax amendment in Parliament",
        "summary": "Legislation is introduced to adjust the TGST rate to 17% for high-end resort accommodations, aligning state revenue targets with national debt amortization commitments.",
        "keywords": [
            "tgst", "t-gst", "ޓީޖީއެސްޓީ", "tourism gst", "resort tax", "tax amendment", "ޓޫރިޒަމް ޖީއެސްޓީ"
        ],
    },
    {
        "id": "cluster-green-tax",
        "tag": "green-tax",
        "story_id": "green-tax-reform",
        "topic": "economy",
        "headline": "Cabinet proposes revised Green Tax framework to fund island coastal defense",
        "summary": "A revised daily Green Tax tariff is submitted to parliament to accelerate island climate adaptation, sea-wall defense, and renewable energy conversion across atolls.",
        "keywords": [
            "green tax", "greentax", "ގްރީން ޓެކްސް", "environment levy", "ތިމާވެށި ޓެކްސް"
        ],
    },
    {
        "id": "cluster-bridge-safety",
        "tag": "bridge-safety",
        "story_id": "sinamale-bridge-incidents",
        "topic": "crime",
        "headline": "Transport Ministry deploys automated speed enforcement on Sinamalé Bridge Highway",
        "summary": "High-speed radar cameras and median barrier reinforcements are activated across the Greater Malé bridge corridor following recurring traffic collisions during commuter peak hours.",
        "keywords": [
            "bridge accident", "bridge crash", "highway accident", "sinamale bridge", "ބްރިޖް އެކްސިޑެންޓް", "ބްރިޖް މަތީގައި", "ހައިވޭ އެކްސިޑެންޓް"
        ],
    },
    {
        "id": "cluster-presidential-speeches",
        "tag": "presidential-speeches",
        "story_id": "presidential-speeches",
        "topic": "policy",
        "headline": "President Dr. Muizzu affirms commitment to housing rights and economic self-reliance",
        "summary": "In a major national address, President Dr. Mohamed Muizzu underscores housing delivery in Ras Malé and Hulhumalé while outlining ongoing state fiscal governance reforms.",
        "keywords": [
            "president said", "president remarks", "muizzu said", "presidential address", "ރައީސް ވިދާޅުވީ", "މުއިއްޒު ވިދާޅުވީ", "ރައީސުލްޖުމްހޫރިއްޔާ ވިދާޅުވީ", "ރައީސްގެ ބަޔާން"
        ],
    },
]

SEMANTIC_ENTITY_MAP: dict[str, str] = {
    "afeef": "afeef", "އަފީފް": "afeef", "އަފީފ": "afeef",
    "azwar": "azwar", "އަޒުވަރު": "azwar",
    "fenaka": "fenaka", "ފެނަކަ": "fenaka",
    "stelco": "stelco", "ސްޓެލްކޯ": "stelco",
    "mtcc": "mtcc", "އެމްޓީސީސީ": "mtcc",
    "rdc": "rdc", "އާރްޑީސީ": "rdc",
    "ooredoo": "ooredoo", "އުރީދޫ": "ooredoo",
    "dhiraagu": "dhiraagu", "ދިރާގު": "dhiraagu",
    "muizzu": "muizzu", "މުއިއްޒު": "muizzu",
    "solih": "solih", "ޞާލިޙް": "solih", "ސާލިހު": "solih",
    "nasheed": "nasheed", "ނަޝީދު": "nasheed",
    "aslam": "aslam", "އަސްލަމް": "aslam",
    "nazeem": "nazeem", "ނާޒިމް": "nazeem", "ނަޒީމް": "nazeem",
    "rasmale": "rasmale", "ras male": "rasmale", "ރަސްމާލެ": "rasmale", "fushidhiggaru": "rasmale", "ފުށިދިއްގަރު": "rasmale",
    "eagle hills": "eaglehills", "އީގަލް ހިލްސް": "eaglehills", "އީގަލްހިލްސް": "eaglehills",
    "guraidhoo": "guraidhoo", "ގުރައިދޫ": "guraidhoo",
    "fuvahmulah": "fuvahmulah", "ފުވައްމުލައް": "fuvahmulah",
    "addu": "addu", "އައްޑޫ": "addu",
    "kulhudhuffushi": "kulhudhuffushi", "ކުޅުދުއްފުށި": "kulhudhuffushi",
    "aman towers": "amantowers", "އަމާން ޓަވަރު": "amantowers",
    "pakistan": "pakistan", "ޕާކިސްތާން": "pakistan",
    "india": "india", "އިންޑިއާ": "india",
    "china": "china", "ޗައިނާ": "china",
    "stabbing": "stabbing", "ތޫނު": "stabbing", "ހަމަލާ": "stabbing",
    "heavy vehicle": "trafficban", "ބޮޑެތި އުޅަނދު": "trafficban", "goods transport": "trafficban",
    "alcohol": "alcoholnet", "ބަނގުރާ": "alcoholnet",
    "mira": "mira", "މީރާ": "mira",
    "fdc": "fdc", "އެފްޑީސީ": "fdc",
    "sultan park": "sultanpark", "sultanpark": "sultanpark", "ސަލްޠާން ޕާކް": "sultanpark", "ސަލްތާން ޕާކް": "sultanpark", "usgekolhu": "sultanpark", "އުސްގެކޮޅު": "sultanpark",
    "tgst": "tgst", "t-gst": "tgst", "ޓީޖީއެސްޓީ": "tgst", "tourism gst": "tgst", "resort tax": "tgst",
    "ggst": "ggst", "g-gst": "ggst", "general gst": "ggst", "ޖީއެސްޓީ": "ggst",
    "green tax": "greentax", "greentax": "greentax", "ގްރީން ޓެކްސް": "greentax",
    "bridge accident": "bridgeaccident", "bridge crash": "bridgeaccident", "ބްރިޖް އެކްސިޑެންޓް": "bridgeaccident", "sinamale bridge": "bridgeaccident",
    "president said": "presidentsaid", "muizzu said": "presidentsaid", "ރައީސް ވިދާޅުވީ": "presidentsaid", "މުއިއްޒު ވިދާޅުވީ": "presidentsaid",
}


def extract_article_entity_tokens(article: dict[str, Any]) -> set[str]:
    """Extract canonical semantic entity tokens and high-information words from an article."""
    text = f"{article.get('headline', '')} {article.get('summary', '')}".lower()
    tokens = set()

    for key, canonical in SEMANTIC_ENTITY_MAP.items():
        if key in text:
            tokens.add(canonical)

    eng_words = re.findall(r"\b[a-z]{4,}\b", text)
    stop_words = {
        "today", "yesterday", "government", "maldives", "minister", "president",
        "ministry", "state", "official", "island", "press", "news", "report",
        "reported", "decided", "following", "under", "after", "about", "their",
        "which", "there", "where", "would", "could", "should", "first"
    }
    for w in eng_words:
        if w not in stop_words:
            tokens.add(w)

    return tokens


def cluster_articles(raw_articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Group related news articles across multiple media outlets into unified story cards.
    Handles both editorial tracks (KNOWN_STORY_CLUSTERS) and dynamic 2-source article grouping.
    """
    normalized: list[dict[str, Any]] = []
    for art in raw_articles:
        a = dict(art)
        if not a.get("sources"):
            a["sources"] = [a.get("source_key") or "press"]
        normalized.append(a)
    raw_articles = normalized

    consumed_ids: set[str] = set()
    clustered_feed: list[dict[str, Any]] = []

    # 1. Match against known editorial running stories
    for cluster_def in KNOWN_STORY_CLUSTERS:
        matched = []
        for art in raw_articles:
            if art["id"] in consumed_ids:
                continue
            text_corpus = f"{art.get('headline', '')} {art.get('summary', '')}".lower()
            if any(k in text_corpus for k in cluster_def["keywords"]):
                matched.append(art)

        if matched:
            for m in matched:
                consumed_ids.add(m["id"])

            sources = list(dict.fromkeys([m["sources"][0] for m in matched]))
            source_links = {}
            for m in matched:
                s_key = m["sources"][0]
                if s_key not in source_links and m.get("url"):
                    source_links[s_key] = m["url"]

            primary_url = ""
            for pref_source in ["standard", "atolltimes", "sun", "psm"]:
                if pref_source in source_links:
                    primary_url = source_links[pref_source]
                    break
            if not primary_url and matched:
                primary_url = matched[0].get("url", "")

            best_art = min(matched, key=lambda x: x.get("minutes_ago", 9999))
            min_minutes = best_art.get("minutes_ago", 60)
            best_iso = best_art.get("published_iso")
            best_raw = best_art.get("published_raw", "Today")

            is_multi = len(sources) >= 2 or cluster_def.get("story_id") is not None
            section = "major" if is_multi else matched[0].get("section", "general")
            tag_list = [cluster_def["tag"]] if cluster_def.get("tag") else []

            clustered_feed.append({
                "id": cluster_def["id"],
                "headline": cluster_def["headline"],
                "summary": cluster_def["summary"],
                "published_raw": best_raw,
                "published_iso": best_iso,
                "minutes_ago": min_minutes,
                "time_ago": format_relative_time(min_minutes, best_iso),
                "sources": sources,
                "source_links": source_links,
                "url": primary_url,
                "section": section,
                "tags": tag_list,
                "story_id": cluster_def.get("story_id"),
                "topic": cluster_def.get("topic", "policy"),
                "articles": matched,
            })

    # 2. Dynamic 2-source article grouping for remaining unconsumed articles
    remaining_articles = [a for a in raw_articles if a["id"] not in consumed_ids]
    article_tokens: dict[str, set[str]] = {a["id"]: extract_article_entity_tokens(a) for a in remaining_articles}

    dynamic_clusters: list[list[dict[str, Any]]] = []
    dynamic_visited: set[str] = set()

    for i, a1 in enumerate(remaining_articles):
        if a1["id"] in dynamic_visited:
            continue
        current_cluster = [a1]
        t1 = article_tokens[a1["id"]]
        src1 = a1["sources"][0] if a1.get("sources") else "press"

        for j in range(i + 1, len(remaining_articles)):
            a2 = remaining_articles[j]
            if a2["id"] in dynamic_visited:
                continue
            src2 = a2["sources"][0] if a2.get("sources") else "press"
            if src1 == src2:
                continue  # group across different outlets

            t2 = article_tokens[a2["id"]]
            shared = t1.intersection(t2)

            has_strong_entity = any(e in shared for e in [
                "afeef", "azwar", "fenaka", "stelco", "mtcc", "rdc", "ooredoo",
                "dhiraagu", "muizzu", "solih", "nasheed", "aslam", "nazeem",
                "rasmale", "eaglehills", "guraidhoo", "fuvahmulah", "addu",
                "kulhudhuffushi", "amantowers", "stabbing", "trafficban", "alcoholnet",
                "sultanpark", "tgst", "ggst", "greentax", "bridgeaccident", "presidentsaid"
            ])
            if (has_strong_entity and len(shared) >= 1) or len(shared) >= 2:
                current_cluster.append(a2)

        if len(current_cluster) >= 2:
            for art in current_cluster:
                dynamic_visited.add(art["id"])
                consumed_ids.add(art["id"])
            dynamic_clusters.append(current_cluster)

    # Build cards for dynamic clusters
    for idx, d_matched in enumerate(dynamic_clusters):
        sources = list(dict.fromkeys([m["sources"][0] for m in d_matched]))
        source_links = {}
        for m in d_matched:
            s_key = m["sources"][0]
            if s_key not in source_links and m.get("url"):
                source_links[s_key] = m["url"]

        eng_art = next((m for m in d_matched if not is_dhivehi(m.get("headline", "")) and not is_latin_dhivehi(m.get("headline", ""))), None)
        thaana_art = next((m for m in d_matched if is_dhivehi(m.get("headline", ""))), None)

        is_translit = False
        orig_latin = None

        if eng_art:
            headline = eng_art["headline"]
            summary = eng_art.get("summary", "")
        elif thaana_art:
            headline = thaana_art["headline"]
            summary = thaana_art.get("summary", "")
        else:
            base_art = d_matched[0]
            raw_h = base_art.get("headline", "")
            if is_latin_dhivehi(raw_h):
                orig_latin = raw_h
                headline = raw_h
                summary = base_art.get("summary", "")
                is_translit = False
            else:
                headline = translate_dhivehi_title(raw_h)
                summary = base_art.get("summary", "")

        primary_url = ""
        for pref_source in ["standard", "atolltimes", "sun", "psm"]:
            if pref_source in source_links:
                primary_url = source_links[pref_source]
                break
        if not primary_url:
            primary_url = d_matched[0].get("url", "")

        best_art = min(d_matched, key=lambda x: x.get("minutes_ago", 9999))
        min_minutes = best_art.get("minutes_ago", 60)
        best_iso = best_art.get("published_iso")
        best_raw = best_art.get("published_raw", "Today")
        first_topic = d_matched[0].get("topic", "policy")

        clustered_feed.append({
            "id": f"dyn-cluster-{idx + 1}-{best_art['id']}",
            "headline": headline,
            "summary": summary,
            "published_raw": best_raw,
            "published_iso": best_iso,
            "minutes_ago": min_minutes,
            "time_ago": format_relative_time(min_minutes, best_iso),
            "sources": sources,
            "source_links": source_links,
            "url": primary_url,
            "section": "major",
            "tags": [],
            "story_id": None,
            "topic": first_topic,
            "is_latin": is_translit,
            "latin_original": orig_latin,
            "is_latin_transliterated": is_translit,
            "articles": d_matched,
        })

    # 3. Add unconsumed articles
    for art in raw_articles:
        if art["id"] in consumed_ids:
            continue
        art_copy = dict(art)
        s_key = art_copy["sources"][0] if art_copy.get("sources") else "press"
        if "source_links" not in art_copy:
            art_copy["source_links"] = {s_key: art_copy.get("url", "")}
        if "articles" not in art_copy:
            art_copy["articles"] = [art]

        h = art_copy.get("headline", "")
        if is_latin_dhivehi(h):
            art_copy["is_latin"] = True
            art_copy["latin_original"] = h
            art_copy["is_dhivehi"] = False
            art_copy["is_latin_transliterated"] = False

        clustered_feed.append(art_copy)

    clustered_feed.sort(key=lambda x: x.get("published_iso") or "", reverse=True)
    return clustered_feed
