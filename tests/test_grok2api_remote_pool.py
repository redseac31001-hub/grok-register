import unittest
from unittest.mock import patch

import grok_register_ttk as app


class DummyResponse:
    def __init__(self, payload=None, status_code=200, reason=""):
        self._payload = payload or {}
        self.status_code = status_code
        self.reason = reason
        self.text = ""

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP Error {self.status_code}: {self.reason}")

    def json(self):
        return self._payload


class Grok2ApiRemotePoolTests(unittest.TestCase):
    def setUp(self):
        self.original_config = app.config.copy()

    def tearDown(self):
        app.config = self.original_config

    def test_remote_pool_falls_back_to_admin_api_prefix_when_root_tokens_add_is_404(self):
        app.config.update({
            "grok2api_remote_base": "https://grok.example.com",
            "grok2api_remote_app_key": "app-secret",
            "grok2api_pool_name": "ssoBasic",
        })
        calls = []

        def fake_post(url, **kwargs):
            calls.append((url, kwargs))
            if url == "https://grok.example.com/tokens/add":
                return DummyResponse(status_code=404)
            return DummyResponse({"status": "success", "count": 1})

        with patch.object(app, "http_post", side_effect=fake_post):
            ok = app.add_token_to_grok2api_remote_pool("sso=abc123", email="a@example.com")

        self.assertTrue(ok)
        self.assertEqual([url for url, _ in calls], [
            "https://grok.example.com/tokens/add",
            "https://grok.example.com/admin/api/tokens/add",
        ])
        self.assertEqual(calls[-1][1]["params"], {"app_key": "app-secret"})
        self.assertEqual(calls[-1][1]["json"], {
            "tokens": ["abc123"],
            "pool": "basic",
            "tags": ["auto-register"],
        })

    def test_remote_pool_does_not_duplicate_admin_api_prefix_when_base_already_points_to_admin_api(self):
        app.config.update({
            "grok2api_remote_base": "https://grok.example.com/admin/api",
            "grok2api_remote_app_key": "app-secret",
            "grok2api_pool_name": "ssoSuper",
        })
        calls = []

        def fake_post(url, **kwargs):
            calls.append((url, kwargs))
            return DummyResponse({"status": "success", "count": 1})

        with patch.object(app, "http_post", side_effect=fake_post):
            ok = app.add_token_to_grok2api_remote_pool("sso=super123", email="a@example.com")

        self.assertTrue(ok)
        self.assertEqual([url for url, _ in calls], [
            "https://grok.example.com/admin/api/tokens/add",
        ])
        self.assertEqual(calls[0][1]["json"]["pool"], "super")


if __name__ == "__main__":
    unittest.main()
