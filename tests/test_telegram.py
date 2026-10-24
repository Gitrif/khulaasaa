from unittest.mock import MagicMock
import pytest
from pathlib import Path

from alerts.telegram import (
    matches_interest,
    format_tender_alert_html,
    send_telegram_message,
    dispatch_tender_alerts,
)
from data.database import (
    init_db,
    get_db,
    register_or_update_telegram_subscriber,
    get_telegram_subscribers,
)


@pytest.fixture
def temp_db(tmp_path: Path):
    db_file = tmp_path / "test_telegram.db"
    init_db(db_file)
    return db_file


def test_matches_interest():
    bid = {
        "title": "Upgrading of A.Dh Fenfushi Harbour",
        "title_en": "Upgrading of A.Dh Fenfushi Harbour",
        "agency": "Ministry of National Planning, Housing and Infrastructure",
        "discipline": "Construction",
        "reference_number": "TES/2020/W-021",
        "submission_location": "National Tender Board Reception",
    }

    # 1. No filters -> matches all
    assert matches_interest(bid, {}) is True
    assert matches_interest(bid, {"disciplines": [], "keywords": []}) is True

    # 2. Match by discipline
    assert matches_interest(bid, {"disciplines": ["Construction"]}) is True
    assert matches_interest(bid, {"disciplines": ["IT", "Medical"]}) is False

    # 3. Match by keyword (case-insensitive)
    assert matches_interest(bid, {"keywords": ["harbour"]}) is True
    assert matches_interest(bid, {"keywords": ["FENFUSHI"]}) is True
    assert matches_interest(bid, {"keywords": ["Solar", "Generator"]}) is False

    # 4. Combination matching (OR semantics)
    assert matches_interest(bid, {"disciplines": ["IT"], "keywords": ["harbour"]}) is True
    assert matches_interest(bid, {"disciplines": ["IT"], "keywords": ["solar"]}) is False


def test_format_tender_alert_html():
    bid = {
        "title": "އއ. އުކުޅަހު ޞިއްޙީ މަރުކަޒުގެ ލެބޯޓްރީ ޢިމާރާތުގެ މަސައްކަތް ކޮށްދޭނެ ފަރާތެއް ހޯދުމަށް",
        "title_en": "Seeking contractor for AA. Ukulhas Health Centre Laboratory Building works",
        "agency": "Ministry of Health",
        "entity_type": "Ministry",
        "discipline": "Construction",
        "gazette_type": "Bid",
        "ref": "(IUL)23-L/23/2026/45",
        "submission_date": "2026-11-15T11:00:00",
        "submission_location": "AA. Ukulhas Health Centre Office",
        "info_date": "2026-10-25 10:00",
        "info_location": "Online via Zoom",
        "source_url": "https://gazette.gov.mv/iulaan/999999",
    }

    msg = format_tender_alert_html(bid)
    assert "NEW TENDER ALERT" in msg
    assert "Seeking contractor for AA. Ukulhas" in msg
    assert "އއ. އުކުޅަހު" in msg
    assert "Ministry of Health" in msg
    assert "(IUL)23-L/23/2026/45" in msg
    assert "2026-11-15T11:00:00" in msg
    assert "AA. Ukulhas Health Centre Office" in msg
    assert "Online via Zoom" in msg
    assert "https://gazette.gov.mv/iulaan/999999" in msg


def test_send_telegram_message_mocked():
    session_mock = MagicMock()
    resp_mock = MagicMock()
    resp_mock.status_code = 200
    resp_mock.json.return_value = {"ok": True, "result": {"message_id": 12345}}
    session_mock.post.return_value = resp_mock

    ok, status = send_telegram_message(
        "<b>Hello World</b>",
        chat_id="12345678",
        bot_token="test_token_xyz",
        session=session_mock,
    )
    assert ok is True
    assert "successfully" in status
    session_mock.post.assert_called_once()
    payload = session_mock.post.call_args[1]["json"]
    assert payload["chat_id"] == "12345678"
    assert payload["text"] == "<b>Hello World</b>"
    assert payload["parse_mode"] == "HTML"


def test_dispatch_tender_alerts_with_dedupe(temp_db, monkeypatch):
    # Mock send_telegram_message to always succeed
    mock_send = MagicMock(return_value=(True, "Alert sent successfully"))
    monkeypatch.setattr("alerts.telegram.send_telegram_message", mock_send)

    with get_db(temp_db) as conn:
        # Register a subscriber with interest in Construction
        sub_id = register_or_update_telegram_subscriber(
            conn,
            chat_id="998877",
            name="Ibrahim Test",
            disciplines=["Construction"],
            keywords=["Harbour"],
            is_paid=1,
        )
        assert sub_id > 0

        bids = [
            {
                "notice_id": "1001",
                "title": "Kamadhoo Harbour Works",
                "discipline": "Construction",
                "agency": "Ministry of Planning",
                "ref": "TES/KAM/01",
            },
            {
                "notice_id": "1002",
                "title": "Supply of Laptops",
                "discipline": "IT",
                "agency": "HDC",
                "ref": "HDC/IT/02",
            },
        ]

        # Dispatch with token
        dispatched = dispatch_tender_alerts(conn, bids, bot_token="fake_bot_token")
        assert len(dispatched) == 1
        assert dispatched[0]["notice_id"] == "1001"
        assert dispatched[0]["status"] == "delivered"
        assert mock_send.call_count == 1

        # Second dispatch with same bids should NOT resend due to deduplication table
        mock_send.reset_mock()
        dispatched_second = dispatch_tender_alerts(conn, bids, bot_token="fake_bot_token")
        assert len(dispatched_second) == 0
        assert mock_send.call_count == 0


def test_handle_incoming_telegram_commands(temp_db, monkeypatch):
    from alerts.telegram import handle_incoming_telegram_update

    # Mock DB path to temp_db
    monkeypatch.setenv("KHULAASAA_DB_PATH", str(temp_db))

    mock_send = MagicMock(return_value=(True, "Success"))
    monkeypatch.setattr("alerts.telegram.send_telegram_message", mock_send)

    # 1. /start command
    update_start = {
        "update_id": 100,
        "message": {
            "chat": {"id": 123456},
            "from": {"first_name": "Ibrahim", "username": "ibrahim_mv"},
            "text": "/start",
        },
    }
    handle_incoming_telegram_update(update_start)
    assert mock_send.call_count == 1
    call_text = mock_send.call_args[0][0]
    assert "Maruhabaa, Ibrahim" in call_text
    assert "123456" in call_text

    # Verify user was saved in DB
    with get_db(temp_db) as conn:
        sub = conn.execute("SELECT * FROM telegram_subscribers WHERE chat_id = '123456'").fetchone()
        assert sub is not None
        assert "Ibrahim" in sub["name"]

    # 2. /tenders command
    mock_send.reset_mock()
    update_tenders = {
        "update_id": 101,
        "message": {
            "chat": {"id": 123456},
            "from": {"first_name": "Ibrahim"},
            "text": "/tenders",
        },
    }
    handle_incoming_telegram_update(update_tenders)
    assert mock_send.call_count == 1
    tenders_text = mock_send.call_args[0][0]
    assert "LATEST GOVERNMENT TENDERS" in tenders_text or "No active tenders" in tenders_text

    # 3. /help command
    mock_send.reset_mock()
    update_help = {
        "update_id": 102,
        "message": {
            "chat": {"id": 123456},
            "from": {"first_name": "Ibrahim"},
            "text": "/help",
        },
    }
    handle_incoming_telegram_update(update_help)
    assert mock_send.call_count == 1
    help_text = mock_send.call_args[0][0]
    assert "Khulaasaa Bot Help" in help_text

    # 4. /settings command with interactive keyboard
    mock_send.reset_mock()
    update_settings = {
        "update_id": 103,
        "message": {
            "chat": {"id": 123456},
            "from": {"first_name": "Ibrahim"},
            "text": "/settings",
        },
    }
    handle_incoming_telegram_update(update_settings)
    assert mock_send.call_count == 1
    settings_text = mock_send.call_args[0][0]
    assert "Khulaasaa Alert Preferences" in settings_text
    reply_markup = mock_send.call_args[1].get("reply_markup")
    assert reply_markup is not None
    assert "inline_keyboard" in reply_markup

    # 5. Callback query toggle: toggle:breaking
    mock_edit = MagicMock(return_value=(True, "Message updated"))
    mock_answer = MagicMock(return_value=True)
    monkeypatch.setattr("alerts.telegram.edit_telegram_message", mock_edit)
    monkeypatch.setattr("alerts.telegram.answer_telegram_callback_query", mock_answer)

    cb_update = {
        "update_id": 104,
        "callback_query": {
            "id": "cb_query_999",
            "from": {"id": 123456, "first_name": "Ibrahim"},
            "message": {
                "message_id": 50,
                "chat": {"id": 123456},
            },
            "data": "toggle:breaking",
        },
    }
    handle_incoming_telegram_update(cb_update)
    assert mock_answer.call_count == 1
    assert mock_edit.call_count == 1

    # Verify that 'breaking' was toggled in SQLite
    with get_db(temp_db) as conn:
        import json
        sub_row = conn.execute("SELECT keywords FROM telegram_subscribers WHERE chat_id = '123456'").fetchone()
        kw_list = json.loads(sub_row["keywords"])
        assert "breaking" not in kw_list  # was toggled off

    # 6. Callback query toggle: topic:ras-male
    mock_edit.reset_mock()
    mock_answer.reset_mock()
    cb_topic_update = {
        "update_id": 105,
        "callback_query": {
            "id": "cb_query_1000",
            "from": {"id": 123456, "first_name": "Ibrahim"},
            "message": {
                "message_id": 50,
                "chat": {"id": 123456},
            },
            "data": "topic:bridge-safety",
        },
    }
    handle_incoming_telegram_update(cb_topic_update)
    assert mock_answer.call_count == 1
    assert mock_edit.call_count == 1

    with get_db(temp_db) as conn:
        sub_row = conn.execute("SELECT keywords FROM telegram_subscribers WHERE chat_id = '123456'").fetchone()
        kw_list = json.loads(sub_row["keywords"])
        assert "bridge-safety" in kw_list  # was toggled on

    # 7. Callback query toggle: toggle:jobs
    mock_edit.reset_mock()
    mock_answer.reset_mock()
    cb_jobs = {
        "update_id": 106,
        "callback_query": {
            "id": "cb_query_1001",
            "from": {"id": 123456, "first_name": "Ibrahim"},
            "message": {"message_id": 50, "chat": {"id": 123456}},
            "data": "toggle:jobs",
        },
    }
    handle_incoming_telegram_update(cb_jobs)
    assert mock_answer.call_count == 1
    assert "Job Alerts" in mock_answer.call_args[1].get("text")
    with get_db(temp_db) as conn:
        sub_row = conn.execute("SELECT keywords FROM telegram_subscribers WHERE chat_id = '123456'").fetchone()
        assert "jobs" in json.loads(sub_row["keywords"])

    # 8. Callback query roadmap: toggle:rentals
    mock_answer.reset_mock()
    cb_rentals = {
        "update_id": 107,
        "callback_query": {
            "id": "cb_query_1002",
            "from": {"id": 123456, "first_name": "Ibrahim"},
            "message": {"message_id": 50, "chat": {"id": 123456}},
            "data": "toggle:rentals",
        },
    }
    handle_incoming_telegram_update(cb_rentals)
    assert mock_answer.call_count == 1
    assert "Phase 3 Roadmap" in mock_answer.call_args[1].get("text")


def test_sponsored_ads_in_alerts_and_broadcast(temp_db, monkeypatch):
    from alerts.telegram import format_tender_alert_html, dispatch_sponsored_broadcast
    from data.database import get_active_sponsored_ad, record_ad_impression, list_sponsored_ads

    monkeypatch.setenv("KHULAASAA_DB_PATH", str(temp_db))
    mock_send = MagicMock(return_value=(True, "Success"))
    monkeypatch.setattr("alerts.telegram.send_telegram_message", mock_send)

    # 1. Verify format_tender_alert_html appends ad_footer
    bid = {"title": "Test Bid", "agency": "Test Agency"}
    msg_with_ad = format_tender_alert_html(bid, ad_footer="<b>Sponsored by Villa Air</b>")
    assert "Sponsored by Villa Air" in msg_with_ad

    # 2. Check canonical sponsored ads in DB
    with get_db(temp_db) as conn:
        ad = get_active_sponsored_ad(conn, target_category="bids")
        assert ad is not None
        assert "sto" in ad["campaign_name"] or "manta" in ad["campaign_name"] or "hooks85" in ad["campaign_name"]

        record_ad_impression(conn, ad["id"])
        updated_ads = list_sponsored_ads(conn)
        matched = next(a for a in updated_ads if a["id"] == ad["id"])
        assert matched["impressions"] >= 1

    # 3. Test sponsored broadcast dispatch
    with get_db(temp_db) as conn:
        # Register a test subscriber
        register_or_update_telegram_subscriber(conn, chat_id="555123", name="Ad Target", disciplines=["Construction"])

        mock_send.reset_mock()
        res = dispatch_sponsored_broadcast(
            conn,
            campaign_name="test-ad-promo",
            sponsor_name="Dhiraagu",
            html_content="Special enterprise discount for tender applicants.",
            target_category="bids",
            bot_token="mock_bot_token",
        )
        assert res["delivered"] == 1
        assert res["sponsor"] == "Dhiraagu"
        assert mock_send.call_count == 1
        broadcast_text = mock_send.call_args[0][0]
        assert "SPONSORED DISPATCH — Dhiraagu" in broadcast_text


