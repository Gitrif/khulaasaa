import unittest
from fastapi.testclient import TestClient

from data.database import get_db, save_company_profile, get_company_profile
from main import app


class TestEstimatorAndInternationalRegistry(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_construction_estimator_routes(self):
        """Verify /calculator and /tools/construction-estimator return 200 with calculators."""
        res1 = self.client.get("/calculator")
        self.assertEqual(res1.status_code, 200)
        self.assertIn("Maldivian Construction &amp; BOQ Material Estimator", res1.text)
        self.assertIn("Sonee Hardware", res1.text)
        self.assertIn("STO", res1.text)
        self.assertIn("hooks85", res1.text)

        res2 = self.client.get("/tools/construction-estimator")
        self.assertEqual(res2.status_code, 200)
        self.assertIn("Concrete Volume &amp; Mix Breakdown", res2.text)
        self.assertIn("calculateConcrete", res2.text)

    def test_company_profile_builder_route(self):
        """Verify /company-profile renders with MED and International bidder options."""
        res = self.client.get("/company-profile")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Maldivian Company (MED)", res.text)
        self.assertIn("International / Foreign Bidder", res.text)
        self.assertIn("cpLocalAgentName", res.text)
        self.assertIn("cpCountry", res.text)

    def test_international_contractor_profile_storage(self):
        """Test saving and retrieving an international contractor profile with local agent."""
        intl_data = {
            "company_name": "SingaTech Marine Engineering Pte Ltd",
            "entity_type": "international",
            "country_of_origin": "Singapore",
            "foreign_reg_no": "UEN-202100889K",
            "foreign_tax_id": "GST-SG-889900",
            "local_agent_name": "Maldives Marine Logistics Pvt Ltd",
            "local_agent_reg": "C-09872019",
            "local_agent_phone": "+960 779 4433",
            "local_agent_email": "agent@marinelogistics.mv",
            "registered_address": "8 Marina View, Asia Square Tower 1, Singapore 018960",
            "phone": "+65 6789 0123",
            "email": "tenders@singatech.sg",
            "website": "www.singatech.sg",
            "managing_director_name": "Tan Wei Ming",
            "managing_director_message": "Committed to delivering world-class coastal engineering in the Maldives.",
            "directors": [
                {"name": "Tan Wei Ming", "role": "Managing Director", "nid": "S8012345Z"}
            ],
            "core_business": [
                {"title": "Coastal Dredging & Reclamation", "desc": "Specialized deep-water island engineering."}
            ]
        }

        with get_db() as conn:
            profile_id = save_company_profile(conn, intl_data)
            self.assertGreater(profile_id, 0)

            retrieved = get_company_profile(conn, profile_id=profile_id)
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved["company_name"], "SingaTech Marine Engineering Pte Ltd")
            self.assertEqual(retrieved["entity_type"], "international")
            self.assertEqual(retrieved["country_of_origin"], "Singapore")
            self.assertEqual(retrieved["foreign_reg_no"], "UEN-202100889K")
            self.assertEqual(retrieved["local_agent_name"], "Maldives Marine Logistics Pvt Ltd")
            self.assertEqual(retrieved["local_agent_reg"], "C-09872019")


if __name__ == "__main__":
    unittest.main()
