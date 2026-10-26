"""
Tests for Latin Dhivehi transliteration engine, multi-source headline prioritization,
expanded narrative entity collections (Sultan Park, TGST, Green Tax, Bridge safety, President remarks),
and World Aggregator Standards (RSS 2.0 feed and Schema.org).
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from scrapers.news import cluster_articles
from scrapers.transliterate import is_latin_dhivehi, transliterate_latin_to_thaana


@pytest.fixture
def client():
    return TestClient(app)


# --- 1. Latin Dhivehi Detection Tests ---------------------------------------

def test_is_latin_dhivehi_positive_cases():
    """Confirms Latin Dhivehi headlines and phrases are accurately detected."""
    assert is_latin_dhivehi("5 meehunnah aniyaavi accident: Haalu serious vi ekaku ventilator gai")
    assert is_latin_dhivehi("Raajjeygai fuhpathuge balithah ithuruvanee kamah doctorun buneifi")
    assert is_latin_dhivehi("Male' ga hinguvi accident gai meehakah aniyaave hospital ah gengosfi")
    assert is_latin_dhivehi("Sarukaarun rayyithunge hiyaa flat thakuge kuli kandhaalhai")


def test_is_latin_dhivehi_negative_for_english():
    """Confirms English news articles with Dhivehi names/proper nouns are NOT flagged as Latin Dhivehi."""
    assert not is_latin_dhivehi("President Dr. Muizzu returns after official state visit to Pakistan")
    assert not is_latin_dhivehi("Procurement of heavy utility vehicles for Hulhumale development project")
    assert not is_latin_dhivehi("Cabinet approves merger of Fenaka Corporation under STELCO")
    assert not is_latin_dhivehi("Finance Ministry tables TGST rate revision amendment in Parliament")


# --- 2. Latin to Thaana Transliteration Tests --------------------------------

def test_transliterate_latin_to_thaana():
    """Confirms accurate phonetic and dictionary conversion from Romanized Dhivehi to Thaana."""
    text = "5 meehunnah aniyaavi accident: Haalu serious vi ekaku ventilator gai"
    converted = transliterate_latin_to_thaana(text)
    
    # Must contain Thaana characters and key translated tokens
    assert "މީހުންނަށް" in converted
    assert "އަނިޔާވި" in converted
    assert "އެކްސިޑެންޓް" in converted
    assert "ގައި" in converted
    assert "އެކަކު" in converted


# --- 3. Multi-Source Headline Prioritization --------------------------------

def test_cluster_prefers_english_over_latin_dhivehi():
    """
    When multiple outlets cover the same event and one is in Latin Dhivehi (e.g. Sun Latin)
    while another is in English (e.g. Atoll Times / Standard), Khulaasaa must choose the
    English title as the primary hero headline.
    """
    articles = [
        {
            "id": "sun-latin-101",
            "headline": "Henveiru geygai roavi alifaan kandaalhai: ekaku hospital ah",
            "summary": "Henveiru kanmathi gai hinguvi alifaange haadhisaa gai meehakah aniyaavi.",
            "sources": ["sun"],
            "url": "https://sun.mv/latin/101",
            "minutes_ago": 30,
            "section": "breaking",
            "topic": "crime",
        },
        {
            "id": "atoll-eng-202",
            "headline": "Emergency responders control residential fire in Henveiru ward",
            "summary": "MNDF Fire and Rescue services extinguished an apartment fire in Henveiru kanmathi, transferring one resident to hospital.",
            "sources": ["atolltimes"],
            "url": "https://atolltimes.mv/post/news/henveiru-fire",
            "minutes_ago": 25,
            "section": "breaking",
            "topic": "crime",
        },
    ]

    clusters = cluster_articles(articles)
    assert len(clusters) == 1
    c = clusters[0]
    
    # Primary headline must be the clean English one, NOT the Latin one
    assert c["headline"] == "Emergency responders control residential fire in Henveiru ward"
    assert "sun" in c["sources"]
    assert "atolltimes" in c["sources"]
    # Direct links to all sources must exist
    assert c["source_links"]["sun"] == "https://sun.mv/latin/101"
    assert c["source_links"]["atolltimes"] == "https://atolltimes.mv/post/news/henveiru-fire"


def test_cluster_preserves_standalone_latin_article_as_is():
    """
    When an article is in Latin Dhivehi, Khulaasaa strictly preserves the original
    Latin headline and text without phonetic Thaana transliteration.
    """
    articles = [
        {
            "id": "mvcrisis-wire-999",
            "headline": "5 meehunnah aniyaavi accident: Haalu serious vi ekaku ventilator gai",
            "summary": "Raajjeyge rasheh gai hinguvi accident eh police in thahgeeg kuranee.",
            "sources": ["mvcrisis"],
            "url": "https://t.me/MvCrisis/999",
            "minutes_ago": 15,
            "section": "breaking",
            "topic": "crime",
        }
    ]

    clusters = cluster_articles(articles)
    assert len(clusters) == 1
    c = clusters[0]

    assert c.get("is_latin_transliterated") is False
    assert c.get("is_dhivehi") is False
    assert c["headline"] == "5 meehunnah aniyaavi accident: Haalu serious vi ekaku ventilator gai"


# --- 4. Narrative Collections & Timelines ------------------------------------

def test_collection_routes(client):
    """Verifies deep-link timeline collections for Sultan Park, TGST, Green Tax, Ras Male, and Bridge."""
    # Direct story timeline routes
    res_sp = client.get("/collections/sultan-park-project")
    assert res_sp.status_code == 200
    assert "Sultan Park" in res_sp.text

    res_tg = client.get("/collections/tgst-tax-reform")
    assert res_tg.status_code == 200
    assert "TGST" in res_tg.text

    res_gt = client.get("/collections/green-tax-reform")
    assert res_gt.status_code == 200
    assert "Green Tax" in res_gt.text

    # Tag slug alias lookup
    res_rm = client.get("/collections/ras-male")
    assert res_rm.status_code == 200
    assert "Ras Malé" in res_rm.text or "Ras Male" in res_rm.text

    res_bridge = client.get("/collections/bridge-safety")
    assert res_bridge.status_code == 200
    assert "Sinamalé Bridge" in res_bridge.text or "Bridge" in res_bridge.text


# --- 5. World Aggregator Standards (RSS & Schema.org) ------------------------

def test_rss_feed_endpoint(client):
    """Verifies RSS 2.0 standard feed output for syndication and external readers."""
    res = client.get("/feed.xml")
    assert res.status_code == 200
    assert "application/xml" in res.headers["content-type"]
    assert "<rss version=\"2.0\">" in res.text
    assert "<channel>" in res.text
    assert "<title>Khulaasaa" in res.text
    assert "<item>" in res.text

    # /rss alias route
    res_rss = client.get("/rss")
    assert res_rss.status_code == 200
    assert "<rss version=\"2.0\">" in res_rss.text


def test_schema_org_microdata_in_feed(client):
    """Verifies Schema.org NewsArticle and ItemList microdata are rendered in the HTML feed."""
    res = client.get("/")
    assert res.status_code == 200
    assert "itemscope" in res.text
    assert "https://schema.org/ItemList" in res.text
    assert "https://schema.org/NewsArticle" in res.text
    assert "NewsMediaOrganization" in res.text
