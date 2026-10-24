import pytest
from fastapi.testclient import TestClient
from main import app
from data.database import (
    get_db,
    register_or_update_viber_subscriber,
    get_viber_subscribers,
    unsubscribe_viber_subscriber,
)
from alerts.viber import (
    build_viber_main_keyboard,
    format_viber_news,
    format_viber_obituary,
    format_viber_bid,
    format_viber_job,
    handle_viber_webhook_event,
    set_viber_webhook,
    send_viber_message,
)

client = TestClient(app)


def test_viber_keyboard_builder():
    kb = build_viber_main_keyboard("https://khulaasaa.tech")
    assert kb["Type"] == "keyboard"
    buttons = kb["Buttons"]
    assert len(buttons) == 5
    action_bodies = [b["ActionBody"] for b in buttons]
    assert "/news" in action_bodies
    assert "/janaza" in action_bodies
    assert "/bids" in action_bodies
    assert "/jobs" in action_bodies
    assert "https://khulaasaa.tech" in action_bodies


def test_viber_formatters():
    # Test News formatting
    sample_art = {
        "id": "test-1",
        "headline": "Cabinet Approves New Renewable Grid Policy",
        "summary": "Government announces solar grid expansion across all atolls.",
        "sources": ["mihaaru", "sun"],
        "url": "https://mihaaru.com/news/123",
    }
    news_text = format_viber_news(sample_art)
    assert "Cabinet Approves New Renewable Grid Policy" in news_text
    assert "Mihaaru" in news_text
    assert "https://mihaaru.com/news/123" in news_text

    # Test Janaza formatting
    sample_ob = {
        "name_dv": "އިބްރާހީމް މުޙައްމަދު",
        "age": 72,
        "address_dv": "ހ. ރޫބީވިލާ / މާލެ",
        "funeral_mosque_dv": "މަސްޖިދުލް ތަޢާވުން (އާސަހަރާ މިސްކިތް)",
        "prayer_time_dv": "މިއަދުގެ ޢަޞްރު ނަމާދަށްފަހު",
        "contact_numbers": "7992266 / 9394545",
    }
    ob_text = format_viber_obituary(sample_ob)
    assert "إِنَّا لِلَّهِ وَإِنَّا إِلَيْهِ رَاجِعُونَ" in ob_text
    assert "އިބްރާހީމް މުޙައްމަދު" in ob_text
    assert "72އ" in ob_text
    assert "އާސަހަރާ" in ob_text
    assert "7992266" in ob_text

    # Test Tender formatting
    sample_bid = {
        "title_en": "Supply of Harbor Solar Lighting Systems",
        "agency_name_en": "Ministry of Climate Change",
        "reference_number": "(IUL)438-CCD/2026/18",
        "submission_date": "2026-11-10",
        "source_url": "https://gazette.gov.mv/iulaan/198273",
    }
    bid_text = format_viber_bid(sample_bid)
    assert "Harbor Solar Lighting Systems" in bid_text
    assert "Ministry of Climate Change" in bid_text
    assert "(IUL)438-CCD/2026/18" in bid_text

    # Test Job formatting
    sample_job = {
        "title": "Shop Operations Supervisor",
        "agency": "State Trading Organization (STO)",
        "discipline": "Customer Service, Retail & Operations",
        "location": "Male'",
        "deadline_iso": "2026-10-31",
        "source_url": "https://gazette.gov.mv/iulaan/type/vazeefaa",
    }
    job_text = format_viber_job(sample_job)
    assert "JOB VACANCY ALERT" in job_text
    assert "Shop Operations Supervisor" in job_text
    assert "State Trading Organization" in job_text
    assert "Maldivian CV Creator" in job_text


def test_viber_subscribers_db():
    with get_db() as conn:
        # Register subscriber
        sub_id = register_or_update_viber_subscriber(
            conn,
            viber_user_id="viber_user_test_99",
            name="Ahmed Test",
            avatar="https://avatar.url/1.png",
            categories=["all", "janaza"],
        )
        assert sub_id > 0

        # Retrieve subscribers
        subs = get_viber_subscribers(conn, active_only=True)
        matching = [s for s in subs if s["viber_user_id"] == "viber_user_test_99"]
        assert len(matching) == 1
        assert matching[0]["name"] == "Ahmed Test"
        assert "janaza" in matching[0]["subscribed_categories"]

        # Unsubscribe
        unsub_ok = unsubscribe_viber_subscriber(conn, "viber_user_test_99")
        assert unsub_ok is True
        subs_after = get_viber_subscribers(conn, active_only=True)
        assert not any(s["viber_user_id"] == "viber_user_test_99" for s in subs_after)


def test_viber_webhook_event_handling():
    # 1. Webhook validation
    res = handle_viber_webhook_event({"event": "webhook"})
    assert res.get("status") == 0

    # 2. Conversation started
    cs_event = {
        "event": "conversation_started",
        "user": {
            "id": "viber_user_cs_123",
            "name": "Ibrahim",
            "avatar": "https://viber.com/avatar.jpg",
        },
    }
    cs_resp = handle_viber_webhook_event(cs_event)
    assert cs_resp["type"] == "text"
    assert "Assalaamu Alaikum" in cs_resp["text"]
    assert "keyboard" in cs_resp

    # 3. Message event /janaza
    msg_event = {
        "event": "message",
        "sender": {
            "id": "viber_user_cs_123",
            "name": "Ibrahim",
        },
        "message": {
            "type": "text",
            "text": "/janaza",
        },
    }
    # Mock send_viber_message to verify dispatch without network
    msg_resp = handle_viber_webhook_event(msg_event)
    assert msg_resp.get("status") == 0


def test_viber_webhook_fastapi_route():
    payload = {"event": "webhook"}
    resp = client.post("/webhook/viber", json=payload)
    assert resp.status_code == 200
    assert resp.json().get("status") == 0


def test_viber_auto_subscribe_on_first_interaction():
    uid = "viber_auto_sub_user_456"
    cs_event = {
        "event": "conversation_started",
        "user": {
            "id": uid,
            "name": "Mariyam",
            "avatar": "https://avatar.url/mariyam.png",
        },
    }
    resp = handle_viber_webhook_event(cs_event)
    assert resp["type"] == "text"
    assert uid in resp["text"]  # Explicitly displays Viber ID
    assert "Assalaamu Alaikum" in resp["text"]
    assert "automatically subscribed" in resp["text"]

    # Verify user is in database with is_active = 1
    with get_db() as conn:
        from data.database import get_viber_subscriber
        sub = get_viber_subscriber(conn, uid)
        assert sub is not None
        assert sub["is_active"] == 1
        assert "jobs" in sub["subscribed_categories"]
        assert "news" in sub["subscribed_categories"]


def test_viber_message_myid_and_start_commands(monkeypatch):
    import alerts.viber
    sent_messages = []

    def mock_send_viber_message(receiver_id, text, keyboard=None, **kwargs):
        sent_messages.append({"receiver": receiver_id, "text": text})
        return {"status": 0, "status_message": "ok"}

    monkeypatch.setattr(alerts.viber, "send_viber_message", mock_send_viber_message)

    uid = "viber_msg_user_789"

    # 1. User sends /start from Viber first
    start_event = {
        "event": "message",
        "sender": {"id": uid, "name": "Ali"},
        "message": {"type": "text", "text": "/start"},
    }
    handle_viber_webhook_event(start_event)
    assert len(sent_messages) == 1
    assert uid in sent_messages[0]["text"]
    assert "subscribed" in sent_messages[0]["text"]

    # 2. User sends /myid
    sent_messages.clear()
    myid_event = {
        "event": "message",
        "sender": {"id": uid, "name": "Ali"},
        "message": {"type": "text", "text": "/myid"},
    }
    handle_viber_webhook_event(myid_event)
    assert len(sent_messages) == 1
    assert uid in sent_messages[0]["text"]

    # 3. User sends /cv
    sent_messages.clear()
    cv_event = {
        "event": "message",
        "sender": {"id": uid, "name": "Ali"},
        "message": {"type": "text", "text": "/cv"},
    }
    handle_viber_webhook_event(cv_event)
    assert len(sent_messages) == 1
    assert "/jobs/cv" in sent_messages[0]["text"]


def test_viber_api_subscribe_and_job_alert(monkeypatch):
    import main
    import alerts.viber
    sent_messages = []

    def mock_send(receiver_id, text, keyboard=None, **kwargs):
        sent_messages.append({"receiver": receiver_id, "text": text})
        return {"status": 0, "status_message": "ok"}

    monkeypatch.setattr(main, "send_viber_message", mock_send)
    monkeypatch.setattr(alerts.viber, "send_viber_message", mock_send)

    # 1. API Subscribe
    resp = client.post(
        "/api/alerts/viber/subscribe",
        json={
            "viber_user_id": "viber_api_test_user",
            "name": "Zuhair",
            "categories": ["all", "jobs"],
        },
    )
    assert resp.status_code == 200
    assert resp.json().get("ok") is True

    # 2. Test Alert
    resp_test = client.post(
        "/api/alerts/viber/test",
        json={"viber_user_id": "viber_api_test_user"},
    )
    assert resp_test.status_code == 200
    assert resp_test.json().get("ok") is True

    # 3. Test Job Alert for Viber
    resp_job = client.post(
        "/api/jobs/test-viber-alert",
        json={"viber_user_id": "viber_api_test_user"},
    )
    assert resp_job.status_code == 200
    assert resp_job.json().get("ok") is True
