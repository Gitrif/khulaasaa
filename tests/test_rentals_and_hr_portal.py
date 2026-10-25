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
from data.scrapers.rentals_scraper import (
    RENTAL_SOURCES,
    COMMON_FURNISHED_ITEMS,
    extract_rooms_and_toilets,
    extract_lift_and_floors,
    detect_leased_status,
    consolidate_key,
)

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
        self.assertIn("View on iBay Maldives", res.text)
        self.assertIn("Also listed at MVR 23,500 on", res.text)
        self.assertIn("Boahiyaa", res.text)
        self.assertIn("Bedrooms", res.text)
        self.assertIn("Bathrooms", res.text)
        self.assertIn("Floor Level", res.text)
        self.assertIn("Floor Area", res.text)

    def test_rentals_filter_by_location_and_bedrooms(self):
        res = client.get("/rentals?location=Hulhumale+Phase+1&bedrooms=2")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Hulhumale Phase 1", res.text)
        self.assertIn("Bedrooms", res.text)

    def test_rentals_filter_by_lift_and_ac(self):
        res = client.get("/rentals?has_lift=1&has_ac=1")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Lift Access", res.text)
        self.assertIn("AC Installed", res.text)

    def test_rental_detail_view(self):
        with get_db() as conn:
            r = list_rentals(conn, limit=1)[0]
        res = client.get(f"/rentals/{r['id']}")
        self.assertEqual(res.status_code, 200)
        self.assertIn(r["title"], res.text)
        # Aggregated listings must have public aggregation disclaimers and source button, not dummy contacts
        if not r.get("is_direct"):
            self.assertIn("Public Aggregation", res.text)
            self.assertIn("View on", res.text)
            self.assertIn("source-action-btn", res.text)
        else:
            self.assertIn("Direct Contact Details", res.text)
        self.assertIn("Key Specifications", res.text)
        self.assertIn("Layout &amp; Climate", res.text)

    def test_rental_contract_builder_view(self):
        res = client.get("/rentals/contract")
        self.assertEqual(res.status_code, 200)
        self.assertIn("RESIDENTIAL TENANCY AGREEMENT", res.text)
        self.assertIn("Standard Maldivian Lease Framework", res.text)
        self.assertIn("Monthly Rent Ledger &amp; Receipts", res.text)
        self.assertIn("Download Official Tenancy Agreement", res.text)
        # Check English public area maintenance & deposit deficit clause
        self.assertIn("Public Area Maintenance &amp; Tenant Interior Upkeep", res.text)
        self.assertIn("stairwell, corridor, and entrance lighting", res.text)
        self.assertIn("debt owed to the Landlord", res.text)
        # Check Dhivehi contract text and public area maintenance presence
        self.assertIn("ކުއްޔަށް ދިނުމާއި ހިފުމުގެ އެއްބަސްވުން", res.text)
        self.assertIn("ކުއްޔަށްދޭ ފަރާތް", res.text)
        self.assertIn("ޢާންމު ސަރަޙައްދު ބެލެހެއްޓުމާއި އެޕާޓްމަންޓް ސާފުތާހިރުކޮށް ބެލެހެއްޓުން", res.text)
        self.assertIn("ސިޑިބަރިތަކާއި ކޮރިޑޯތަކުގެ ބޮކިތައް", res.text)
        self.assertIn("ސާބިތު ދަރަންޏެކެވެ", res.text)

    def test_rental_contract_builder_with_rental_id(self):
        with get_db() as conn:
            r = list_rentals(conn, limit=1)[0]
        res = client.get(f"/rentals/contract?rental_id={r['id']}")
        self.assertEqual(res.status_code, 200)
        addr = r.get("address") or r.get("plot_building") or "Nirolhu Magu"
        self.assertIn(addr, res.text)

    def test_save_rental_contract_api(self):
        payload = {
            "landlord_name": "Test Landlord Solih",
            "landlord_nid": "A998877",
            "landlord_phone": "7712345",
            "landlord_address": "M. Light, Male",
            "tenant_name": "Test Tenant Waheed",
            "tenant_nid": "A112233",
            "tenant_phone": "7987654",
            "tenant_address": "H. Dawn, Male",
            "property_address": "Flat 402, Nirolhu Magu, Hulhumale",
            "monthly_rent_mvr": 23000,
            "security_deposit_mvr": 46000,
            "late_fine_mvr_per_day": 150,
            "lease_duration_months": 12,
            "notice_period_days": 30,
            "contract_language": "dv",
            "inventory_items": ["Master Bed & Mattress", "Living Room Sofa Set"],
            "status": "draft"
        }
        res = client.post("/api/rentals/contract/save", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertGreater(data["contract_id"], 0)

    def test_scraper_heuristics(self):
        rooms, att, tot = extract_rooms_and_toilets("Spacious 3 room apartment with 3 attached toilets and 1 guest toilet")
        self.assertEqual(rooms, 3)
        self.assertEqual(att, 3)
        self.assertEqual(tot, 4)

        has_lift, b_floors, floor_desc = extract_lift_and_floors("Apartment on 5th floor with lift access and balcony in 10 floors building")
        self.assertEqual(has_lift, 1)
        self.assertEqual(floor_desc, "5 Floor")
        self.assertEqual(b_floors, 10)

        self.assertTrue(detect_leased_status("This property is leased out / rented"))
        self.assertFalse(detect_leased_status("Available for immediate rent"))

        key = consolidate_key("Hulhumale Phase 1", "Lot 10423", "4", 3)
        self.assertEqual(key, "hulhumale phase 1|lot 10423|4|3bhk")

        source_names = [s["name"] for s in RENTAL_SOURCES]
        self.assertEqual(len(source_names), 6)
        self.assertIn("iBay Maldives", source_names)
        self.assertIn("Boahiyaa Real Estate", source_names)
        self.assertIn("Property.mv", source_names)
        self.assertIn("Hiyaa.mv Residential", source_names)
        self.assertIn("KobaPages Maldives", source_names)
        self.assertIn("Apex Atoll Properties", source_names)

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
