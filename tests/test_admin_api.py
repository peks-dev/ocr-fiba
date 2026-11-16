from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from ocr_engine_api.main import create_app
from ocr_engine_api.routes.admin import require_supabase_user

PROD_ENV = {
    "OCR_ENV": "production",
    "OCR_ENGINE_API_KEY": "secret",
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_SERVICE_KEY": "service-role-key",
    "SUPABASE_JWT_SECRET": "jwt-secret-at-least-32-chars!!",
}

ADMIN = {"id": "admin-acct", "email": "admin@example.com", "role": "admin", "status": "active"}
TESTER = {"id": "tester-acct", "email": "tester@example.com", "role": "tester", "status": "active", "assigned_demo": "player"}


class AdminApiKeysTest(unittest.TestCase):
    def test_non_admin_is_forbidden(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {**PROD_ENV, "OCR_RUNS_DIR": tmp}
            with patch.dict("os.environ", env, clear=True):
                with patch(
                    "ocr_engine_api.routes.admin.get_account_by_supabase_user_id",
                    return_value=TESTER,
                ):
                    app = create_app()
                    app.dependency_overrides[require_supabase_user] = lambda: {"sub": "user-tester"}
                    client = TestClient(app)
                    response = client.get("/v1/admin/accounts", headers={"Authorization": "Bearer eyJhbGciOiJ.payload.sig"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"]["error"]["code"], "FORBIDDEN")

    def test_unauthenticated_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {**PROD_ENV, "OCR_RUNS_DIR": tmp}
            with patch.dict("os.environ", env, clear=True):
                client = TestClient(create_app())
                response = client.get("/v1/admin/accounts")
        self.assertEqual(response.status_code, 401)

    def test_admin_can_list_accounts_and_manage_keys(self) -> None:
        stored = []

        def fake_store(account_id, key_hash, key_prefix, name="default"):
            stored.append({"account_id": account_id, "name": name, "key_prefix": key_prefix})
            return {"id": "key-1", "account_id": account_id, "name": name, "key_prefix": key_prefix}

        with tempfile.TemporaryDirectory() as tmp:
            env = {**PROD_ENV, "OCR_RUNS_DIR": tmp}
            with patch.dict("os.environ", env, clear=True):
                with patch("ocr_engine_api.routes.admin.list_accounts", return_value=[ADMIN, TESTER]):
                    with patch("ocr_engine_api.routes.admin.get_account_by_id", return_value=TESTER):
                        with patch("ocr_engine_api.routes.admin.list_api_keys", return_value=[]):
                            with patch("ocr_engine_api.routes.admin.store_api_key", side_effect=fake_store):
                                with patch(
                                    "ocr_engine_api.routes.admin.delete_api_key_record",
                                    return_value={"id": "key-1"},
                                ):
                                    with patch(
                                        "ocr_engine_api.routes.admin.get_account_by_supabase_user_id",
                                        return_value=ADMIN,
                                    ):
                                        app = create_app()
                                        app.dependency_overrides[require_supabase_user] = lambda: {"sub": "user-admin"}
                                        client = TestClient(app)
                                        headers = {"Authorization": "Bearer eyJhbGciOiJ.payload.sig"}
                                        listed = client.get("/v1/admin/accounts", headers=headers)
                                        created = client.post(
                                            "/v1/admin/accounts/tester-acct/api-keys",
                                            params={"name": "agentic-os"},
                                            headers=headers,
                                        )
                                        keys = client.get("/v1/admin/accounts/tester-acct/api-keys", headers=headers)
                                        deleted = client.delete(
                                            "/v1/admin/accounts/tester-acct/api-keys/key-1",
                                            headers=headers,
                                        )
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["accounts"]), 2)
        self.assertEqual(created.status_code, 200)
        self.assertTrue(created.json()["key"].startswith("ocr_live_"))
        self.assertEqual(created.json()["name"], "agentic-os")
        self.assertEqual(keys.status_code, 200)
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json()["status"], "deleted")
        self.assertEqual(stored[0]["account_id"], "tester-acct")

    def test_admin_create_key_unknown_account_is_404(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {**PROD_ENV, "OCR_RUNS_DIR": tmp}
            with patch.dict("os.environ", env, clear=True):
                with patch("ocr_engine_api.routes.admin.get_account_by_id", return_value=None):
                    with patch(
                        "ocr_engine_api.routes.admin.get_account_by_supabase_user_id",
                        return_value=ADMIN,
                    ):
                        app = create_app()
                        app.dependency_overrides[require_supabase_user] = lambda: {"sub": "user-admin"}
                        client = TestClient(app)
                        response = client.post(
                            "/v1/admin/accounts/missing/api-keys",
                            headers={"Authorization": "Bearer eyJhbGciOiJ.payload.sig"},
                        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"]["error"]["code"], "ACCOUNT_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
