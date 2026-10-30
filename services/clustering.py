"""
News Clustering & Semantic Grouping Service.
Re-exports pure clustering primitives from `scrapers.news.clustering` for service-layer callers.
"""
from __future__ import annotations

from scrapers.news.clustering import (
    KNOWN_STORY_CLUSTERS,
    SEMANTIC_ENTITY_MAP,
    cluster_articles,
    extract_article_entity_tokens,
)

__all__ = [
    "KNOWN_STORY_CLUSTERS",
    "SEMANTIC_ENTITY_MAP",
    "cluster_articles",
    "extract_article_entity_tokens",
]
