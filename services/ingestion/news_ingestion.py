"""
News Ingestion Service.
Coordinates news scraper engine, obituary separation & persistence, canonical article
persistence, cross-publisher clustering, and alert evaluation.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Callable

from alerts.telegram import dispatch_news_alerts
from data.database import get_db, log_db_error, upsert_article
from scrapers.news import (
    cluster_articles,
    fetch_raw_news_articles,
    split_news_and_obituaries,
)
from services.alert_decision_service import process_content_event
from services.ingestion.obituary_ingestion import (
    ingest_obituary_candidates,
    sync_external_obituaries,
)

logger = logging.getLogger(__name__)


def execute_news_ingestion(
    raw_fetcher: Callable[[], list[dict[str, Any]]] = fetch_raw_news_articles,
    alert_dispatcher: Callable = dispatch_news_alerts,
    sync_telegram_obits: bool = False,
) -> list[dict[str, Any]]:
    """
    Execute the complete news and obituary ingestion pipeline:
    1. Fetch raw articles across news sources and split obituary candidates.
    2. Persist obituary candidates via obituary_ingestion.
    3. Persist canonical publisher articles via stories repository.
    4. Cluster persisted articles into cross-source story groups.
    5. Dispatch broadcast and personalized alerts.
    Returns the clustered articles list.
    """
    raw_items = raw_fetcher()
    news_items, obit_items = split_news_and_obituaries(raw_items)

    if obit_items or sync_telegram_obits:
        try:
            with get_db() as conn:
                if obit_items:
                    ingest_obituary_candidates(conn, obit_items)
                if sync_telegram_obits:
                    sync_external_obituaries(conn)
        except Exception as e:
            logger.warning("Error during obituary ingestion: %s", e)

    persisted_news_items = []
    if news_items:
        with get_db() as conn:
            for item in news_items:
                try:
                    conn.execute("SAVEPOINT art_sp;")
                    upsert_article(conn, item)
                    conn.execute("RELEASE SAVEPOINT art_sp;")
                    persisted_news_items.append(item)
                except Exception as exc:
                    try:
                        conn.execute("ROLLBACK TO SAVEPOINT art_sp;")
                    except Exception:
                        pass
                    log_db_error(logger, f"upsert_article_{item.get('id')}", "services.ingestion.news_ingestion", exc)

    articles = cluster_articles(persisted_news_items) if persisted_news_items else []
    if articles:
        try:
            with get_db() as conn:
                alert_dispatcher(conn, articles)
        except Exception as e:
            log_db_error(logger, "dispatch_news_alerts", "services.ingestion.news_ingestion", e)

        try:
            with get_db() as conn:
                for art in articles:
                    s_id = art.get("story_id") or art.get("id")
                    if s_id:
                        try:
                            conn.execute("SAVEPOINT alert_decision_sp;")
                            is_brk = bool(art.get("is_breaking") or art.get("category") == "breaking")
                            topics = [art.get("category")] if art.get("category") else []
                            headline = art.get("headline", "")
                            summary = art.get("summary")
                            sources = art.get("sources") or []
                            fp_raw = f"{headline.strip()}|{(summary or '').strip()[:100]}|{len(sources)}"
                            fp = hashlib.sha256(fp_raw.encode("utf-8")).hexdigest()[:10]
                            process_content_event(
                                conn,
                                content_type="news",
                                content_id=str(s_id),
                                title=headline,
                                summary=summary,
                                url=art.get("url") or f"/story/{s_id}",
                                is_breaking=is_brk,
                                topics=topics,
                                section=art.get("section") or "news",
                                source_id=art.get("source_name") or art.get("source"),
                                event_version=art.get("event_version", 1),
                                update_fingerprint=fp,
                            )
                            conn.execute("RELEASE SAVEPOINT alert_decision_sp;")
                        except Exception as exc:
                            try:
                                conn.execute("ROLLBACK TO SAVEPOINT alert_decision_sp;")
                            except Exception:
                                pass
                            log_db_error(logger, f"process_news_alert_{s_id}", "services.ingestion.news_ingestion", exc)
        except Exception as e:
            log_db_error(logger, "evaluate_news_alerts_batch", "services.ingestion.news_ingestion", e)

    return articles
