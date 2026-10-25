import os
import sys
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

# Ensure root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["TELEGRAM_BOT_TOKEN"] = ""

from main import app
from data.database import get_db, list_hooks85_subscriptions, list_sponsored_ads

client = TestClient(app)

class TestHooks85AdsAndSubscription(unittest.TestCase):

    def test_sponsored_ads_in_db_are_hooks85(self):
        with get_db() as conn:
            ads = list_sponsored_ads(conn)
            self.assertGreater(len(ads), 0, "Should have sponsored ads configured")
            for ad in ads:
                if ad.get("is_active"):
                    self.assertIn("hooks85", (ad.get("campaign_name", "") + ad.get("sponsor_name", "")).lower())

    @patch("routers.web_ui.trigger_bids_background_sync")
    def test_homepage_renders_hooks85_ad(self, mock_sync):
        res = client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("hooks85", res.text)
        self.assertNotIn("Dhiraagu &mdash; Ultra-fast", res.text)

    @patch("routers.web_ui.trigger_bids_background_sync")
    def test_bids_page_renders_hooks85_ad_and_no_duplicate_header_ad(self, mock_sync):
        res = client.get("/bids?source=mock")
        self.assertEqual(res.status_code, 200)
        self.assertIn("hooks85", res.text)
        # Check that Prepare Bid workspace links to hooks85 subscription
        with get_db() as conn:
            row = conn.execute("SELECT notice_id FROM bids LIMIT 1;").fetchone()
            notice_id = row[0] if row else "166396"
        prep = client.get(f"/bids/prepare?notice_id={notice_id}")
        self.assertIn("/subscription?plan=tender_erp", prep.text)

    def test_jobs_page_renders_hooks85_ad(self):
        res = client.get("/jobs")
        self.assertEqual(res.status_code, 200)
        self.assertIn("hooks85", res.text)

    def test_subscription_page_get(self):
        res = client.get("/subscription")
        self.assertEqual(res.status_code, 200)
        self.assertIn("hooks85 POS &amp; Business ERP", res.text)
        self.assertIn("Cloud Point of Sale (POS)", res.text)
        self.assertIn("Tender &amp; Contractor ERP", res.text)
        self.assertIn("MIRA GST", res.text)
        self.assertIn("MVR 1,299", res.text)

    def test_hooks85_alias_get(self):
        res = client.get("/hooks85")
        self.assertEqual(res.status_code, 200)
        self.assertIn("hooks85 POS &amp; Business ERP", res.text)

    def test_subscription_page_with_notice_id(self):
        with get_db() as conn:
            row = conn.execute("SELECT notice_id FROM bids LIMIT 1;").fetchone()
            notice_id = row[0] if row else "166396"

        res = client.get(f"/subscription?plan=tender_erp&notice_id={notice_id}")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Tender Fast-Track Preparation", res.text)

    def test_subscription_inquire_post(self):
        form_data = {
            "company_name": "Test Alimas Builders Pvt Ltd",
            "contact_name": "Ahmed Rasheed",
            "phone": "9607999888",
            "email": "ahmed@alimas.mv",
            "island_atoll": "K. Male",
            "plan_tier": "tender_erp",
            "modules": ["pos_checkout", "tender_boq", "mira_invoicing"],
            "notice_id": "418724",
            "notes": "Looking for BOQ pricing and POS checkouts.",
        }
        res = client.post("/subscription/inquire", data=form_data, follow_redirects=False)
        self.assertEqual(res.status_code, 303)
        self.assertIn("/subscription?msg=", res.headers["location"])

        # Check DB entry
        with get_db() as conn:
            subs = list_hooks85_subscriptions(conn)
            matched = [s for s in subs if s.get("phone") == "9607999888"]
            self.assertGreater(len(matched), 0)
            sub = matched[0]
            self.assertEqual(sub["company_name"], "Test Alimas Builders Pvt Ltd")
            self.assertEqual(sub["plan_tier"], "tender_erp")
            self.assertIn("tender_boq", sub["interested_modules"])

    def test_advertise_page_and_footer_links(self):
        res = client.get("/advertise")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Advertise on Khulaasaa MV", res.text)
        self.assertIn("advertise@khulaasaa.tech", res.text)
        self.assertIn("Header Leaderboard Banner", res.text)
        self.assertIn("In-Feed Native Sponsor Card", res.text)

        # Check footer links on home page
        home = client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn('href="/advertise"', home.text)
        self.assertIn('href="/about"', home.text)
        self.assertIn('href="/compliance"', home.text)
        self.assertIn('href="/compliance#legality"', home.text)
        self.assertIn('href="/compliance#removal"', home.text)
        self.assertIn('href="/about#standards"', home.text)
        self.assertIn('href="/jobs/cv"', home.text)
        self.assertIn('href="/feed.xml"', home.text)
        self.assertIn('editorial@khulaasaa.tech', home.text)
        # Check that hooks85 links in footer and ads open in new window
        self.assertIn('href="/subscription" target="_blank" rel="noopener noreferrer"', home.text)
        self.assertIn('target="_blank" rel="noopener noreferrer"', home.text)

    def test_all_footer_destination_pages_return_200(self):
        destinations = [
            "/",
            "/bids",
            "/jobs",
            "/jobs/cv",
            "/feed.xml",
            "/advertise",
            "/about",
            "/compliance",
            "/subscription",
            "/hooks85",
        ]
        for dest in destinations:
            res = client.get(dest)
            self.assertEqual(res.status_code, 200, f"Expected 200 for destination: {dest}")


if __name__ == "__main__":
    unittest.main()
