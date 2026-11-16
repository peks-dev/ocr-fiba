from __future__ import annotations

import time
import unittest
from unittest.mock import MagicMock, patch

import jwt

from ocr_engine_api.api_keys import (
    generate_api_key,
    hash_api_key,
    update_last_used_at,
    KEY_PREFIX,
)
from ocr_engine_api.auth_api_key import (
    _cache_get,
    _cache_set,
    is_api_key_request,
    validate_api_key,
    _cache,
)
from ocr_engine_api.auth_supabase import verify_supabase_jwt


class GenerateApiKeyTest(unittest.TestCase):
    def test_generate_produces_ocr_live_prefix(self) -> None:
        raw, key_hash, prefix = generate_api_key()
        self.assertTrue(raw.startswith(KEY_PREFIX))
        self.assertTrue(prefix.startswith(KEY_PREFIX))

    def test_hash_is_deterministic(self) -> None:
        raw, key_hash, _ = generate_api_key()
        self.assertEqual(hash_api_key(raw), key_hash)

    def test_hash_is_sha256_64_hex_chars(self) -> None:
        _, key_hash, _ = generate_api_key()
        self.assertEqual(len(key_hash), 64)
        self.assertRegex(key_hash, r"^[0-9a-f]{64}$")

    def test_different_calls_produce_different_keys(self) -> None:
        raw1, _, _ = generate_api_key()
        raw2, _, _ = generate_api_key()
        self.assertNotEqual(raw1, raw2)


class VerifySupabaseJwtTest(unittest.TestCase):
    SECRET = "test-jwt-secret-at-least-32-chars!!"

    def _make_token(self, payload: dict, secret: str | None = None) -> str:
        return jwt.encode(payload, secret or self.SECRET, algorithm="HS256")

    @patch("ocr_engine_api.auth_supabase.get_api_settings")
    def test_valid_jwt_passes(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value = MagicMock(
            has_supabase=True,
            supabase_jwt_secret=self.SECRET,
        )
        token = self._make_token({
            "sub": "user-123",
            "email": "test@example.com",
            "iat": int(time.time()) - 10,
            "exp": int(time.time()) + 3600,
        })
        payload = verify_supabase_jwt(token)
        self.assertEqual(payload["sub"], "user-123")

    @patch("ocr_engine_api.auth_supabase.get_api_settings")
    def test_expired_jwt_is_rejected(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value = MagicMock(
            has_supabase=True,
            supabase_jwt_secret=self.SECRET,
        )
        token = self._make_token({
            "sub": "user-123",
            "iat": int(time.time()) - 7200,
            "exp": int(time.time()) - 3600,
        })
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as exc:
            verify_supabase_jwt(token)
        self.assertEqual(exc.exception.status_code, 401)

    @patch("ocr_engine_api.auth_supabase.get_api_settings")
    def test_wrong_secret_is_rejected(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value = MagicMock(
            has_supabase=True,
            supabase_jwt_secret=self.SECRET,
        )
        token = self._make_token(
            {
                "sub": "user-123",
                "iat": int(time.time()) - 10,
                "exp": int(time.time()) + 3600,
            },
            secret="wrong-secret-xxxxxxxxxxxxxxxxxxxxxx",
        )
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as exc:
            verify_supabase_jwt(token)
        self.assertEqual(exc.exception.status_code, 401)

    @patch("ocr_engine_api.auth_supabase.get_api_settings")
    def test_missing_sub_is_rejected(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value = MagicMock(
            has_supabase=True,
            supabase_jwt_secret=self.SECRET,
        )
        token = self._make_token({
            "iat": int(time.time()) - 10,
            "exp": int(time.time()) + 3600,
        })
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as exc:
            verify_supabase_jwt(token)
        self.assertEqual(exc.exception.status_code, 401)


class ApiKeyCacheTest(unittest.TestCase):
    def setUp(self) -> None:
        _cache.clear()

    def test_cache_set_and_get(self) -> None:
        _cache_set("hash1", "account1", "active")
        result = _cache_get("hash1")
        self.assertIsNotNone(result)
        self.assertEqual(result, ("account1", "active"))

    def test_cache_miss_returns_none(self) -> None:
        result = _cache_get("nonexistent")
        self.assertIsNone(result)

    def test_cache_entry_expires(self) -> None:
        _cache["hash2"] = ("account2", "active", time.monotonic() - 61)
        result = _cache_get("hash2")
        self.assertIsNone(result)
        self.assertNotIn("hash2", _cache)

    def test_revoked_key_in_cache_is_rejected(self) -> None:
        _cache_set("hash3", "account3", "revoked")
        result = _cache_get("hash3")
        self.assertIsNotNone(result)
        self.assertEqual(result, ("account3", "revoked"))


class IsApiKeyRequestTest(unittest.TestCase):
    def test_ocr_live_bearer_is_detected(self) -> None:
        request = MagicMock()
        request.headers = {"authorization": "Bearer ocr_live_abc123"}
        self.assertTrue(is_api_key_request(request))

    def test_other_bearer_is_not_detected(self) -> None:
        request = MagicMock()
        request.headers = {"authorization": "Bearer some-jwt-token"}
        self.assertFalse(is_api_key_request(request))

    def test_no_auth_header_is_not_detected(self) -> None:
        request = MagicMock()
        request.headers = {}
        self.assertFalse(is_api_key_request(request))


class UpdateLastUsedAtTest(unittest.TestCase):
    def test_update_sends_timezone_aware_iso_timestamp(self) -> None:
        client = MagicMock()
        table = client.table.return_value
        update = table.update.return_value
        eq = update.eq.return_value

        with patch("ocr_engine_api.api_keys.get_supabase_client", return_value=client):
            update_last_used_at("key-123")

        client.table.assert_called_once_with("api_keys")
        payload = table.update.call_args.args[0]
        self.assertIn("last_used_at", payload)
        self.assertTrue(payload["last_used_at"].endswith("+00:00") or payload["last_used_at"].endswith("Z"))
        update.eq.assert_called_once_with("id", "key-123")
        eq.execute.assert_called_once()

    def test_generated_key_hex_length_is_64(self) -> None:
        raw, _, _ = generate_api_key()
        suffix = raw.removeprefix(KEY_PREFIX)
        self.assertEqual(len(suffix), 64)
        self.assertRegex(suffix, r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
