"""
Tests for Consolidated Rentals, Tenancy Agreement, and Employer HR Portal.
Strictly under 500 lines. Zero emojis.
"""
import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["TELEGRAM_BOT_TOKEN"] = ""

from main import app
from data.connection import get_db
from data.rentals import init_rentals_schema, seed_initial_rentals, list_rentals

client = TestClient(app)

class TestRentalsAndHrPortal(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with get_db() as conn:
            init_rentals_schema(conn)
            seed_initial_rentals(conn)

    def test_rentals_page_renders_listings_and_sources(self):
        res = client.get("/rentals")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Maldivian Apartment &amp; Rental Directory", res.text)
        self.assertIn("Hulhumale Phase 1", res.text)
        self.assertIn("MVR 22,000", res.text)
        self.assertIn("Source: iBay Maldives", res.text)
        self.assertIn("Draft Tenancy Agreement", res.text)

    def test_rentals_filter_by_location_and_bedrooms(self):
        res = client.get("/rentals?location=Hulhumale+Phase+1&bedrooms=2")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Hulhumale Phase 1", res.text)
        self.assertIn("2 Bedrooms", res.text)

    def test_rental_detail_view(self):
        with get_db() as conn:
            r = list_rentals(conn, limit=1)[0]
        res = client.get(f"/rentals/{r['id']}")
        self.assertEqual(res.status_code, 200)
        self.assertIn(r["title"], res.text)
        self.assertIn("Direct Contact Details", res.text)
        self.assertIn("Hooks85 Tenancy Suite", res.text)

    def test_rental_contract_builder_view(self):
        res = client.get("/rentals/contract")
        self.assertEqual(res.status_code, 200)
        self.assertIn("RESIDENTIAL TENANCY AGREEMENT", res.text)
        self.assertIn("Standard Maldivian Lease Framework", res.text)
        self.assertIn("Monthly Rent Ledger &amp; Receipts", res.text)
        self.assertIn("Download Official Tenancy Agreement", res.text)

    def test_rental_contract_builder_with_rental_id(self):
        with get_db() as conn:
            r = list_rentals(conn, limit=1)[0]
        res = client.get(f"/rentals/contract?rental_id={r['id']}")
        self.assertEqual(res.status_code, 200)
        self.assertIn(r["address"], res.text)

    def test_save_rental_contract_api(self):
        payload = {
            "landlord_name": "Test Landlord Solih",
            "landlord_nid": "A998877",
            "landlord_phone": "7712345",
            "tenant_name": "Test Tenant Waheed",
            "tenant_nid": "A112233",
            "tenant_phone": "7987654",
            "property_address": "Flat 402, Nirolhu Magu, Hulhumale",
            "monthly_rent_mvr": 23000,
            "security_deposit_mvr": 46000,
            "lease_start_date": "2026-11-01",
            "lease_duration_months": 12,
            "utilities_clause": "Tenant pays electricity and water.",
            "status": "draft"
        }
        res = client.post("/api/rentals/contract/save", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertGreater(data["contract_id"], 0)

    def test_candidates_talent_pool_renders_with_consent(self):
        res = client.get("/jobs/candidates")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Consent-Verified Talent Pool", res.text)
        self.assertIn("Ahmed Simah", res.text)
        self.assertIn("Accounting &amp; Finance", res.text)
        self.assertIn("Consent Verified", res.text)
        self.assertIn("Invite to Apply", res.text)

    def test_candidates_filter_by_discipline(self):
        res = client.get("/jobs/candidates?discipline=Engineering")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Hassan Ziyau", res.text)
        self.assertIn("Site Civil Engineer", res.text)

    def test_employer_hr_portal_renders_shortlisting(self):
        res = client.get("/jobs/hr-portal")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Automated Candidate Shortlisting &amp; Hiring Portal", res.text)
        self.assertIn("Automated Shortlisting", res.text)
        self.assertIn("Coming Soon", res.text)
        self.assertIn("Automated Police Record Verification", res.text)
        self.assertIn("Pension Office (MRPS) &amp; Payroll Sync", res.text)

    def test_shortlist_candidate_api(self):
        payload = {"candidate_id": "c1", "candidate_name": "Ahmed Simah"}
        res = client.post("/api/jobs/shortlist", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("Ahmed Simah", data["message"])


if __name__ == "__main__":
    unittest.main()
