"""
Live News Aggregator for Khulaasaa / Dispatch.
Backwards-compatible facade re-exporting atomic news scrapers and clustering service.
"""
from scrapers.news.base import (
    HEADERS,
    NEWS_SOURCES_CONFIG,
    strip_html_tags,
    classify_topic,
    classify_section,
    calculate_minutes_ago,
    format_relative_time,
)
from scrapers.news.rss import fetch_rss_posts
from scrapers.news.wp_rest import fetch_wp_rest_posts
from scrapers.news.telegram import fetch_telegram_posts
from scrapers.news.mihaaru import fetch_mihaaru_posts
from scrapers.news.miadhu import fetch_miadhu_posts
from scrapers.news.engine import fetch_all_live_news, fetch_source_articles
from services.clustering import (
    KNOWN_STORY_CLUSTERS,
    SEMANTIC_ENTITY_MAP,
    extract_article_entity_tokens,
    cluster_articles,
)

__all__ = [
    "HEADERS",
    "NEWS_SOURCES_CONFIG",
    "strip_html_tags",
    "classify_topic",
    "classify_section",
    "calculate_minutes_ago",
    "format_relative_time",
    "fetch_rss_posts",
    "fetch_wp_rest_posts",
    "fetch_telegram_posts",
    "fetch_mihaaru_posts",
    "fetch_miadhu_posts",
    "fetch_all_live_news",
    "fetch_source_articles",
    "KNOWN_STORY_CLUSTERS",
    "SEMANTIC_ENTITY_MAP",
    "extract_article_entity_tokens",
    "cluster_articles",
]
