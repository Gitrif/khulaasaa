"""
Live News Aggregation Engine.
Dispatches requests concurrently across all configured media outlets,
deduplicates/filters non-news notices, and applies semantic clustering.
Pure scraper layer: contains zero database side effects.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from scrapers.news.base import NEWS_SOURCES_CONFIG
from scrapers.news.rss import fetch_rss_posts
from scrapers.news.wp_rest import fetch_wp_rest_posts
from scrapers.news.telegram import fetch_telegram_posts
from scrapers.news.mvcrisis import fetch_mvcrisis_posts
from scrapers.news.mihaaru import fetch_mihaaru_posts
from scrapers.news.miadhu import fetch_miadhu_posts

logger = logging.getLogger(__name__)

OBITUARY_KEYWORDS = [
    "kashunamaadhu", "ކަށުނަމާދު", "صلاة الجނaza", "ޖަނާޒާ", "جنازة",
    "niyaavejje", "ނިޔާވެއްޖެ", "ނިޔާވުން", "މަރުޙޫމް", "މަރުހޫމް",
    "ކަށުކަމާކެމީގެ", "إِنَّا لِلَّهِ", "އިންނާލިއްލާހި", "އާސަހަރާ މިސްކިތް",
    "janaza", "janazah", "funeral", "obituary", "funeral prayer",
]


def is_obituary_article(art: dict[str, Any]) -> bool:
    """Classify whether a scraped post is an obituary notice based on keywords."""
    text_corpus = f"{art.get('headline', '')} {art.get('summary', '')}".lower()
    return any(k in text_corpus for k in OBITUARY_KEYWORDS)


def fetch_source_articles(source_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Dispatch fetcher based on source type.
    
    Routes to:
    - mvcrisis adapter if source key or type is 'mvcrisis'
    - generic telegram adapter if type is 'telegram'
    - wp_rest adapter if type is 'wp_rest'
    - rss adapter if type is 'rss'
    - specialized html adapters for mihaaru and miadhu
    
    Catches adapter exceptions and logs structured errors without raising.
    Logs structured errors for unknown source types.
    """
    s_key = source_cfg.get("id", "")
    s_type = source_cfg.get("type", "")
    s_url = source_cfg.get("url", "")

    if not s_key or not s_url:
        logger.warning("Invalid source configuration missing 'id' or 'url': %s", source_cfg)
        return []

    try:
        if s_key == "mvcrisis" or s_type == "mvcrisis":
            return fetch_mvcrisis_posts(s_key, s_url) or []
        elif s_type == "telegram":
            return fetch_telegram_posts(s_key, s_url) or []
        elif s_type == "wp_rest":
            return fetch_wp_rest_posts(s_key, s_url) or []
        elif s_type == "rss":
            return fetch_rss_posts(s_key, s_url) or []
        elif s_type == "html_mihaaru":
            return fetch_mihaaru_posts(s_key, s_url) or []
        elif s_type == "html_miadhu":
            return fetch_miadhu_posts(s_key, s_url) or []
        else:
            logger.error("Unsupported source type '%s' for source '%s'", s_type, s_key)
            return []
    except Exception as exc:
        logger.error("Adapter exception fetching source '%s' (type '%s'): %s", s_key, s_type, exc, exc_info=True)
        return []


def fetch_raw_news_articles(
    sources: dict[str, dict[str, Any]] | None = None,
    max_workers: int = 6
) -> list[dict[str, Any]]:
    """Aggregate raw news articles across all configured media outlets."""
    source_configs = (sources or NEWS_SOURCES_CONFIG).values()
    all_articles: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(fetch_source_articles, source_configs)
        for res in results:
            if res:
                all_articles.extend(res)

    return all_articles


def split_news_and_obituaries(articles: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Partition raw scraped items into standard news articles and obituary candidates."""
    news_articles: list[dict[str, Any]] = []
    obituary_articles: list[dict[str, Any]] = []

    for art in articles:
        if is_obituary_article(art):
            obituary_articles.append(art)
        else:
            news_articles.append(art)

    return news_articles, obituary_articles


def fetch_all_live_news(max_workers: int = 6) -> list[dict[str, Any]]:
    """Aggregate live news articles across all configured media outlets and cluster them.
    
    Filters out obituary notices from the general news articles without persisting them
    to the database directly. Database persistence is handled by domain/ingestion services.
    """
    from scrapers.news.clustering import cluster_articles

    all_articles = fetch_raw_news_articles(max_workers=max_workers)
    filtered_articles, _ = split_news_and_obituaries(all_articles)

    # Cluster related articles across multiple newsrooms
    return cluster_articles(filtered_articles)
