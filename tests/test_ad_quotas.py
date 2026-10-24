import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["TELEGRAM_BOT_TOKEN"] = ""

from main import app
from data.database import (
    get_db,
    upsert_sponsored_ad,
    get_active_sponsored_ad,
    record_ad_impression,
    list_sponsored_ads,
    extend_sponsored_ad,
    delete_sponsored_ad,
)

client = TestClient(app)

class TestAdQuotasAndDuration(unittest.TestCase):

    def setUp(self):
        with get_db() as conn:
            conn.execute("DELETE FROM sponsored_ads WHERE campaign_name LIKE 'test-%';")
            conn.commit()

    def tearDown(self):
        with get_db() as conn:
            conn.execute("DELETE FROM sponsored_ads WHERE campaign_name LIKE 'test-%';")
            conn.commit()

    def test_impression_quota_limit(self):
        with get_db() as conn:
            ad_id = upsert_sponsored_ad(
                conn,
                {
                    "campaign_name": "test-quota-ad",
                    "sponsor_name": "Test Sponsor",
                    "text_html": "Test creative",
                    "target_category": "bids",
                    "is_active": 1,
                    "max_impressions": 3,
                },
            )
            # 0 impressions: should serve
            active = get_active_sponsored_ad(conn, target_category="bids")
            self.assertIsNotNone(active)

            # Record 3 impressions
            record_ad_impression(conn, ad_id)
            record_ad_impression(conn, ad_id)
            record_ad_impression(conn, ad_id)

            # Now quota is reached (3/3): should NOT serve
            rows = conn.execute("SELECT impressions, max_impressions FROM sponsored_ads WHERE id = ?;", (ad_id,)).fetchone()
            self.assertEqual(rows[0], 3)
            self.assertEqual(rows[1], 3)

            # Check status evaluation
            all_ads = list_sponsored_ads(conn)
            test_ad = next(a for a in all_ads if a["id"] == ad_id)
            self.assertTrue(test_ad["is_quota_filled"])
            self.assertFalse(test_ad["is_serving"])
            self.assertEqual(test_ad["status_label"], "Quota Reached")

    def test_time_duration_expiration(self):
        with get_db() as conn:
            # 1. Active ad expiring in future (30 days)
            future_ts = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
            ad_id_future = upsert_sponsored_ad(
                conn,
                {
                    "campaign_name": "test-future-ad",
                    "sponsor_name": "Future Sponsor",
                    "text_html": "Test future creative",
                    "target_category": "news",
                    "is_active": 1,
                    "expires_at": future_ts,
                },
            )

            # 2. Expired ad (ended yesterday)
            past_ts = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            ad_id_past = upsert_sponsored_ad(
                conn,
                {
                    "campaign_name": "test-past-ad",
                    "sponsor_name": "Past Sponsor",
                    "text_html": "Test past creative",
                    "target_category": "news",
                    "is_active": 1,
                    "expires_at": past_ts,
                },
            )

            all_ads = list_sponsored_ads(conn)
            future_ad = next(a for a in all_ads if a["id"] == ad_id_future)
            past_ad = next(a for a in all_ads if a["id"] == ad_id_past)

            self.assertFalse(future_ad["is_expired"])
            self.assertTrue(future_ad["is_serving"])
            self.assertGreaterEqual(future_ad["days_remaining"], 29)

            self.assertTrue(past_ad["is_expired"])
            self.assertFalse(past_ad["is_serving"])
            self.assertEqual(past_ad["status_label"], "Expired")

    def test_extend_sponsored_ad_topup(self):
        with get_db() as conn:
            ad_id = upsert_sponsored_ad(
                conn,
                {
                    "campaign_name": "test-renew-ad",
                    "sponsor_name": "Renew Sponsor",
                    "text_html": "Renewal test",
                    "is_active": 1,
                    "max_impressions": 1000,
                },
            )
            # Fake 1000 impressions
            conn.execute("UPDATE sponsored_ads SET impressions = 1000 WHERE id = ?;", (ad_id,))
            conn.commit()

            # Extend by +1,000 views
            extend_sponsored_ad(conn, ad_id, add_impressions=1000, add_days=30)

            updated = list_sponsored_ads(conn)
            ad = next(a for a in updated if a["id"] == ad_id)
            self.assertEqual(ad["max_impressions"], 2000)
            self.assertEqual(ad["impressions"], 1000)
            self.assertTrue(ad["is_serving"])
            self.assertIsNotNone(ad["expires_at"])

if __name__ == "__main__":
    unittest.main()
