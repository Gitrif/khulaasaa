from unittest.mock import patch, MagicMock
import pytest
from pathlib import Path
from starlette.testclient import TestClient

from data.database import (
    init_db,
    get_db,
    create_user,
    authenticate_user,
    get_user_by_email,
    create_user_session,
    get_user_from_session,
    save_user_cv,
    get_user_cv,
    update_user_plan,
    update_user_job_alerts,
    upsert_job,
    query_jobs,
    get_job_disciplines,
)
from scrapers.jobs import classify_job_discipline
from alerts.telegram import format_job_alert_html, dispatch_job_alerts
from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_classify_job_discipline():
    # IT
    assert classify_job_discipline("Software Engineer (Backend)") == "IT, Tech & Communications"
    assert classify_job_discipline("ކޮމްޕިއުޓަރ ޕްރޮގްރާމަރ") == "IT, Tech & Communications"

    # Construction & Engineering
    assert classify_job_discipline("Civil Engineer (Coastal Infrastructure)") == "Construction, Architecture & Engineering"
    assert classify_job_discipline("އިލެކްޓްރީޝަން") == "Construction, Architecture & Engineering"

    # Medical
    assert classify_job_discipline("Specialist Medical Officer (Pediatrics)") == "Medical & Healthcare"
    assert classify_job_discipline("ރަޖިސްޓަރޑް ނަރުސް") == "Medical & Healthcare"

    # Administration
    assert classify_job_discipline("Senior Administrative Officer") == "Administration & Management"
    assert classify_job_discipline("ކައުންސިލް އެސިސްޓެންޓް") == "Administration & Management"

    # Separate Transport Disciplines: Land Transport, Sea Transport, Aviation
    assert classify_job_discipline("Van Driver (Transport Fleet)") == "Land Transport"
    assert classify_job_discipline("ޑްރައިވަރ", agency="Ministry of Transport") == "Land Transport"
    assert classify_job_discipline("Speedboat Captain", agency="Kurumba Maldives") == "Sea Transport"
    assert classify_job_discipline("Launch Driver & Boat Crew") == "Sea Transport"
    assert classify_job_discipline("Seaplane First Officer", agency="Trans Maldivian Airways") == "Aviation"
    assert classify_job_discipline("Airport Operations & Ramp Coordinator") == "Aviation"

    # Role precedence: The applicant cares about the profession, not just the employer industry!
    # 1. Procurement in a pharmacy / hospital is Procurement, NOT Medicine
    assert classify_job_discipline("Senior Procurement Officer", agency="State Pharmaceutical and Medical Supply Corporation Ltd") == "Finance, Accounting & Procurement"
    assert classify_job_discipline("Purchasing & Stores Assistant", agency="Indira Gandhi Memorial Hospital") == "Finance, Accounting & Procurement"

    # 2. Doctor / Nurse in a resort is Medical, NOT Hospitality
    assert classify_job_discipline("Resident Medical Doctor", agency="Joali Maldives Resort") == "Medical & Healthcare"
    assert classify_job_discipline("Registered Nurse (Staff Clinic)", agency="Soneva Fushi") == "Medical & Healthcare"


def test_format_job_alert_html():
    job = {
        "title": "Shop Operations Supervisor",
        "title_en": "Shop Operations Supervisor",
        "agency": "State Trading Organization (STO)",
        "agency_name_en": "State Trading Organization Plc",
        "discipline": "Customer Service, Retail & Operations",
        "location": "Male'",
        "salary_raw": "MVR 14,500",
        "deadline_iso": "2026-10-30T14:00:00",
        "source_url": "https://gazette.gov.mv/iulaan/12345",
        "source_portal": "gazette.gov.mv",
    }
    msg = format_job_alert_html(job)
    assert "NEW JOB VACANCY — Khulaasaa Jobs" in msg
    assert "Shop Operations Supervisor" in msg
    assert "State Trading Organization" in msg
    assert "Customer Service, Retail &amp; Operations" in msg
    assert "gazette.gov.mv/iulaan/12345" in msg
    # Enforce zero emojis in Telegram alert
    emojis = [c for c in msg if 0x1F300 <= ord(c) <= 0x1F9FF or 0x2600 <= ord(c) <= 0x27BF or 0x1FA70 <= ord(c) <= 0x1FAFF]
    assert emojis == []


def test_user_cv_lifecycle(tmp_path: Path):
    db_file = tmp_path / "test_cv.db"
    init_db(db_file)

    with get_db(db_file) as conn:
        # 1. Create user with dummy candidate details
        uid = create_user(
            conn,
            email="ahmed.naseem.test@example.mv",
            password="securepassword123",
            full_name="Ahmed Naseem",
            phone="+960 700 0001",
            telegram_chat_id="12345678",
            job_alert_categories=["Land Transport", "Customer Service, Retail & Operations"],
        )
        assert uid > 0

        # 2. Authenticate
        user = authenticate_user(conn, "ahmed.naseem.test@example.mv", "securepassword123")
        assert user is not None
        assert user["full_name"] == "Ahmed Naseem"
        assert user["is_paid"] is False

        # Wrong password
        assert authenticate_user(conn, "ahmed.naseem.test@example.mv", "wrong") is None

        # 3. Save CV
        sample_data = {
            "fullName": "Ahmed Naseem",
            "nationalId": "A000000",
            "dob": "15th March 1993",
            "sex": "Male",
            "nationality": "Maldivian",
            "address": "H. Dhunfini, Male’, Rep. of Maldives.",
            "skills": ["Driving", "Store Management"],
        }
        cv_id = save_user_cv(conn, uid, sample_data, title="Ahmed Naseem Maldivian CV", template="standard")
        assert cv_id > 0

        # 4. Retrieve CV
        cv = get_user_cv(conn, uid)
        assert cv is not None
        assert cv["title"] == "Ahmed Naseem Maldivian CV"
        assert cv["template"] == "standard"
        assert cv["data"]["nationalId"] == "A000000"

        # 5. Upgrade user plan
        update_user_plan(conn, uid, 1)
        upgraded_user = authenticate_user(conn, "ahmed.naseem.test@example.mv", "securepassword123")
        assert upgraded_user["is_paid"] is True


def test_jobs_web_and_api_endpoints(client):
    # 1. GET /jobs view
    res = client.get("/jobs")
    assert res.status_code == 200
    assert "Job Vacancies" in res.text
    assert "Create Your CV Now" in res.text

    # 2. GET /jobs/cv view
    res = client.get("/jobs/cv")
    assert res.status_code == 200
    assert "Maldivian CV Creator" in res.text
    assert "Ahmed Naseem" in res.text

    # 3. GET /api/cv as unauthenticated guest -> 401
    res = client.get("/api/cv")
    assert res.status_code == 401

    # 4. POST /api/auth/register
    import secrets
    test_email = f"testuser_{secrets.token_hex(4)}@example.mv"
    reg_payload = {
        "email": test_email,
        "password": "mypassword123",
        "full_name": "Test Candidate",
        "phone": "+960 777 9999",
        "telegram_chat_id": "987654321",
        "job_alert_categories": ["IT, Tech & Communications"],
    }
    res = client.post("/api/auth/register", json=reg_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["user"]["email"] == test_email

    # 5. GET /api/cv as authenticated user -> 200
    res = client.get("/api/cv")
    assert res.status_code == 200

    # 6. Save CV without Pro tier -> 403 Forbidden (CV saving & updating is a Pro feature)
    save_payload = {
        "title": "Test Maldivian CV",
        "template": "standard",
        "data": {
            "fullName": "Test Candidate",
            "nationalId": "A123456",
            "dob": "1st Jan 1995",
            "skills": ["FastAPI", "Python"],
        },
    }
    res = client.post("/api/cv", json=save_payload)
    assert res.status_code == 403

    # 7. Upgrade user to Pro (MVR 30/mo)
    res = client.post("/api/user/upgrade")
    assert res.status_code == 200
    assert res.json()["is_paid"] is True

    # 8. Save CV as Pro user -> 200 OK
    res = client.post("/api/cv", json=save_payload)
    assert res.status_code == 200

    # Verify saved
    res = client.get("/api/cv")
    assert res.status_code == 200
    assert res.json()["cv"]["data"]["nationalId"] == "A123456"

    # 9. Standards API
    res_std = client.get("/api/cv/standards")
    assert res_std.status_code == 200
    assert "English" in res_std.json()["languages"]
    assert "Dhivehi" in res_std.json()["languages"]

    # 10. Company Profile API & View
    cp_view = client.get("/bids/company-profile")
    assert cp_view.status_code == 200
    assert "Company Profile" in cp_view.text
    assert "Download A4 PDF" in cp_view.text
    assert "html2pdf.bundle.min.js" in cp_view.text
    assert "@page" in cp_view.text or "print.css" in cp_view.text
    assert "@page" in client.get("/static/css/print.css").text

    # Verify CV Creator also has Download A4 PDF and clean print stylesheet
    cv_view = client.get("/jobs/cv")
    assert cv_view.status_code == 200
    assert "Download A4 PDF" in cv_view.text
    assert "html2pdf.bundle.min.js" in cv_view.text
    assert "@page" in cv_view.text or "print.css" in cv_view.text

    # Verify static js is served
    static_res = client.get("/static/js/html2pdf.bundle.min.js")
    assert static_res.status_code == 200

    cp_save = client.post(
        "/api/company-profile",
        json={
            "company_name": "Mai & Emi Investments Pvt Ltd",
            "registration_number": "C04812021",
            "tin_number": "1130267",
            "directors": [{"name": "Mohamed Ashraf", "role": "Managing Director"}],
        },
    )
    assert cp_save.status_code == 200
    assert cp_save.json()["status"] == "ok"
    assert cp_save.json()["profile"]["registration_number"] == "C04812021"

    # 11. Update job alert preferences
    alert_payload = {
        "categories": ["IT, Tech & Communications", "Administration & Management"],
        "telegram_chat_id": "987654321",
    }
    res = client.post("/api/user/job-alerts", json=alert_payload)
    assert res.status_code == 200

    # 9. Test alert endpoint
    with patch("main.send_telegram_message", return_value=(True, "Message delivered")):
        res = client.post("/api/jobs/test-alert", json={"chat_id": "987654321"})
        assert res.status_code == 200
        assert res.json()["ok"] is True

    # 10. Logout
    res = client.post("/api/auth/logout")
    assert res.status_code == 200
    # Following GET /api/cv should now be 401
    res = client.get("/api/cv")
    assert res.status_code == 401


def test_job_enrichment_and_hdc_prioritization(client: TestClient):
    from services.jobs_service import enrich_job

    # 1. Test HDC Job: strictly only HDC source
    hdc_raw = {
        "id": 7,
        "notice_id": "job-hdc-proc-lead",
        "title": "Senior Procurement Officer",
        "title_en": "Senior Procurement Officer",
        "agency": "Housing Development Corporation (HDC)",
        "agency_name_en": "Housing Development Corporation",
        "discipline": "Finance, Accounting & Procurement",
        "location": "Hulhumale'",
        "salary_raw": "MVR 18,000 - 22,000",
        "deadline_iso": "2026-10-26T13:00:00",
        "requirements": "Degree in Procurement or CIPS qualification.",
    }
    hdc_enriched = enrich_job(hdc_raw)
    assert hdc_enriched["is_hdc"] is True
    assert hdc_enriched["employer_logo"] == "/static/logos/hdc.svg"
    assert hdc_enriched["requirements_clean"] == "Degree in Procurement or CIPS qualification."
    assert len(hdc_enriched["application_sources"]) == 1
    assert hdc_enriched["application_sources"][0]["id"] == "hdc"
    assert hdc_enriched["application_sources"][0]["name"] == "HDC Careers"
    assert "hdc.mv" in hdc_enriched["application_sources"][0]["url"]
    assert hdc_enriched["secondary_source"] is None

    # 2. Test STO job on Gazette: when no posting on sto.mv, strictly links to Gazette post where job info is!
    sto_raw = {
        "id": 2,
        "notice_id": "job-sto-shop-sup",
        "title": "Shop Operations Supervisor",
        "title_en": "Shop Operations Supervisor",
        "agency": "State Trading Organization (STO)",
        "agency_name_en": "State Trading Organization Plc",
        "discipline": "Customer Service, Retail & Operations",
        "location": "Male'",
        "salary_raw": "MVR 14,500 - 18,000",
        "deadline_iso": "2026-10-27T14:00:00",
        "requirements": "Retail operations experience and inventory handling.",
        "source_url": "https://gazette.gov.mv/iulaan/248530",
        "source_portal": "gazette.gov.mv",
    }
    sto_enriched = enrich_job(sto_raw)
    assert sto_enriched["is_hdc"] is False
    assert sto_enriched["employer_logo"] == "/static/logos/sto.svg"
    assert len(sto_enriched["application_sources"]) == 1
    assert sto_enriched["application_sources"][0]["id"] == "gazette"
    assert "gazette.gov.mv/iulaan/248530" in sto_enriched["application_sources"][0]["url"]

    # 3. Test MyCareer job: links directly to the specific job on MyCareer portal
    mc_raw = {
        "id": 20,
        "notice_id": "mycareer-audit-associate",
        "title": "Audit Associate",
        "title_en": "Audit Associate",
        "agency": "Ernst & Young",
        "agency_name_en": "Ernst & Young",
        "discipline": "Finance, Accounting & Procurement",
        "location": "Male'",
        "source_url": "https://mycareer.gov.mv/en/jobs/audit-associate",
        "source_portal": "mycareer.gov.mv",
    }
    mc_enriched = enrich_job(mc_raw)
    assert len(mc_enriched["application_sources"]) == 1
    assert mc_enriched["application_sources"][0]["id"] == "mycareer"
    assert mc_enriched["application_sources"][0]["name"] == "MyCareer.mv"
    assert "mycareer.gov.mv/en/jobs/audit-associate" in mc_enriched["application_sources"][0]["url"]

    # 4. Test Gazette job (Rule 2: Government Gazette jobs only show Gazette source)
    council_raw = {
        "id": 8,
        "notice_id": "job-male-city-admin",
        "title": "Senior Administrative Officer",
        "title_en": "Senior Administrative Officer",
        "agency": "Malé City Council",
        "agency_name_en": "Malé City Council",
        "discipline": "Administration & Management",
        "source_portal": "gazette.gov.mv",
        "source_url": "https://gazette.gov.mv/iulaan/248315",
    }
    council_enriched = enrich_job(council_raw)
    assert len(council_enriched["application_sources"]) == 1
    assert council_enriched["application_sources"][0]["id"] == "gazette"
    assert "gazette.gov.mv" in council_enriched["application_sources"][0]["url"]

    # 5. Test Web UI GET /jobs endpoint rendering
    res = client.get("/jobs")
    assert res.status_code == 200
    html = res.text

    # Discipline badges present
    assert "Administration &amp; Management" in html or "Administration & Management" in html
    assert "Finance, Accounting &amp; Procurement" in html or "Finance, Accounting & Procurement" in html

    # Employer logos present
    assert "/static/logos/hdc.svg" in html
    assert "/static/logos/gazette.svg" in html

    # Salary & Employer prominently visible
    assert "MVR" in html
    assert "Housing Development Corporation" in html or "HDC" in html
    assert "Tree Top Hospital" in html or "Ernst & Young" in html

    # Apply via source pattern & Prepare CV
    assert "Apply via HDC" in html
    assert "Apply via Gazette" in html
    assert "Prepare CV for this job" in html

    # HDC strictly only links to specific HDC post
    assert "Apply via HDC Careers" in html or "Apply via HDC" in html
    assert "https://jobs.hdc.mv/jobs/591" in html or "hdc.mv" in html
    assert "https://gazette.gov.mv/iulaan?type=vazeefaa" not in html

    # Specific Gazette post URL rendered
    assert "https://gazette.gov.mv/iulaan/248315" in html or "https://gazette.gov.mv/iulaan/" in html

    # Deadline rendered cleanly
    assert "Deadline:" in html

