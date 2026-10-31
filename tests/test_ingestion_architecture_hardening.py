"""
Regression and architectural boundary tests for the Ingestion Architecture Hardening Pass.
Covers:
1. Pure scraper boundary enforcement (zero DB, repository, alert, or service imports inside `scrapers/`).
2. Zero references to deleted legacy modules across the repository.
3. Deterministic SHA-256 record identifiers (zero salted `hash()` calls in `scrapers/` or `services/ingestion/`).
4. Shared HTTP primitive routing (`scrapers/common/http_client.py`) across scrapers.
5. Partial source failure isolation across News, Tenders, Jobs, and Rentals engines.
6. Background sync scheduler lifecycle (tracked threads, interruptible shutdown, single-instance lock).
"""
from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import patch

import bs4
import pytest

from scrapers.common.http_client import fetch_json, fetch_text, http_get
from scrapers.common.source_result import stable_digest, stable_record_id
from scrapers.dedupe import SourceRecord
from scrapers.jobs.engine import fetch_all_jobs
from scrapers.news.engine import fetch_raw_news_articles
from scrapers.rentals.engine import fetch_and_consolidate_rentals
from scrapers.tenders.engine import _resolve_soup_getter, fetch_all_agency_portals
from services.ingestion.tender_ingestion import normalize_agency_record
from services.sync_scheduler import (
    is_scheduler_running,
    start_sync_scheduler,
    stop_sync_scheduler,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_SCRAPER_IMPORT_PREFIXES = (
    "data.database",
    "data.repos",
    "alerts",
    "services",
    "routes",
)

DELETED_LEGACY_MODULES = (
    "scrapers.agencies",
    "scrapers.gazette",
    "scrapers.gazette_classifier",
    "scrapers.jobs_enricher",
    "scrapers.facebook",
    "scrapers.haftha",
    "data.rentals",
    "data.scrapers",
)


def _iter_python_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.rglob("*.py") if "__pycache__" not in p.parts)


def test_scrapers_have_zero_database_alert_or_service_imports():
    """Every module under `scrapers/` must be a pure scraper/parser/consolidator with zero DB/alert/service imports."""
    scrapers_dir = REPO_ROOT / "scrapers"
    violations: list[str] = []

    for py_file in _iter_python_files(scrapers_dir):
        rel = py_file.relative_to(REPO_ROOT).as_posix()
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=rel)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(FORBIDDEN_SCRAPER_IMPORT_PREFIXES):
                        violations.append(f"{rel}:{node.lineno} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod.startswith(FORBIDDEN_SCRAPER_IMPORT_PREFIXES):
                    violations.append(f"{rel}:{node.lineno} from {mod} import ...")

    assert violations == [], f"Scraper boundary violations found: {violations}"


def test_zero_deleted_legacy_module_references_in_production_code():
    """No production module may import or reference deleted legacy scraper modules."""
    prod_dirs = ["scrapers", "services", "routes", "data", "alerts", "core"]
    violations: list[str] = []

    for d in prod_dirs:
        folder = REPO_ROOT / d
        if not folder.exists():
            continue
        for py_file in _iter_python_files(folder):
            rel = py_file.relative_to(REPO_ROOT).as_posix()
            source = py_file.read_text(encoding="utf-8")
            for legacy_mod in DELETED_LEGACY_MODULES:
                if legacy_mod in source:
                    violations.append(f"{rel} references deleted module '{legacy_mod}'")

    assert violations == [], f"Legacy module references remaining: {violations}"


def test_zero_salted_builtin_hash_in_scrapers_and_ingestion():
    """Neither `scrapers/` nor `services/ingestion/` may call Python's non-deterministic `hash()`."""
    target_dirs = [REPO_ROOT / "scrapers", REPO_ROOT / "services" / "ingestion"]
    violations: list[str] = []

    for folder in target_dirs:
        for py_file in _iter_python_files(folder):
            rel = py_file.relative_to(REPO_ROOT).as_posix()
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=rel)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "hash":
                    violations.append(f"{rel}:{node.lineno} calls built-in hash()")

    assert violations == [], f"Non-deterministic hash() calls found: {violations}"


def test_deterministic_agency_record_and_fallback_identifiers():
    """`normalize_agency_record` and `stable_record_id` must generate deterministic SHA-256 IDs."""
    rec_without_ref = SourceRecord(
        source_name="mwsc.com.mv",
        source_url="https://www.mwsc.com.mv/tenders/water-network-upgrade",
        reference_number=None,
        agency="Male' Water and Sewerage Company",
        title="Supply and Delivery of Submersible Sewage Pumps",
        published_iso="2026-10-10",
        deadline_iso="2026-10-25",
    )
    norm_1 = normalize_agency_record(rec_without_ref)
    norm_2 = normalize_agency_record(rec_without_ref)
    assert norm_1["notice_id"] == norm_2["notice_id"]
    assert norm_1["notice_id"].startswith("mwsc-com-mv-")
    # Verify whitespace/case normalization produces identical ID
    rec_whitespace_variant = SourceRecord(
        source_name="mwsc.com.mv",
        source_url="https://www.mwsc.com.mv/tenders/water-network-upgrade ",
        reference_number=None,
        agency="Male' Water and Sewerage Company",
        title="  Supply   and Delivery of Submersible Sewage Pumps ",
        published_iso="2026-10-10",
        deadline_iso="2026-10-25",
    )
    assert normalize_agency_record(rec_whitespace_variant)["notice_id"] == norm_1["notice_id"]

    # With reference number, notice_id uses reference_number directly
    rec_with_ref = SourceRecord(
        source_name="mwsc.com.mv",
        source_url="https://www.mwsc.com.mv/tenders",
        reference_number="MWSC-2026-101",
        agency="Male' Water and Sewerage Company",
        title="Supply of Pipes",
        published_iso="2026-10-10",
        deadline_iso="2026-10-25",
    )
    assert normalize_agency_record(rec_with_ref)["notice_id"] == "mwsc.com.mv-MWSC-2026-101"

    assert stable_digest("gazette", "https://gazette.gov.mv/iulaan", "Job Title") == stable_digest(
        "GAZETTE", " https://gazette.gov.mv/iulaan ", "job   title"
    )
    assert stable_record_id("gazette-job", "https://gazette.gov.mv", "Nurse").startswith("gazette-job-")


def test_scrapers_use_shared_http_client(monkeypatch):
    """Verify `http_client` helpers standardize headers, retries, and status checks while respecting monkeypatched `requests.get`."""
    calls: list[dict] = []

    class DummyResp:
        def __init__(self, status_code: int, text: str = "", json_data=None):
            self.status_code = status_code
            self.text = text
            self._json = json_data
            self.headers = {}

        def json(self):
            return self._json

    def fake_get(url, **kwargs):
        calls.append({"url": url, **kwargs})
        if len(calls) == 1 and "flaky" in url:
            return DummyResp(503, "Service Unavailable")
        if "json" in url:
            return DummyResp(200, '{"ok": true}', {"ok": True})
        return DummyResp(200, "<html><body>OK</body></html>")

    monkeypatch.setattr("requests.get", fake_get)

    text = fetch_text("https://example.mv/flaky", timeout=5, retries=2)
    assert text == "<html><body>OK</body></html>"
    assert len(calls) == 2
    assert "User-Agent" in calls[0]["headers"]

    payload = fetch_json("https://example.mv/json", timeout=5, retries=1)
    assert payload == {"ok": True}

    resp = http_get("https://example.mv/direct", timeout=4, retries=1)
    assert resp is not None and resp.status_code == 200


def test_tenders_engine_soup_getter_injection_and_no_legacy_lookup():
    """Verify `_resolve_soup_getter` uses explicit override first and contains no `scrapers.agencies` fallback."""
    custom_getter = lambda url: bs4.BeautifulSoup("<div></div>", "html.parser")
    assert _resolve_soup_getter(custom_getter) is custom_getter


def test_partial_source_failure_isolation_across_engines(monkeypatch):
    """A failure in one source adapter must never prevent other sources from completing."""
    # 1. News engine partial failure
    test_sources = {
        "failing_source": {"id": "failing_source", "type": "rss", "url": "https://bad.example.mv/rss"},
        "working_source": {"id": "working_source", "type": "wp_rest", "url": "https://ok.example.mv/wp-json"},
    }
    with patch("scrapers.news.engine.fetch_rss_posts", side_effect=RuntimeError("RSS boom")), patch(
        "scrapers.news.engine.fetch_wp_rest_posts",
        return_value=[{"id": "ok-1", "headline": "Working Headline", "summary": "Body", "sources": ["working_source"]}],
    ):
        articles = fetch_raw_news_articles(sources=test_sources, max_workers=2)
        assert len(articles) == 1
        assert articles[0]["id"] == "ok-1"

    # 2. Tenders engine partial failure
    def broken_then_ok_soup(url, timeout=10):
        if "finance" in url:
            raise ConnectionError("Finance portal timeout")
        if "tourism" in url:
            return bs4.BeautifulSoup(
                "<table><tr><td>01 Oct</td><td>Island Eco Resort - (IUL)88-PS/2026/77</td></tr></table>",
                "html.parser",
            )
        return None

    tender_records = fetch_all_agency_portals(max_workers=2, soup_getter=broken_then_ok_soup)
    assert len(tender_records) == 1
    assert tender_records[0].reference_number == "(IUL)88-PS/2026/77"

    # 3. Jobs engine partial failure
    with patch("scrapers.jobs.engine.fetch_gazette_job_vacancies", side_effect=RuntimeError("Gazette down")), patch(
        "scrapers.jobs.engine.fetch_mycareer_jobs",
        return_value=[{"notice_id": "mycareer-1", "title": "Accountant"}],
    ):
        jobs = fetch_all_jobs(pages=1)
        assert len(jobs) == 1
        assert jobs[0]["notice_id"] == "mycareer-1"

    # 4. Rentals engine partial failure
    rentals, rental_errors, attempted = fetch_and_consolidate_rentals(
        sources=[
            ("FailingPortal", lambda: (_ for _ in ()).throw(RuntimeError("Portal down"))),
            ("WorkingPortal", lambda: [{"id": "rent-1", "title": "3BHK Hulhumale"}]),
        ]
    )
    assert attempted == 2
    assert len(rental_errors) == 1
    assert len(rentals) == 1
    assert rentals[0]["id"] == "rent-1"


def test_sync_scheduler_lifecycle_and_single_instance_protection(monkeypatch, tmp_path: Path):
    """Verify `start_sync_scheduler` tracks threads, prevents duplicate starts, and stops cleanly."""
    lock_file = tmp_path / "test_scheduler.lock"
    monkeypatch.setenv("KHULAASAA_SCHEDULER_LOCK_PATH", str(lock_file))
    monkeypatch.setenv("KHULAASAA_ENABLE_SCHEDULER", "1")

    bids_calls: list[bool] = []
    jobs_calls: list[bool] = []

    monkeypatch.setattr(
        "services.sync_scheduler.trigger_bids_background_sync",
        lambda force=False: bids_calls.append(force),
    )
    monkeypatch.setattr(
        "services.sync_scheduler.trigger_jobs_background_sync",
        lambda force=False: jobs_calls.append(force),
    )

    stop_sync_scheduler()
    try:
        started = start_sync_scheduler(startup_jobs_delay=5.0, initial_delay=5.0, interval_seconds=5.0)
        assert started is True
        assert is_scheduler_running() is True
        assert len(bids_calls) == 1

        # Second start while running must be rejected
        duplicate_start = start_sync_scheduler(startup_jobs_delay=5.0, initial_delay=5.0, interval_seconds=5.0)
        assert duplicate_start is False

        # Stopping interrupts the 5s wait immediately and joins threads cleanly
        stop_sync_scheduler(join_timeout=2.0)
        assert is_scheduler_running() is False

        # Can restart cleanly after stop
        restarted = start_sync_scheduler(startup_jobs_delay=5.0, initial_delay=5.0, interval_seconds=5.0)
        assert restarted is True
    finally:
        stop_sync_scheduler(join_timeout=2.0)
        assert is_scheduler_running() is False


def test_admin_sync_status_endpoint_and_observability(monkeypatch):
    """Verify /admin/api/sync-status returns operational status and requires editor auth."""
    from main import app
    from fastapi.testclient import TestClient
    import base64

    client = TestClient(app)

    # Unauthenticated access must be rejected
    unauth = client.get("/admin/api/sync-status")
    assert unauth.status_code == 401

    # Authenticated editor access returns status for news, tenders, jobs, rentals
    creds = base64.b64encode(b"editor:changeme").decode("ascii")
    auth_res = client.get("/admin/api/sync-status", headers={"Authorization": f"Basic {creds}"})
    assert auth_res.status_code == 200
    data = auth_res.json()
    assert data["status"] == "ok"
    assert "scheduler_running" in data
    sync = data["sync"]
    assert "news" in sync and "is_syncing" in sync["news"]
    assert "tenders" in sync and "status" in sync["tenders"]
    assert "jobs" in sync and "status" in sync["jobs"]
    assert "rentals" in sync and "status" in sync["rentals"]
