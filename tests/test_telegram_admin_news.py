from pathlib import Path
from unittest.mock import MagicMock
import pytest
from data.database import (
    init_db,
    get_db,
    register_or_update_telegram_subscriber,
    get_telegram_subscriber,
    list_sponsored_ads,
    get_sponsored_ad,
)


@pytest.fixture
def temp_db(tmp_path: Path):
    db_file = tmp_path / "test_telegram_admin.db"
    init_db(db_file)
    return db_file


def test_admin_ad_manager_endpoints(monkeypatch, tmp_path):
    temp_db_path = str(tmp_path / "test_ad_manager.db")
    monkeypatch.setenv("KHULAASAA_DB_PATH", temp_db_path)
    init_db(temp_db_path, seed_bids=False)

    from main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)

    # 1. Unauthenticated access returns 401
    resp_unauth = client.get("/admin/ads")
    assert resp_unauth.status_code == 401

    # 2. Authenticated access
    auth = ("editor", "changeme")
    resp_auth = client.get("/admin/ads", auth=auth)
    assert resp_auth.status_code == 200
    assert "Commercial Ad Manager" in resp_auth.text
    assert "State Trading Organization (STO)" in resp_auth.text or "hooks85" in resp_auth.text

    # 3. Create a new campaign
    create_payload = {
        "sponsor_name": "Bank of Maldives",
        "campaign_name": "bml-business-credit",
        "target_category": "bids",
        "link_url": "https://bankofmaldives.com.mv",
        "text_html": "<b>BML Tender Guarantee:</b> Instant digital guarantees for government bids.",
        "is_active": 1,
    }
    resp_create = client.post("/admin/ads/create", data=create_payload, auth=auth, follow_redirects=True)
    assert resp_create.status_code == 200
    assert "Bank of Maldives" in resp_create.text
    assert "bml-business-credit" in resp_create.text

    with get_db(temp_db_path) as conn:
        ads = list_sponsored_ads(conn)
        bml_ad = next(a for a in ads if a["campaign_name"] == "bml-business-credit")
        assert bml_ad["is_active"] == 1
        bml_id = bml_ad["id"]

    # 4. Toggle campaign status
    resp_toggle = client.post(f"/admin/ads/{bml_id}/toggle", auth=auth, follow_redirects=True)
    assert resp_toggle.status_code == 200
    with get_db(temp_db_path) as conn:
        toggled = get_sponsored_ad(conn, bml_id)
        assert toggled["is_active"] == 0

    # 5. Broadcast campaign (mock send)
    mock_send = MagicMock(return_value=(True, "OK"))
    monkeypatch.setattr("alerts.telegram.send_telegram_message", mock_send)
    with get_db(temp_db_path) as conn:
        register_or_update_telegram_subscriber(conn, chat_id="777999", name="Tender Lead", disciplines=["All"])

    resp_broadcast = client.post(f"/admin/ads/{bml_id}/broadcast", auth=auth, follow_redirects=True)
    assert resp_broadcast.status_code == 200
    assert "Broadcast for" in resp_broadcast.text and "Bank of Maldives" in resp_broadcast.text and "completed" in resp_broadcast.text

    # 6. Delete campaign
    resp_delete = client.post(f"/admin/ads/{bml_id}/delete", auth=auth, follow_redirects=True)
    assert resp_delete.status_code == 200
    with get_db(temp_db_path) as conn:
        assert get_sponsored_ad(conn, bml_id) is None


def test_start_deep_linking_alert_selection(monkeypatch, temp_db):
    monkeypatch.setenv("KHULAASAA_DB_PATH", str(temp_db))
    from alerts.telegram import handle_incoming_telegram_update

    mock_send = MagicMock(return_value=(True, "OK"))
    monkeypatch.setattr("alerts.telegram.send_telegram_message", mock_send)

    # 1. User clicked "Connect Telegram" with Breaking News & Followed Stories only
    update_news = {
        "update_id": 201,
        "message": {
            "chat": {"id": 888111},
            "from": {"first_name": "Aishath", "username": "aishath"},
            "text": "/start alerts_breaking_followed",
        },
    }
    handle_incoming_telegram_update(update_news)
    with get_db(temp_db) as conn:
        sub = get_telegram_subscriber(conn, "888111")
        assert sub is not None
        assert "breaking" in sub["keywords"]
        assert "ras-male" in sub["keywords"]
        assert len(sub["disciplines"]) == 0  # No tenders requested!

    # 2. User clicked "Connect Tender Alerts" for Construction only
    update_tenders = {
        "update_id": 202,
        "message": {
            "chat": {"id": 888222},
            "from": {"first_name": "Contractor"},
            "text": "/start tenders_construction",
        },
    }
    handle_incoming_telegram_update(update_tenders)
    with get_db(temp_db) as conn:
        sub_tender = get_telegram_subscriber(conn, "888222")
        assert sub_tender is not None
        assert "Construction" in sub_tender["disciplines"]
        assert "breaking" not in sub_tender["keywords"]

    # 3. User sends bare /start -> Defaults to ALL feeds active
    update_default = {
        "update_id": 203,
        "message": {
            "chat": {"id": 888333},
            "from": {"first_name": "New User"},
            "text": "/start",
        },
    }
    handle_incoming_telegram_update(update_default)
    with get_db(temp_db) as conn:
        sub_all = get_telegram_subscriber(conn, "888333")
        assert sub_all is not None
        assert sub_all["disciplines"] == ["All"]
        assert "all_news" in sub_all["keywords"]
        assert "breaking" in sub_all["keywords"]
        assert "janaza" in sub_all["keywords"]

    # 4. User toggles janaza off via inline keyboard callback
    update_toggle_janaza = {
        "update_id": 204,
        "callback_query": {
            "id": "cb123",
            "from": {"id": 888333},
            "message": {"message_id": 99, "chat": {"id": 888333}},
            "data": "toggle:janaza",
        },
    }
    handle_incoming_telegram_update(update_toggle_janaza)
    with get_db(temp_db) as conn:
        sub_toggled = get_telegram_subscriber(conn, "888333")
        assert "janaza" not in sub_toggled["keywords"]

    # 5. User updates preferences on web portal
    from starlette.testclient import TestClient
    from main import app
    client = TestClient(app)
    resp = client.post(
        "/api/alerts/preferences",
        json={
            "chat_id": "888333",
            "all_news": True,
            "breaking": False,
            "janaza": True,
            "tenders_enabled": True,
            "disciplines": ["Construction", "Information Technology"],
            "storylines": ["ras-male"],
        },
    )
    assert resp.status_code == 200
    assert resp.json().get("ok") is True
    with get_db(temp_db) as conn:
        sub_web = get_telegram_subscriber(conn, "888333")
        assert "janaza" in sub_web["keywords"]
        assert "breaking" not in sub_web["keywords"]
        assert "all_news" in sub_web["keywords"]
        assert sub_web["disciplines"] == ["Construction", "Information Technology"]


def test_telegram_module_has_zero_emojis():
    """Enforce strict design policy: zero emojis anywhere in Telegram bot text, menus, or keyboards."""
    content = Path("alerts/telegram.py").read_text(encoding="utf-8")
    emojis = [
        c for c in content
        if (0x1F300 <= ord(c) <= 0x1F9FF)
        or (0x2600 <= ord(c) <= 0x27BF)
        or (0x1FA70 <= ord(c) <= 0x1FAFF)
    ]
    assert emojis == [], f"Found unexpected emojis in alerts/telegram.py: {emojis}"


def test_dispatch_news_alerts(temp_db, monkeypatch):
    from alerts.telegram import dispatch_news_alerts

    mock_send = MagicMock(return_value=(True, "Alert sent successfully"))
    monkeypatch.setattr("alerts.telegram.send_telegram_message", mock_send)

    with get_db(temp_db) as conn:
        register_or_update_telegram_subscriber(
            conn,
            chat_id="554433",
            name="News Reader",
            disciplines=[],
            keywords=["breaking", "all_news"],
        )

        articles = [
            {
                "id": "mihaaru-9901",
                "headline": "High Court ruling on parliamentary election",
                "summary": "Full summary of the court decision",
                "section": "breaking",
                "topic": "policy",
                "sources": ["mihaaru"],
                "url": "https://mihaaru.com/news/9901",
            },
            {
                "id": "sun-9902",
                "headline": "Weather advisory issued for Southern Atolls",
                "summary": "Met office warning",
                "section": "general",
                "topic": "weather",
                "sources": ["sun"],
                "url": "https://sun.mv/9902",
            },
        ]

        dispatched = dispatch_news_alerts(conn, articles, bot_token="fake_bot_token")
        assert len(dispatched) == 2
        assert mock_send.call_count == 2
        assert dispatched[0]["status"] == "delivered"

        # Re-dispatching should be deduplicated
        mock_send.reset_mock()
        dispatched_second = dispatch_news_alerts(conn, articles, bot_token="fake_bot_token")
        assert len(dispatched_second) == 0
        assert mock_send.call_count == 0


def test_alerts_only_sent_for_items_received_after_bot_started(temp_db, monkeypatch):
    from alerts.telegram import dispatch_news_alerts

    mock_send = MagicMock(return_value=(True, "Delivered"))
    monkeypatch.setattr("alerts.telegram.send_telegram_message", mock_send)

    with get_db(temp_db) as conn:
        # 1. Article received yesterday
        conn.execute(
            """
            INSERT INTO articles (id, headline, summary, published_raw, source_key, url, section, topic, created_at)
            VALUES ('art-yesterday', 'Yesterday Economy Report', 'Summary', 'Yesterday', 'sun', 'https://sun.mv/1', 'general', 'policy', '2026-10-15 10:00:00');
            """
        )

        # 2. User starts the bot today at 12:00
        conn.execute(
            """
            INSERT INTO telegram_subscribers (chat_id, name, disciplines, keywords, is_active, created_at)
            VALUES ('112233', 'Late Subscriber', '["All"]', '["all_news"]', 1, '2026-10-16 12:00:00');
            """
        )

        # 3. Article received today at 13:00 (after user started the bot)
        conn.execute(
            """
            INSERT INTO articles (id, headline, summary, published_raw, source_key, url, section, topic, created_at)
            VALUES ('art-today', 'Today Breaking Decision', 'Summary', 'Today', 'mihaaru', 'https://mihaaru.com/2', 'breaking', 'policy', '2026-10-16 13:00:00');
            """
        )

        articles = [
            {"id": "art-yesterday", "headline": "Yesterday Economy Report", "sources": ["sun"], "section": "general", "created_at": "2026-10-15 10:00:00"},
            {"id": "art-today", "headline": "Today Breaking Decision", "sources": ["mihaaru"], "section": "breaking", "created_at": "2026-10-16 13:00:00"},
        ]

        # 4. Dispatch news
        sent = dispatch_news_alerts(conn, articles, bot_token="fake_token")

        # 5. Only the article received after the bot was started should be delivered
        assert len(sent) == 1
        assert sent[0]["article_id"] == "art-today"
        assert mock_send.call_count == 1

        # 6. Verify news alert text is simple, clean, and contains NO partner spotlight
        msg_text = mock_send.call_args[0][0]
        assert "Today Breaking Decision" in msg_text
        assert "Reported by:" in msg_text
        assert "Partner Spotlight" not in msg_text
        assert "Ad:" not in msg_text
