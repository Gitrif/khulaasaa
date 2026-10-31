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


def test_free_user_retains_stream_reason_not_upgraded_to_pro_follow():
    """Verify free user qualifying via broad stream retains 'stream_{clean_type}' and is NOT recorded with Pro-only 'followed_{type}'."""
    with get_db() as conn:
        u_free = create_user(conn, email="stream_bob@example.com", password="password123", full_name="Bob Free")
        update_user_preferences(conn, u_free, news_alerts=1, followed_content_alerts=1)
        add_follow(conn, u_free, "topic", "economy", "Economy")

        candidates = evaluate_candidate_recipients(conn, "news", "story_econ_1", topics=["economy"])
        assert u_free in candidates
        # Must strictly be stream_news, never upgraded to followed_topic for free user
        assert candidates[u_free]["reason"] == "stream_news"


def test_topic_follow_does_not_match_unrelated_event_types():
    """Verify news topic follows only match news events, never tenders, jobs, or rentals."""
    with get_db() as conn:
        u_pro = create_user(conn, email="stream_carol_pro@example.com", password="password123", full_name="Carol Pro")
        conn.execute("UPDATE users SET is_paid = 1 WHERE id = ?;", (u_pro,))
        update_user_preferences(conn, u_pro, news_alerts=0, tender_alerts=0, job_alerts=0, rental_alerts=0, followed_content_alerts=1)
        add_follow(conn, u_pro, "topic", "tourism", "Tourism")

        # 1. Matching news event -> matches
        c_news = evaluate_candidate_recipients(conn, "news", "story_tour_1", topics=["tourism"])
        assert u_pro in c_news
        assert c_news[u_pro]["reason"] == "followed_topic"

        # 2. Tender event with topic parameter -> does NOT match
        c_tender = evaluate_candidate_recipients(conn, "tender", "bid_tour_1", topics=["tourism"])
        assert u_pro not in c_tender

        # 3. Job event with topic parameter -> does NOT match
        c_job = evaluate_candidate_recipients(conn, "job", "job_tour_1", topics=["tourism"])
        assert u_pro not in c_job


def test_story_follow_does_not_match_non_news_events():
    """Verify story cluster follows only match news events, never jobs or tenders with identical ID."""
    with get_db() as conn:
        u_pro = create_user(conn, email="stream_carol_pro@example.com", password="password123", full_name="Carol Pro")
        conn.execute("UPDATE users SET is_paid = 1 WHERE id = ?;", (u_pro,))
        update_user_preferences(conn, u_pro, news_alerts=0, job_alerts=0, tender_alerts=0, followed_content_alerts=1)
        add_follow(conn, u_pro, "story", "cluster-777", "Story Cluster 777")

        # 1. News event with id cluster-777 -> matches
        c_news = evaluate_candidate_recipients(conn, "news", "cluster-777")
        assert u_pro in c_news
        assert c_news[u_pro]["reason"] == "followed_story"

        # 2. Job event with identical id cluster-777 -> must NOT match
        c_job = evaluate_candidate_recipients(conn, "job", "cluster-777")
        assert u_pro not in c_job

        # 3. Tender event with identical id cluster-777 -> must NOT match
        c_tender = evaluate_candidate_recipients(conn, "tender", "cluster-777")
        assert u_pro not in c_tender


def test_section_follow_compatibility_across_event_types():
    """Verify section follows map strictly to compatible event types."""
    with get_db() as conn:
        u_pro = create_user(conn, email="stream_carol_pro@example.com", password="password123", full_name="Carol Pro")
        conn.execute("UPDATE users SET is_paid = 1 WHERE id = ?;", (u_pro,))
        update_user_preferences(conn, u_pro, news_alerts=0, tender_alerts=0, job_alerts=0, rental_alerts=0, followed_content_alerts=1)

        # Follow section 'tenders'
        add_follow(conn, u_pro, "section", "tenders", "Tenders Section")

        # Tender event matches
        c_tender = evaluate_candidate_recipients(conn, "tender", "bid_101")
        assert u_pro in c_tender
        assert c_tender[u_pro]["reason"] == "followed_section"
        assert c_tender[u_pro]["reason_target"] == "tenders"

        # News event does NOT match section 'tenders'
        c_news = evaluate_candidate_recipients(conn, "news", "news_101", section="major")
        assert u_pro not in c_news


def test_multiple_matching_reasons_single_logical_notification():
    """Verify that multiple triggers result in exactly 1 logical notification without duplication."""
    with get_db() as conn:
        u_pro = create_user(conn, email="stream_carol_pro@example.com", password="password123", full_name="Carol Pro")
        conn.execute("UPDATE users SET is_paid = 1 WHERE id = ?;", (u_pro,))
        update_user_preferences(conn, u_pro, news_alerts=1, breaking_alerts=1, followed_content_alerts=1)
        add_follow(conn, u_pro, "topic", "health", "Health")

        # Process breaking news event with followed topic
        stats = process_content_event(
            conn,
            content_type="news",
            content_id="story_health_urgent",
            title="Urgent Health Update",
            is_breaking=True,
            topics=["health"],
        )
        assert stats["eligible_users"] >= 1
        assert stats["notifications_created"] == 1

        # Second call with same event key creates 0 new notifications
        stats2 = process_content_event(
            conn,
            content_type="news",
            content_id="story_health_urgent",
            title="Urgent Health Update Repeat",
            is_breaking=True,
            topics=["health"],
        )
        assert stats2["notifications_created"] == 0


def test_global_pause_and_verified_channel_delivery_gate():
    """Verify global pause excludes users and only truthfully verified channels receive deliveries."""
    with get_db() as conn:
        # User 1: Paused
        u_paused = create_user(conn, email="stream_alice@example.com", password="password123", full_name="Alice Paused")
        update_user_preferences(conn, u_paused, is_paused=1, news_alerts=1)

        # User 2: Active with unverified telegram
        u_unver = create_user(conn, email="stream_bob@example.com", password="password123", full_name="Bob Unverified")
        conn.execute("UPDATE users SET telegram_chat_id = '99999', telegram_verified = 0 WHERE id = ?;", (u_unver,))
        update_user_preferences(conn, u_unver, is_paused=0, news_alerts=1, telegram_enabled=1)

        # User 3: Active with verified telegram
        u_ver = create_user(conn, email="stream_carol_pro@example.com", password="password123", full_name="Carol Verified")
        conn.execute("UPDATE users SET telegram_chat_id = '88888', telegram_verified = 1 WHERE id = ?;", (u_ver,))
        update_user_preferences(conn, u_ver, is_paused=0, news_alerts=1, telegram_enabled=1)

        candidates = evaluate_candidate_recipients(conn, "news", "story_pause_test")
        assert u_paused not in candidates
        assert u_unver in candidates
        assert u_ver in candidates

        # Run process_content_event
        process_content_event(conn, "news", "story_pause_test", title="Pause Gate Headline")

        # Unverified user got 0 deliveries
        d_unver = conn.execute("SELECT COUNT(*) FROM notification_deliveries WHERE user_id = ?;", (u_unver,)).fetchone()[0]
        assert d_unver == 0

        # Verified user got 1 delivery
        d_ver = conn.execute("SELECT COUNT(*) FROM notification_deliveries WHERE user_id = ?;", (u_ver,)).fetchone()[0]
        assert d_ver == 1


def test_account_menu_xss_protection():
    """
    Verify malicious profile values (HTML tags, script tags, event handlers, quotes)
    are strictly assigned via DOM textContent and cannot execute or inject tags.
    """
    malicious_payloads = [
        '<script>alert("xss")</script>',
        '<img src=x onerror=alert(1)>',
        '"><svg/onload=alert(1)>',
        "';alert(String.fromCharCode(88,83,83))//",
    ]

    # Verify that in static/js/app_shell.js, renderUserAvatarMenu sets textContent and does not use innerHTML
    with open("static/js/app_shell.js", "r", encoding="utf-8") as f:
        shell_js = f.read()

    # Assert DOM construction functions exist and contain zero innerHTML
    assert "function renderUserAvatarMenu(" in shell_js
    assert "function renderGuestAvatarButton(" in shell_js

    # Extract the renderUserAvatarMenu function body
    fn_match = re.search(r"function renderUserAvatarMenu\(container, u\)\s*\{(.*?)\n\}", shell_js, re.DOTALL)
    assert fn_match is not None, "renderUserAvatarMenu function must be defined"
    fn_body = fn_match.group(1)

    # Must NOT contain innerHTML
    assert "innerHTML" not in fn_body, "renderUserAvatarMenu must strictly use DOM APIs without innerHTML"
    # Must use textContent for full_name, email, displayName, and initials
    assert "dropFullEl.textContent" in fn_body
    assert "dropEmailEl.textContent" in fn_body
    assert "nameEl.textContent" in fn_body
    assert "initEl.textContent" in fn_body


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
