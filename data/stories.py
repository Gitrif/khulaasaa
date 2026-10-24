"""
Unified Stories and Metadata aggregation module.
Re-exports sources, topics, timelines, and fallback story events.
"""
from data.sources_data import SOURCES, TOPICS, TRENDING, TIMELINE_TAGS
from data.timelines_data import TIMELINES
from data.mock_events import (
    DEFAULT_EVENTS,
    JOBS,
    PENDING_CLUSTERS,
    APPROVAL_LOG,
    approve_cluster,
)

__all__ = [
    "SOURCES",
    "TOPICS",
    "TRENDING",
    "TIMELINES",
    "TIMELINE_TAGS",
    "DEFAULT_EVENTS",
    "JOBS",
    "PENDING_CLUSTERS",
    "APPROVAL_LOG",
    "approve_cluster",
]
