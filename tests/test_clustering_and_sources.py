from pathlib import Path
from fastapi.testclient import TestClient

from main import app
from scrapers.news import cluster_articles, KNOWN_STORY_CLUSTERS
from data.stories import SOURCES, TIMELINE_TAGS, TIMELINES, TRENDING

client = TestClient(app)


def test_mock_data_file_is_completely_deleted():
    mock_file = Path("data/mock_data.py")
    assert not mock_file.exists(), "data/mock_data.py must be completely deleted from the codebase."


def test_clustering_groups_multiple_outlets():
    raw_sample = [
        {
            "id": "sun-fenaka-1",
            "headline": "Fenakaige acting MD ge magaamah Azwar ayyankohfi",
            "summary": "Fenaka management restructuring initiated.",
            "sources": ["sun"],
            "url": "https://sun.mv/229143",
            "published_iso": "2026-10-15T12:00:00Z",
            "minutes_ago": 60,
        },
        {
            "id": "standard-fenaka-2",
            "headline": "Fenaka management handed over to STELCO MD Dr Ali Azwar",
            "summary": "Cabinet transfers operational oversight.",
            "sources": ["standard"],
            "url": "https://standard.mv/fenaka-handover",
            "published_iso": "2026-10-15T12:05:00Z",
            "minutes_ago": 55,
        },
        {
            "id": "psm-fenaka-3",
            "headline": "ފެނަކަ ހިންގުން ސްޓެލްކޯގެ އެމްޑީ ޑރ.އަޒުވަރަށް",
            "summary": "ސަރުކާރުން ނިންމި ނިންމުން.",
            "sources": ["psm"],
            "url": "https://psmnews.mv/190258",
            "published_iso": "2026-10-15T12:10:00Z",
            "minutes_ago": 50,
        },
    ]

    clustered = cluster_articles(raw_sample)
    assert len(clustered) == 1
    card = clustered[0]
    assert card["id"] == "cluster-fenaka-merger"
    assert set(card["sources"]) == {"sun", "standard", "psm"}
    assert "sun" in card["source_links"]
    assert "standard" in card["source_links"]
    assert "psm" in card["source_links"]
    assert card["section"] == "major"
    assert card["story_id"] == "fenaka-stelco-merger"


def test_home_page_renders_with_real_stories():
    response = client.get("/")
    assert response.status_code == 200
    assert "Khulaasaa" in response.text
    # Check that trending reflects real Maldivian stories
    assert "Heavy vehicles" in response.text or "Fenaka" in response.text
    # Check that tags contain current tracks
    assert "Greater Malé Traffic Ban" in response.text or "Ras Malé Project" in response.text


def test_timeline_page_renders_multi_outlet_story():
    response = client.get("/timeline/male-traffic-ban")
    assert response.status_code == 200
    assert "Greater Malé Heavy Vehicle" in response.text
    assert "Transport Ministry" in response.text


def test_timeline_ras_male_project():
    response = client.get("/timeline/ras-male-project")
    assert response.status_code == 200
    assert "Ras Malé" in response.text
    assert "Fushidhiggaru" in response.text


def test_fenaka_afeef_clustering_multi_outlet():
    """Verify that Fenaka MD Afeef's appointment reported across Atoll Times, Haftha, Dhauru, and The Standard clusters into a single story card."""
    raw_articles = [
        {
            "id": "atolltimes-afeef-101",
            "headline": "Fenaka MD Afeef appointed state minister following restructuring",
            "summary": "Former Fenaka Managing Director Muaz Mohamed Rasheed (Afeef) has been appointed as a State Minister at the Ministry of Climate Change, Environment and Energy.",
            "sources": ["atolltimes"],
            "url": "https://atolltimes.mv/post/news/12345",
            "published_iso": "2026-10-15T10:00:00Z",
            "minutes_ago": 90,
        },
        {
            "id": "haftha-afeef-102",
            "headline": "ފެނަކަ އުވާލުމުން، އެމްޑީއަކަށް ހުންނެވި އަފީފް ސްޓޭޓް މިނިސްޓަރަކަށް",
            "summary": "ފެނަކަ ކޯޕަރޭޝަން އުވާލައި ސްޓެލްކޯގެ ދަށަށް ބަދަލުކުރުމަށްފަހު، އެ ކުންފުނީގެ މެނޭޖިން ޑިރެކްޓަރު މުއާޒު މުހައްމަދު ރަޝީދު (އަފީފް) އެންވަޔަރަންމަންޓް މިނިސްޓްރީގެ ސްޓޭޓް މިނިސްޓަރަކަށް އައްޔަންކޮށްފިއެވެ.",
            "sources": ["haftha"],
            "url": "https://haftha.mv/12845",
            "published_iso": "2026-10-15T10:05:00Z",
            "minutes_ago": 85,
        },
        {
            "id": "dhauru-afeef-103",
            "headline": "އެމްޑީ އަފީފް ސްޓޭޓް މިނިސްޓަރަކަށް އައްޔަންކޮށްފި",
            "summary": "ފެނަކަ ރީސްޓްރަކްޗަރ ކުރުމުގެ ތެރެއިން ނިންމި ނިންމުމެއް.",
            "sources": ["dhauru"],
            "url": "https://dhauru.com/story/9876",
            "published_iso": "2026-10-15T10:10:00Z",
            "minutes_ago": 80,
        },
        {
            "id": "standard-afeef-104",
            "headline": "Fenaka MD Afeef appointed State Minister at Environment Ministry",
            "summary": "Cabinet decisions to merge Fenaka operations into STELCO led to Afeef taking on a state ministerial portfolio.",
            "sources": ["standard"],
            "url": "https://standard.mv/afeef-state-minister",
            "published_iso": "2026-10-15T10:15:00Z",
            "minutes_ago": 75,
        },
    ]

    clustered = cluster_articles(raw_articles)
    assert len(clustered) == 1
    card = clustered[0]
    assert card["id"] == "cluster-fenaka-afeef"
    assert "Fenaka MD Afeef appointed State Minister" in card["headline"]
    assert set(card["sources"]) == {"atolltimes", "haftha", "dhauru", "standard"}
    assert card["source_links"]["atolltimes"] == "https://atolltimes.mv/post/news/12345"
    assert card["source_links"]["haftha"] == "https://haftha.mv/12845"
    assert card["source_links"]["dhauru"] == "https://dhauru.com/story/9876"
    assert card["source_links"]["standard"] == "https://standard.mv/afeef-state-minister"
    assert card["section"] == "major"
    assert card["story_id"] == "fenaka-stelco-merger"


def test_dynamic_clustering_two_different_sources():
    """Verify that unconsumed articles from different media outlets sharing semantic entities are dynamically grouped."""
    articles = [
        {
            "id": "sun-event-1",
            "headline": "Ooredoo expands high-speed 5G connectivity to Laamu Atoll",
            "summary": "Ooredoo telecom expansion completed across southern islands.",
            "sources": ["sun"],
            "url": "https://sun.mv/ooredoo-laamu-5g",
            "published_iso": "2026-10-15T11:00:00Z",
            "minutes_ago": 40,
        },
        {
            "id": "atolltimes-event-2",
            "headline": "Ooredoo activates 5G network coverage in Gan and Fonadhoo",
            "summary": "Residents in Laamu atoll receive 5G mobile coverage from Ooredoo.",
            "sources": ["atolltimes"],
            "url": "https://atolltimes.mv/ooredoo-5g",
            "published_iso": "2026-10-15T11:15:00Z",
            "minutes_ago": 25,
        },
    ]

    clustered = cluster_articles(articles)
    assert len(clustered) == 1
    card = clustered[0]
    assert set(card["sources"]) == {"sun", "atolltimes"}
    assert "sun" in card["source_links"]
    assert "atolltimes" in card["source_links"]
    assert card["section"] == "major"


def test_all_canonical_sources_have_valid_logos():
    """Verify every canonical source in SOURCES has an existing logo file in static/logos/."""
    for source_id, info in SOURCES.items():
        assert "logo" in info, f"Source {source_id} missing 'logo' field"
        logo_path = Path(info["logo"].lstrip("/"))
        assert logo_path.exists(), f"Logo file for {source_id} does not exist at {logo_path}"
        assert logo_path.stat().st_size > 0, f"Logo file for {source_id} is empty"


def test_home_page_renders_logos_and_no_duplicate_outlets():
    """Verify that outlet logos are rendered and the duplicate 'Compare coverage' row is removed."""
    response = client.get("/?source=mock")
    assert response.status_code == 200
    # No duplicate 'Compare coverage' rows in the UI
    assert "Compare coverage (" not in response.text
    # Logos are rendered in the HTML
    assert "/static/logos/" in response.text
    # Check specific logos appear
    for expected in ["standard.png", "sun.png"]:
        assert f"/static/logos/{expected}" in response.text


def test_story_detail_endpoint_renders_multi_source_outlets():
    """Verify that /story/{story_id} displays multi-source comparison with exact outlet headlines."""
    from data.stories import DEFAULT_EVENTS
    # Pick a story with multiple sources
    target_story = next((e for e in DEFAULT_EVENTS if len(e.get("sources", [])) > 1), DEFAULT_EVENTS[0])
    response = client.get(f"/story/{target_story['id']}")
    assert response.status_code == 200
    assert "Coverage Across Outlets" in response.text
    assert target_story["headline"] in response.text
    # Verify outlet links and logos appear
    assert "Read on" in response.text


def test_viber_sponsored_broadcast_and_alerts():
    """Verify Viber sponsored broadcast logic and formatting."""
    from alerts.viber import format_viber_sponsored_block, dispatch_viber_sponsored_broadcast
    from data.database import get_db

    with get_db() as conn:
        ad_block = format_viber_sponsored_block(conn, target_category="all")
        assert "SPONSORED:" in ad_block or ad_block == ""

        # Test broadcast handler executes without crashing
        res = dispatch_viber_sponsored_broadcast(
            conn,
            campaign_name="Test Campaign",
            sponsor_name="Test Sponsor",
            html_content="<p>Test sponsored content</p>",
            target_category="all",
            link_url="https://khulaasaa.tech",
        )
        assert isinstance(res, dict)
        assert "delivered" in res
        assert "failed" in res


