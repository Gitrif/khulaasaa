from unittest.mock import MagicMock
import pytest
from pathlib import Path

from alerts.telegram import (
    matches_interest,
    matches_news_interest,
    dispatch_tender_alerts,
    dispatch_news_alerts,
    format_pro_tier_message,
    build_settings_keyboard_and_text,
    handle_incoming_telegram_update,
)
from alerts.viber import (
    handle_viber_webhook_event,
    dispatch_viber_bid_alerts,
)
from data.database import (
    init_db,
    get_db,
    register_or_update_telegram_subscriber,
    is_subscriber_paid,
    update_telegram_subscriber_plan,
    register_or_update_viber_subscriber,
    is_viber_subscriber_paid,
    update_viber_subscriber_plan,
)


@pytest.fixture
def temp_db(tmp_path: Path):
    db_file = tmp_path / "test_alert_tiers.db"
    init_db(db_file)
    return db_file


def test_matches_interest_free_vs_paid():
    bid_construction = {
        "title": "Harbour Construction Project",
        "title_en": "Harbour Construction Project",
        "discipline": "Construction",
        "reference_number": "TES/2026/01",
    }
    bid_it = {
        "title": "Supply of Cloud Servers",
        "title_en": "Supply of Cloud Servers",
        "discipline": "IT",
        "reference_number": "TES/2026/02",
    }

    # Subscriber with custom filter: only wants IT
    it_sub_prefs = {
        "disciplines": ["IT"],
        "keywords": ["servers"],
    }

    # 1. Paid Subscriber (is_paid=True): Receives customized filtering
    assert matches_interest(bid_it, it_sub_prefs, is_paid=True) is True
    assert matches_interest(bid_construction, it_sub_prefs, is_paid=True) is False

    # 2. Free Subscriber (is_paid=False): Receives the NORMAL feed (all tenders)
    # Even though free user selected only IT, without Pro they get all tenders
    assert matches_interest(bid_it, it_sub_prefs, is_paid=False) is True
    assert matches_interest(bid_construction, it_sub_prefs, is_paid=False) is True

    # 3. Free Subscriber who explicitly muted tenders (empty disciplines)
    muted_sub_prefs = {
        "disciplines": [],
        "keywords": [],
    }
    assert matches_interest(bid_it, muted_sub_prefs, is_paid=False) is False
    assert matches_interest(bid_construction, muted_sub_prefs, is_paid=False) is False


def test_matches_news_interest_free_vs_paid():
    general_article = {
        "id": "art-1",
        "headline": "President meets local council",
        "section": "general",
        "tags": ["governance"],
    }
    custom_topic_article = {
        "id": "art-2",
        "headline": "Ras Malé land reclamation progress",
        "section": "business",
        "tags": ["ras-male", "infrastructure"],
    }

    # Subscriber who set a custom storyline filter: only ras-male
    custom_prefs = ["ras-male"]

    # 1. Paid Pro subscriber: only receives articles matching their custom keyword
    assert matches_news_interest(custom_topic_article, custom_prefs, is_paid=True) is True
    assert matches_news_interest(general_article, custom_prefs, is_paid=True) is False

    # 2. Free subscriber: receives normal feed
    assert matches_news_interest(custom_topic_article, custom_prefs, is_paid=False) is True
    assert matches_news_interest(general_article, custom_prefs, is_paid=False) is True

    # 3. Subscriber with news muted (empty list)
    assert matches_news_interest(general_article, [], is_paid=False) is False


def test_dispatch_tender_alerts_tier_behavior(temp_db, monkeypatch):
    mock_send = MagicMock(return_value=(True, "Delivered"))
    monkeypatch.setattr("alerts.telegram.send_telegram_message", mock_send)

    with get_db(temp_db) as conn:
        # Register a Free subscriber (is_paid=0)
        register_or_update_telegram_subscriber(
            conn,
            chat_id="free_user_1",
            name="Free User",
            disciplines=["IT"],
            is_paid=0,
            reset_start_time=True,
        )

        # Register a Pro subscriber (is_paid=1)
        register_or_update_telegram_subscriber(
            conn,
            chat_id="pro_user_1",
            name="Pro User",
            disciplines=["IT"],
            is_paid=1,
            reset_start_time=True,
        )

        bids = [
            {
                "notice_id": "notice-it",
                "title": "Supply of Network Switches",
                "discipline": "IT",
                "agency": "NCIT",
                "source_url": "https://gazette.gov.mv/iulaan/1",
            },
            {
                "notice_id": "notice-const",
                "title": "Hospital Renovation Works",
                "discipline": "Construction",
                "agency": "IGMH",
                "source_url": "https://gazette.gov.mv/iulaan/2",
            },
        ]

        dispatched = dispatch_tender_alerts(conn, bids, bot_token="fake_token", force_resend=True)

        # Free user receives BOTH tenders (normal feed: 2 notices)
        # Pro user receives ONLY the IT tender (customized filter: 1 notice)
        # Total dispatched: 3
        free_dispatches = [d for d in dispatched if d["chat_id"] == "free_user_1"]
        pro_dispatches = [d for d in dispatched if d["chat_id"] == "pro_user_1"]

        assert len(free_dispatches) == 2
        assert len(pro_dispatches) == 1
        assert pro_dispatches[0]["notice_id"] == "notice-it"

        # Check that the free user message contains the Pro upgrade promotional footer
        free_calls = [c for c in mock_send.call_args_list if c[1]["chat_id"] == "free_user_1"]
        for c in free_calls:
            msg_html = c[0][0]
            assert "Upgrade to Pro (MVR 50/mo)" in msg_html
            kb = c[1]["reply_markup"]
            assert any("Upgrade to Pro" in btn["text"] for row in kb["inline_keyboard"] for btn in row)

        # Check that the Pro user message does NOT contain the promotional upgrade notice
        pro_calls = [c for c in mock_send.call_args_list if c[1]["chat_id"] == "pro_user_1"]
        for c in pro_calls:
            msg_html = c[0][0]
            assert "Upgrade to Pro (MVR 50/mo) for custom keyword" not in msg_html
            kb = c[1]["reply_markup"]
            assert not any("Upgrade to Pro" in btn["text"] for row in kb["inline_keyboard"] for btn in row)


def test_subscriber_paid_hierarchy_and_plan_updates(temp_db):
    with get_db(temp_db) as conn:
        # 1. New subscriber is Free by default
        register_or_update_telegram_subscriber(conn, chat_id="user_plan_test", name="Tester")
        assert is_subscriber_paid(conn, "user_plan_test") is False

        # 2. Upgrade subscriber to Pro (MVR 50/mo)
        update_telegram_subscriber_plan(conn, "user_plan_test", is_paid=1)
        assert is_subscriber_paid(conn, "user_plan_test") is True

        # 3. Downgrade back to Free
        update_telegram_subscriber_plan(conn, "user_plan_test", is_paid=0)
        assert is_subscriber_paid(conn, "user_plan_test") is False

        # 4. If linked user in users table is paid, is_subscriber_paid reflects it
        conn.execute(
            """
            INSERT INTO users (email, password_hash, full_name, telegram_chat_id, is_paid)
            VALUES ('pro@khulaasaa.tech', 'hash', 'Pro Member', 'user_plan_test', 1);
            """
        )
        assert is_subscriber_paid(conn, "user_plan_test") is True


def test_telegram_pro_command_and_settings(temp_db, monkeypatch):
    mock_send = MagicMock(return_value=(True, "OK"))
    monkeypatch.setattr("alerts.telegram.send_telegram_message", mock_send)
    monkeypatch.setattr("data.database.get_db", lambda *args, **kwargs: get_db(temp_db))

    with get_db(temp_db) as conn:
        register_or_update_telegram_subscriber(conn, chat_id="tg_cmd_test", name="Cmd Tester", is_paid=0)

    # 1. Test /pro command for Free user
    update_pro = {
        "update_id": 1,
        "message": {
            "chat": {"id": "tg_cmd_test"},
            "from": {"first_name": "Cmd"},
            "text": "/pro",
        },
    }
    handle_incoming_telegram_update(update_pro)
    mock_send.assert_called_once()
    pro_text = mock_send.call_args[0][0]
    assert "Upgrade to Khulaasaa Pro (MVR 50 / month)" in pro_text
    assert "Free Tier (Normal Feed)" in pro_text
    assert "7730000123456" in pro_text

    # 2. Test /pro command for Pro user
    with get_db(temp_db) as conn:
        update_telegram_subscriber_plan(conn, "tg_cmd_test", is_paid=1)

    mock_send.reset_mock()
    handle_incoming_telegram_update(update_pro)
    mock_send.assert_called_once()
    pro_text_paid = mock_send.call_args[0][0]
    assert "Khulaasaa Pro — Active Subscription" in pro_text_paid
    assert "ACTIVE (MVR 50 / month)" in pro_text_paid

    # 3. Test /settings shows plan badge
    mock_send.reset_mock()
    update_settings = {
        "update_id": 2,
        "message": {
            "chat": {"id": "tg_cmd_test"},
            "from": {"first_name": "Cmd"},
            "text": "/settings",
        },
    }
    handle_incoming_telegram_update(update_settings)
    mock_send.assert_called_once()
    settings_text = mock_send.call_args[0][0]
    assert "Pro Tier (Active — MVR 50/mo)" in settings_text


def test_telegram_gating_custom_filter_callbacks(temp_db, monkeypatch):
    mock_send = MagicMock(return_value=(True, "OK"))
    mock_answer = MagicMock(return_value=True)
    mock_edit = MagicMock(return_value=(True, "Message updated"))
    monkeypatch.setattr("alerts.telegram.send_telegram_message", mock_send)
    monkeypatch.setattr("alerts.telegram.answer_telegram_callback_query", mock_answer)
    monkeypatch.setattr("alerts.telegram.edit_telegram_message", mock_edit)
    monkeypatch.setattr("data.database.get_db", lambda *args, **kwargs: get_db(temp_db))

    with get_db(temp_db) as conn:
        register_or_update_telegram_subscriber(conn, chat_id="gate_user", name="Gate Tester", is_paid=0)

    # Free user toggles custom trade discipline in settings
    cb_update = {
        "update_id": 3,
        "callback_query": {
            "id": "cb_123",
            "from": {"id": "gate_user", "first_name": "Gate"},
            "message": {"message_id": 55, "chat": {"id": "gate_user"}},
            "data": "disc:Construction",
        },
    }
    handle_incoming_telegram_update(cb_update)

    mock_answer.assert_called_once()
    assert "Subscribed Construction" in mock_answer.call_args[1]["text"]

    # Updated settings message reflects free tier notice informing user that custom alerts require Pro
    mock_edit.assert_called_once()
    edited_text = mock_edit.call_args[0][2]
    assert "Free normal feed active. Upgrade to Pro (MVR 50/mo) for custom keyword & industry filters: /pro" in edited_text

    # And in dispatching, because user is free (is_paid=0), custom discipline does NOT filter out other tenders
    with get_db(temp_db) as conn:
        it_bid = {"notice_id": "b-it", "discipline": "IT", "title": "Network Servers"}
        assert matches_interest(it_bid, {"disciplines": ["Construction"]}, is_paid=is_subscriber_paid(conn, "gate_user")) is True


def test_viber_pro_command_and_alerts(temp_db, monkeypatch):
    mock_viber_send = MagicMock(return_value={"status": 0})
    monkeypatch.setattr("alerts.viber.send_viber_message", mock_viber_send)
    monkeypatch.setattr("alerts.viber.get_db", lambda *args, **kwargs: get_db(temp_db))

    with get_db(temp_db) as conn:
        register_or_update_viber_subscriber(conn, viber_user_id="viber_user_1", name="Viber Free", is_paid=0)
        register_or_update_viber_subscriber(conn, viber_user_id="viber_user_2", name="Viber Pro", is_paid=1)

    # 1. /pro command on Viber for free user
    event_free = {
        "event": "message",
        "sender": {"id": "viber_user_1", "name": "Viber Free"},
        "message": {"text": "/pro"},
    }
    handle_viber_webhook_event(event_free)
    mock_viber_send.assert_called_once()
    viber_text = mock_viber_send.call_args[0][1]
    assert "Upgrade to Khulaasaa Pro (MVR 50 / month)" in viber_text
    assert "Free Tier (Normal Feed)" in viber_text

    # 2. /pro command on Viber for Pro user
    mock_viber_send.reset_mock()
    event_pro = {
        "event": "message",
        "sender": {"id": "viber_user_2", "name": "Viber Pro"},
        "message": {"text": "/pro"},
    }
    handle_viber_webhook_event(event_pro)
    mock_viber_send.assert_called_once()
    viber_pro_text = mock_viber_send.call_args[0][1]
    assert "Khulaasaa Pro (Active Subscription)" in viber_pro_text
    assert "ACTIVE (MVR 50 / month)" in viber_pro_text

    # 3. Viber Bid Dispatch appends footer for Free user
    mock_viber_send.reset_mock()
    bids = [{"title": "Tender Notice", "agency": "MMPRC", "ref": "B-01"}]
    with get_db(temp_db) as conn:
        delivered = dispatch_viber_bid_alerts(bids, bot_token="fake_viber_token")

    assert delivered == 2
    # Verify free user got the upgrade prompt
    free_call = [c for c in mock_viber_send.call_args_list if c[0][0] == "viber_user_1"][0]
    assert "Upgrade to Pro (MVR 50/mo)" in free_call[0][1]
    # Verify pro user did not get the prompt
    pro_call = [c for c in mock_viber_send.call_args_list if c[0][0] == "viber_user_2"][0]
    assert "Upgrade to Pro (MVR 50/mo)" not in pro_call[0][1]
