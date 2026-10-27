"""
Unit & Integration Tests for hooks85 Gateway Authentication, SSO & Subscriptions.
Tests essentials/v1 contract compliance, login, registration, and fallback.
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ["TELEGRAM_BOT_TOKEN"] = ""

from fastapi.testclient import TestClient
from main import app
from services.hooks85_service import (
    login_via_hooks85,
    register_khulaasaa_manifest,
    register_via_hooks85,
    verify_hooks85_session,
)

client = TestClient(app)


class TestHooks85GatewayIntegration(unittest.TestCase):

    @patch("urllib.request.urlopen")
    def test_khulaasaa_manifest_registration(self, mock_urlopen):
        """Verify Khulaasaa app manifest registers cleanly with hooks85 Gateway."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp
        res = register_khulaasaa_manifest()
        self.assertTrue(res, "Manifest should register successfully with hooks85 Gateway")

    def test_anonymous_session_returns_none(self):
        """Verify verify_hooks85_session returns None for empty/invalid sessions."""
        self.assertIsNone(verify_hooks85_session(""))
        self.assertIsNone(verify_hooks85_session("invalid-dummy-cookie"))

    @patch("urllib.request.urlopen")
    def test_login_via_hooks85_invalid_credentials(self, mock_urlopen):
        """Verify login_via_hooks85 returns error status for bad credentials."""
        import urllib.error
        import io
        err = urllib.error.HTTPError("http://localhost:8101", 401, "Unauthorized", {}, io.BytesIO(b'{"detail":"Invalid credentials"}'))
        mock_urlopen.side_effect = err
        res = login_via_hooks85("nobody_test@example.mv", "badpassword999")
        self.assertIsNotNone(res)
        self.assertEqual(res.get("status"), "error")
        self.assertEqual(res.get("code"), 401)

    def test_api_login_fallback_to_local_when_hooks85_rejects(self):
        """Verify /api/auth/login falls back seamlessly to local SQLite accounts."""
        # 1. Register a user locally
        reg_payload = {
            "email": "local_fallback_user@example.mv",
            "password": "localpassword123",
            "full_name": "Local User",
        }
        res_reg = client.post("/api/auth/register", json=reg_payload)
        self.assertEqual(res_reg.status_code, 200)

        # 2. Login with that local user
        login_payload = {
            "email": "local_fallback_user@example.mv",
            "password": "localpassword123",
        }
        res_login = client.post("/api/auth/login", json=login_payload)
        self.assertEqual(res_login.status_code, 200)
        self.assertEqual(res_login.json()["status"], "ok")
        self.assertEqual(res_login.json()["user"]["email"], "local_fallback_user@example.mv")

    def test_hooks85_session_cookie_grants_access(self):
        """Verify that a valid hooks85 session cookie authenticates via get_current_user."""
        mock_user = {
            "id": "h85-mock-uuid-1234",
            "email": "sso_executive@hooks85.com",
            "full_name": "SSO Executive",
            "is_paid": 1,
            "tenant_id": "tenant-abc",
            "tenant_plan": "business",
        }
        with patch("core.deps.verify_hooks85_session", return_value=mock_user):
            res = client.get("/api/auth/me", cookies={"hooks85_session": "mock-h85-jwt-session"})
            self.assertEqual(res.status_code, 200)
            user_data = res.json().get("user")
            self.assertIsNotNone(user_data)
            self.assertEqual(user_data["email"], "sso_executive@hooks85.com")
            self.assertEqual(user_data["is_paid"], 1)


if __name__ == "__main__":
    unittest.main()
