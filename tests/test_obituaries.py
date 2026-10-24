from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from main import app
from data.database import (
    get_db,
    list_obituaries,
    get_obituary,
    upsert_obituary,
    toggle_obituary,
    delete_obituary,
    parse_obituary_text,
    upsert_scraped_obituary,
)
from scrapers.news import fetch_telegram_posts

client = TestClient(app)
AUTH = ("editor", "changeme")


def test_public_obituaries_page():
    resp = client.get("/obituaries")
    assert resp.status_code == 200
    assert "Funeral Announcements" in resp.text
    assert "ކަށުނަމާދު" in resp.text
    assert "إِنَّا لِلَّهِ وَإِنَّا إِلَيْهِ رَاجِعُونَ" in resp.text
    # Should display the seeded announcement for Dr. Shainee's father
    assert "އިބްރާހީމް މުޙައްމަދު" in resp.text
    assert "އާސަހަރާ" in resp.text


def test_janaza_alias_route():
    resp = client.get("/janaza")
    assert resp.status_code == 200
    assert "Funeral Announcements" in resp.text


def test_public_obituaries_search_filter():
    resp = client.get("/obituaries?q=Roobyvilla")
    assert resp.status_code == 200
    assert "އިބްރާހީމް މުޙައްމަދު" in resp.text

    # Search for non-existent entry
    resp_empty = client.get("/obituaries?q=NonExistentPersonXYZ")
    assert resp_empty.status_code == 200
    assert "No obituary announcements posted yet" in resp_empty.text


def test_obituary_parser_and_attributes():
    sample_text = """
    ކަށުނަމާދު (KashunamaadhuMV)
    އިބްރާހީމް މުޙައްމަދު (72އ)
    ހ. ރޫބީވިލާ / މާލެ
    ކަށުނަމާދު އޮންނާނީ: މިއަދުގެ ޢަޞްރު ނަމާދަށްފަހު އާސަހަރާ މިސްކިތުގައި
    އާއިލާގެ ނަންބަރު: 7992266 / 9394545
    """
    parsed = parse_obituary_text(sample_text)
    assert "އިބްރާހީމް މުޙައްމަދު" in parsed["name_dv"]
    assert parsed["age"] == 72
    assert "ރޫބީވިލާ" in parsed["address_dv"]
    assert "އާސަހަރާ" in parsed["funeral_mosque_dv"]
    assert "ޢަޞްރު" in parsed["prayer_time_dv"]
    assert "7992266" in parsed["contact_numbers"]
    assert "9394545" in parsed["contact_numbers"]


def test_telegram_obituary_excluded_from_news(monkeypatch):
    sample_tg_html = """
    <div class="tgme_widget_message">
      <div class="tgme_widget_message_text">
        ކަށުނަމާދު: އަލްމަރުޙޫމް އަޙްމަދު ރަޝީދު (65އ) ދަފްތަރު ނަންބަރު 1021 / މާލެ.
        ކަށުނަމާދު އޮންނާނީ މިއަދުގެ މަޣްރިބް ނަމާދަށްފަހު އާސަހަރާ މިސްކިތުގައި.
        ފޯނު: 7789012
      </div>
      <div class="tgme_widget_message_date"><time datetime="2026-10-16T08:00:00+00:00"></time></div>
    </div>
    <div class="tgme_widget_message">
      <div class="tgme_widget_message_text">
        🚨 #Breaking: Police launch investigation into vehicle collision on Sinamale Bridge highway.
      </div>
      <div class="tgme_widget_message_date"><time datetime="2026-10-16T08:30:00+00:00"></time></div>
    </div>
    """
    class MockResp:
        status_code = 200
        text = sample_tg_html

    monkeypatch.setattr("requests.get", lambda *args, **kwargs: MockResp())
    articles = fetch_telegram_posts("mvcrisis", "https://t.me/s/mvcrisis")

    # The obituary announcement MUST NOT be in general news articles!
    headlines = [a["headline"] for a in articles]
    for h in headlines:
        assert "ކަށުނަމާދު" not in h
        assert "އަޙްމަދު ރަޝީދު" not in h

    # But the genuine breaking news post must pass through
    assert any("Sinamale Bridge" in h for h in headlines)


def test_admin_obituaries_auth_and_management(tmp_path):
    # Unauthenticated should fail
    resp_unauth = client.get("/admin/obituaries")
    assert resp_unauth.status_code == 401

    # Authenticated view
    resp = client.get("/admin/obituaries", auth=AUTH)
    assert resp.status_code == 200
    assert "Obituary &amp; Janaza Registry" in resp.text
    assert "Post New Obituary" in resp.text

    # Create new notice via form
    form_data = {
        "name_dv": "ޢަލީ ޒާހިރު",
        "name_en": "Ali Zahir",
        "address_dv": "މ. ވެލިދޫގެ / މާލެ",
        "address_en": "M. Velidhooge, Male'",
        "age": 75,
        "funeral_mosque_dv": "މަސްޖިދުލް ޒައިދު ބިން ޘާބިތު (ހުޅުމާލެ)",
        "funeral_mosque_en": "Hulhumale Cemetery Mosque",
        "prayer_time_dv": "މިއަދުގެ ޢިޝާ ނަމާދަށްފަހު",
        "prayer_time_en": "After Isha Prayer",
        "funeral_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "contact_numbers": "7711223",
    }
    resp_create = client.post("/admin/obituaries/create", data=form_data, auth=AUTH, follow_redirects=False)
    assert resp_create.status_code == 303
    assert "/admin/obituaries?msg=" in resp_create.headers["location"]

    # Verify created notice in DB and public page
    with get_db() as conn:
        obs = list_obituaries(conn, search_q="Ali Zahir")
        assert len(obs) >= 1
        created_ob = obs[0]
        assert created_ob["name_dv"] == "ޢަލީ ޒާހިރު"

        # Toggle status
        toggle_obituary(conn, created_ob["id"])
        ob_toggled = get_obituary(conn, created_ob["id"])
        assert ob_toggled["is_active"] == 0

        # Delete notice
        delete_obituary(conn, created_ob["id"])
        ob_deleted = get_obituary(conn, created_ob["id"])
        assert ob_deleted is None


def test_admin_quick_import_kashunamaadhu():
    sample_fb_post = """
    ކަށުނަމާދު (KashuNamaadhuMV)
    މަރްޔަމް ޚަދީޖާ (80އ)
    ގ. އަލިމަސްގެ / މާލެ
    ކަށުނަމާދު އޮންނާނީ: މިއަދުގެ ޢަޞްރު ނަމާދަށްފަހު އާސަހަރާ މިސްކިތުގައި
    އާއިލާގެ ނަންބަރު: 7799112 / 9911223
    """
    resp = client.post(
        "/admin/obituaries/quick-import",
        data={"post_text": sample_fb_post},
        auth=AUTH,
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "/admin/obituaries?msg=" in resp.headers["location"]

    with get_db() as conn:
        obs = list_obituaries(conn, search_q="މަރްޔަމް")
        assert len(obs) >= 1
        assert "މަރްޔަމް ޚަދީޖާ" in obs[0]["name_dv"]
        assert obs[0]["age"] == 80
        assert "އާސަހަރާ" in obs[0]["funeral_mosque_dv"]
        assert "7799112" in obs[0]["contact_numbers"]


def test_obituaries_atoll_and_island_extraction():
    from data.database import extract_atoll_and_island

    # 1. Male'
    male_res = extract_atoll_and_island("ހ. ރޫބީވިލާ / މާލެ", "H. Roobyvilla, Male'", "އާސަހަރާ މިސްކިތް")
    assert male_res["atoll_code"] == "K-MALE"
    assert male_res["region_group"] == "male"
    assert male_res["sort_order"] == 0

    # 2. Hulhumale'
    hulh_res = extract_atoll_and_island("ހުޅުމާލެ ފްލެޓް 12", "Hulhumale Flat 12", "ހުޅުމާލެ ސަހަރާ މިސްކިތް")
    assert hulh_res["atoll_code"] == "K-MALE"
    assert hulh_res["island_name"] == "ހުޅުމާލެ"

    # 3. North: HDh. Kulhudhuffushi
    north_res = extract_atoll_and_island("ހުވަދޫގެ / ހދ. ކުޅުދުއްފުށި", "Huvadhooge, HDh. Kulhudhuffushi")
    assert north_res["atoll_code"] == "HDh"
    assert north_res["region_group"] == "north"
    assert north_res["island_name"] == "ކުޅުދުއްފުށި"
    assert north_res["sort_order"] == 2

    # 4. South: S. Addu City
    south_res = extract_atoll_and_island("މ. ފިނިފެންމާގެ / ސ. ހިތަދޫ", "M. Finifenmaage, S. Hithadhoo")
    assert south_res["atoll_code"] == "S"
    assert south_res["region_group"] == "south"
    assert south_res["sort_order"] == 20


def test_obituaries_seven_day_retention_and_purge(tmp_path):
    from data.database import init_db, purge_expired_obituaries
    from datetime import datetime, timedelta, timezone

    db_path = tmp_path / "test_retention.db"
    init_db(db_path, seed_bids=False)

    today = datetime.now(timezone.utc).date()
    date_today = today.strftime("%Y-%m-%d")
    date_5_days_ago = (today - timedelta(days=5)).strftime("%Y-%m-%d")
    date_10_days_ago = (today - timedelta(days=10)).strftime("%Y-%m-%d")

    with get_db(db_path) as conn:
        # Insert 3 obituaries with different dates
        upsert_obituary(conn, {
            "slug": "notice-recent-1",
            "name_dv": "މިއަދުގެ ނޯޓިސް",
            "funeral_date": date_today,
            "funeral_mosque_dv": "އާސަހަރާ",
        })
        upsert_obituary(conn, {
            "slug": "notice-recent-2",
            "name_dv": "ފަސް ދުވަސްވީ ނޯޓިސް",
            "funeral_date": date_5_days_ago,
            "funeral_mosque_dv": "ހުޅުމާލެ ސަހަރާ",
        })
        upsert_obituary(conn, {
            "slug": "notice-expired-old",
            "name_dv": "ދިހަ ދުވަސްވީ ނޯޓިސް",
            "funeral_date": date_10_days_ago,
            "funeral_mosque_dv": "އާސަހަރާ",
        })

        # Purge directly
        purged = purge_expired_obituaries(conn, retention_days=7)
        assert purged >= 1

        # Verify list_obituaries returns recent ones and filters expired
        recent_obs = list_obituaries(conn, retention_days=7)
        slugs = [o["slug"] for o in recent_obs]
        assert "notice-recent-1" in slugs
        assert "notice-recent-2" in slugs
        assert "notice-expired-old" not in slugs

        all_remaining = conn.execute("SELECT slug FROM obituaries;").fetchall()
        remaining_slugs = [r["slug"] for r in all_remaining]
        assert "notice-expired-old" not in remaining_slugs


def test_obituaries_atoll_sorting(tmp_path):
    from data.database import init_db

    db_path = tmp_path / "test_sorting.db"
    init_db(db_path, seed_bids=False)

    with get_db(db_path) as conn:
        # Insert out of order
        upsert_obituary(conn, {
            "slug": "ob-addu",
            "name_dv": "އައްޑޫ މީހެއް",
            "address_dv": "ސ. ހިތަދޫ",
            "funeral_mosque_dv": "ހިތަދޫ މިސްކިތް",
        })
        upsert_obituary(conn, {
            "slug": "ob-male",
            "name_dv": "މާލޭ މީހެއް",
            "address_dv": "މާލެ",
            "funeral_mosque_dv": "އާސަހަރާ",
        })
        upsert_obituary(conn, {
            "slug": "ob-kulhudhuffushi",
            "name_dv": "ކުޅުދުއްފުށީ މީހެއް",
            "address_dv": "ހދ. ކުޅުދުއްފުށި",
            "funeral_mosque_dv": "ޢަފާފް މިސްކިތް",
        })

        # list_obituaries sorts by sort_order (0: Male, 2: HDh, 20: S)
        obs = list_obituaries(conn)
        res_slugs = [o["slug"] for o in obs if o["slug"] in ["ob-addu", "ob-male", "ob-kulhudhuffushi"]]
        assert res_slugs == ["ob-male", "ob-kulhudhuffushi", "ob-addu"]

