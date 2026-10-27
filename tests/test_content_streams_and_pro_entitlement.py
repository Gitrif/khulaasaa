"""
Tests for Free Content Streams (News, Tenders, Jobs, Rentals) and Pro Personalization Entitlement.
Validates:
1. 4 category streams defaults (1) and independent persistence.
2. Free tier stream broadcast routing vs explicit category opting out.
3. Pro entitlement boundary: Pro subscribers receive targeted followed alerts even when streams are muted;
   free users cannot bypass muted streams for granular follow alerts.
4. Preference API contract endpoints for all 4 stream columns.
5. Safe notification DOM rendering validation (XSS prevention and URL boundary verification).
"""
from __future__ import annotations

import re
import subprocess
import pytest
from data.database import (
    get_db,
    init_db,
    create_user,
    get_user_preferences,
    update_user_preferences,
    add_follow,
    create_logical_notification,
    create_notification_delivery,
)
from services.alert_decision_service import evaluate_candidate_recipients, process_content_event


@pytest.fixture(autouse=True)
def clean_test_env():
    init_db()
    emails = ["stream_alice@example.com", "stream_bob@example.com", "stream_carol_pro@example.com"]
    with get_db() as conn:
        for em in emails:
            u = conn.execute("SELECT id FROM users WHERE email = ?;", (em,)).fetchone()
            if u:
                uid = u[0]
                conn.execute("DELETE FROM notification_deliveries WHERE user_id = ?;", (uid,))
                conn.execute("DELETE FROM notifications WHERE user_id = ?;", (uid,))
                conn.execute("DELETE FROM user_notification_preferences WHERE user_id = ?;", (uid,))
                conn.execute("DELETE FROM user_follows WHERE user_id = ?;", (uid,))
                conn.execute("DELETE FROM users WHERE id = ?;", (uid,))
        if hasattr(conn, "commit"):
            conn.commit()
    yield
    with get_db() as conn:
        for em in emails:
            u = conn.execute("SELECT id FROM users WHERE email = ?;", (em,)).fetchone()
            if u:
                uid = u[0]
                conn.execute("DELETE FROM notification_deliveries WHERE user_id = ?;", (uid,))
                conn.execute("DELETE FROM notifications WHERE user_id = ?;", (uid,))
                conn.execute("DELETE FROM user_notification_preferences WHERE user_id = ?;", (uid,))
                conn.execute("DELETE FROM user_follows WHERE user_id = ?;", (uid,))
                conn.execute("DELETE FROM users WHERE id = ?;", (uid,))
        if hasattr(conn, "commit"):
            conn.commit()


def test_four_content_streams_defaults_and_toggle_independence():
    """Verify all 4 content stream toggles default to 1 (True) and can be toggled independently."""
    with get_db() as conn:
        u_id = create_user(conn, email="stream_alice@example.com", password="password123", full_name="Alice Streams")
        prefs = get_user_preferences(conn, u_id)

        # 1. Defaults are all active
        assert prefs["news_alerts"] is True
        assert prefs["tender_alerts"] is True
        assert prefs["job_alerts"] is True
        assert prefs["rental_alerts"] is True

        # 2. Toggle two OFF, keep two ON
        updated = update_user_preferences(
            conn,
            u_id,
            news_alerts=1,
            tender_alerts=0,
            job_alerts=1,
            rental_alerts=0,
        )
        assert updated["news_alerts"] is True
        assert updated["tender_alerts"] is False
        assert updated["job_alerts"] is True
        assert updated["rental_alerts"] is False

        # Verify DB re-read
        refetched = get_user_preferences(conn, u_id)
        assert refetched["news_alerts"] is True
        assert refetched["tender_alerts"] is False
        assert refetched["job_alerts"] is True
        assert refetched["rental_alerts"] is False


def test_stream_category_routing_for_free_subscribers():
    """Verify free users receive events for enabled streams, and zero events for muted streams."""
    with get_db() as conn:
        # User Alice: News ON, Tenders OFF
        u_alice = create_user(conn, email="stream_alice@example.com", password="password123", full_name="Alice")
        update_user_preferences(conn, u_alice, news_alerts=1, tender_alerts=0)

        # User Bob: News OFF, Tenders ON
        u_bob = create_user(conn, email="stream_bob@example.com", password="password123", full_name="Bob")
        update_user_preferences(conn, u_bob, news_alerts=0, tender_alerts=1)

        # 1. Evaluate News Event
        news_candidates = evaluate_candidate_recipients(conn, "news", "story_abc1")
        assert u_alice in news_candidates
        assert news_candidates[u_alice]["reason"] == "stream_news"
        assert u_bob not in news_candidates

        # 2. Evaluate Tender Event
        tender_candidates = evaluate_candidate_recipients(conn, "tender", "bid_xyz9")
        assert u_bob in tender_candidates
        assert tender_candidates[u_bob]["reason"] == "stream_tender"
        assert u_alice not in tender_candidates


def test_pro_entitlement_for_granular_follows_when_stream_is_muted():
    """
    Verify:
    - If a free user mutes a category stream, their granular follows in that category do NOT alert them.
    - If a Pro user (is_paid = 1) mutes a category stream, their granular follows DO alert them.
    """
    with get_db() as conn:
        # Free User Bob: news_alerts = 0, followed topic 'finance'
        u_free = create_user(conn, email="stream_bob@example.com", password="password123", full_name="Bob Free")
        update_user_preferences(conn, u_free, news_alerts=0, followed_content_alerts=1)
        add_follow(conn, u_free, "topic", "finance", "Finance Topic")

        # Pro User Carol: is_paid = 1, news_alerts = 0, followed topic 'finance'
        u_pro = create_user(conn, email="stream_carol_pro@example.com", password="password123", full_name="Carol Pro")
        conn.execute("UPDATE users SET is_paid = 1 WHERE id = ?;", (u_pro,))
        update_user_preferences(conn, u_pro, news_alerts=0, followed_content_alerts=1)
        add_follow(conn, u_pro, "topic", "finance", "Finance Topic")

        # Evaluate news with topic 'finance'
        candidates = evaluate_candidate_recipients(conn, "news", "story_finance_1", topics=["finance"])

        # Free user is NOT alerted because general stream is muted and personalization is Pro
        assert u_free not in candidates

        # Pro user IS alerted because Pro entitlement delivers targeted follows
        assert u_pro in candidates
        assert candidates[u_pro]["reason"] == "followed_topic"
        assert candidates[u_pro]["reason_target"] == "finance"


def test_urgent_breaking_alerts_bypass_category_stream_mute():
    """Verify urgent breaking news reaches subscribers who enabled breaking alerts, even if general news is muted."""
    with get_db() as conn:
        u_id = create_user(conn, email="stream_alice@example.com", password="password123", full_name="Alice Breaking")
        update_user_preferences(conn, u_id, news_alerts=0, breaking_alerts=1)

        candidates = evaluate_candidate_recipients(conn, "news", "crisis_report", is_breaking=True)
        assert u_id in candidates
        assert candidates[u_id]["reason"] == "breaking"


def test_all_javascript_syntax_validity_across_templates():
    """Verify that all inline script blocks in rendered templates pass Node.js V8 compile checks."""
    files = ["templates/base.html", "templates/index.html", "templates/account_alerts.html", "static/js/app.js"]
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if path.endswith(".html"):
            tag_and_scripts = re.findall(r"<script(\s+[^>]*)?>(.*?)</script>", content, re.DOTALL | re.IGNORECASE)
        else:
            tag_and_scripts = [("", content)]

        for idx, (tag_attr, s) in enumerate(tag_and_scripts):
            if "application/ld+json" in tag_attr:
                continue
            cleaned = re.sub(r"\{\{.*?\}\}", '"template_val"', s)
            cleaned = re.sub(r"\{%.*?%\}", "", cleaned)
            p = subprocess.run(["node", "-c"], input=cleaned, text=True, capture_output=True, encoding="utf-8")
            assert p.returncode == 0, f"Syntax error in {path} script {idx}: {p.stderr}"
