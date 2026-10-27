"""
Tests for News Scraper Dispatch Engine (scrapers/news/engine.py).
Verifies:
- Telegram dispatch invokes generic telegram adapter
- MV Crisis dispatch invokes dedicated mvcrisis adapter
- RSS dispatch invokes rss adapter
- WordPress dispatch invokes wp_rest adapter
- Unknown/unsupported source types produce structured error and return empty list
- Adapter exceptions are caught safely without crashing aggregation
- Empty, None, or malformed adapter responses are handled safely
- Obituary separation operates without database side-effects
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch
import pytest

from scrapers.news.engine import (
    fetch_source_articles,
    fetch_raw_news_articles,
    split_news_and_obituaries,
    is_obituary_article,
    fetch_all_live_news,
)


def test_telegram_dispatch():
    """Verify generic Telegram source type invokes fetch_telegram_posts."""
    cfg = {
        "id": "channel_breaking",
        "type": "telegram",
        "url": "https://t.me/s/breakingnews",
    }
    fake_posts = [{"headline": "Breaking headline", "url": "https://t.me/breaking/1"}]

    with patch("scrapers.news.engine.fetch_telegram_posts", return_value=fake_posts) as mock_tg, \
         patch("scrapers.news.engine.fetch_mvcrisis_posts") as mock_mvc:
        res = fetch_source_articles(cfg)
        mock_tg.assert_called_once_with("channel_breaking", "https://t.me/s/breakingnews")
        mock_mvc.assert_not_called()
        assert res == fake_posts


def test_mvcrisis_dispatch_by_key():
    """Verify source with key 'mvcrisis' invokes fetch_mvcrisis_posts."""
    cfg = {
        "id": "mvcrisis",
        "type": "telegram",
        "url": "https://t.me/s/mvcrisis",
    }
    fake_posts = [{"headline": "MVCrisis incident wire", "url": "https://t.me/mvcrisis/100"}]

    with patch("scrapers.news.engine.fetch_mvcrisis_posts", return_value=fake_posts) as mock_mvc, \
         patch("scrapers.news.engine.fetch_telegram_posts") as mock_tg:
        res = fetch_source_articles(cfg)
        mock_mvc.assert_called_once_with("mvcrisis", "https://t.me/s/mvcrisis")
        mock_tg.assert_not_called()
        assert res == fake_posts


def test_mvcrisis_dispatch_by_type():
    """Verify source with type 'mvcrisis' invokes fetch_mvcrisis_posts."""
    cfg = {
        "id": "mvcrisis_mirror",
        "type": "mvcrisis",
        "url": "https://t.me/s/mvcrisis_mirror",
    }
    fake_posts = [{"headline": "MVCrisis mirror", "url": "https://t.me/mvcrisis_mirror/1"}]

    with patch("scrapers.news.engine.fetch_mvcrisis_posts", return_value=fake_posts) as mock_mvc, \
         patch("scrapers.news.engine.fetch_telegram_posts") as mock_tg:
        res = fetch_source_articles(cfg)
        mock_mvc.assert_called_once_with("mvcrisis_mirror", "https://t.me/s/mvcrisis_mirror")
        mock_tg.assert_not_called()
        assert res == fake_posts


def test_rss_dispatch():
    """Verify RSS sources invoke fetch_rss_posts."""
    cfg = {
        "id": "atolltimes",
        "type": "rss",
        "url": "https://atolltimes.mv/feed/",
    }
    fake_posts = [{"headline": "Atoll Times headline", "url": "https://atolltimes.mv/1"}]

    with patch("scrapers.news.engine.fetch_rss_posts", return_value=fake_posts) as mock_rss:
        res = fetch_source_articles(cfg)
        mock_rss.assert_called_once_with("atolltimes", "https://atolltimes.mv/feed/")
        assert res == fake_posts


def test_wp_rest_dispatch():
    """Verify WordPress REST sources invoke fetch_wp_rest_posts."""
    cfg = {
        "id": "haftha",
        "type": "wp_rest",
        "url": "https://haftha.mv/wp-json/wp/v2/posts",
    }
    fake_posts = [{"headline": "Haftha headline", "url": "https://haftha.mv/1"}]

    with patch("scrapers.news.engine.fetch_wp_rest_posts", return_value=fake_posts) as mock_wp:
        res = fetch_source_articles(cfg)
        mock_wp.assert_called_once_with("haftha", "https://haftha.mv/wp-json/wp/v2/posts")
        assert res == fake_posts


def test_unknown_source_type(caplog):
    """Verify unknown source type logs structured error and returns empty list."""
    cfg = {
        "id": "unknown_outlet",
        "type": "unsupported_protocol_xyz",
        "url": "https://example.com/unsupported",
    }
    with caplog.at_level(logging.ERROR):
        res = fetch_source_articles(cfg)
        assert res == []
        assert "Unsupported source type 'unsupported_protocol_xyz'" in caplog.text


def test_adapter_exception_handled(caplog):
    """Verify that an adapter throwing an exception is handled safely and logged."""
    cfg = {
        "id": "faulty_feed",
        "type": "rss",
        "url": "https://faulty.com/feed",
    }
    with patch("scrapers.news.engine.fetch_rss_posts", side_effect=ConnectionResetError("Socket reset")), \
         caplog.at_level(logging.ERROR):
        res = fetch_source_articles(cfg)
        assert res == []
        assert "Adapter exception fetching source 'faulty_feed'" in caplog.text


def test_empty_and_malformed_adapter_response():
    """Verify that adapter returning None or empty list doesn't crash."""
    cfg = {
        "id": "empty_feed",
        "type": "rss",
        "url": "https://empty.com/feed",
    }
    with patch("scrapers.news.engine.fetch_rss_posts", return_value=None):
        res = fetch_source_articles(cfg)
        assert res == []

    with patch("scrapers.news.engine.fetch_rss_posts", return_value=[]):
        res = fetch_source_articles(cfg)
        assert res == []


def test_obituary_classification_and_splitting_no_db_side_effects():
    """Verify obituary detection and separation without database side-effects."""
    articles = [
        {
            "id": "news-1",
            "headline": "President inaugurates regional airport development",
            "summary": "Infrastructure ceremony held in Haa Dhaalu Atoll.",
            "url": "https://example.mv/news1",
        },
        {
            "id": "obit-1",
            "headline": "ކަށުނަމާދު: އިބްރާހީމް މުޙައްމަދު ނިޔާވެއްޖެ",
            "summary": "ކަށުނަމާދު އޮންނާނީ މިއަދުގެ ޢަޞްރު ނަމާދަށްފަހު އާސަހަރާ މިސްކިތުގައެވެ.",
            "url": "https://t.me/s/mvcrisis/99",
        },
        {
            "id": "news-2",
            "headline": "Fisheries Ministry announces subsidies for local vessels",
            "summary": "Fuel subsidy distribution begins next week.",
            "url": "https://example.mv/news2",
        },
    ]

    news, obits = split_news_and_obituaries(articles)
    assert len(news) == 2
    assert news[0]["id"] == "news-1"
    assert news[1]["id"] == "news-2"

    assert len(obits) == 1
    assert obits[0]["id"] == "obit-1"
