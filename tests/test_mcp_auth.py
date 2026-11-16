from __future__ import annotations

import asyncio
import time
import unittest
from unittest.mock import MagicMock, patch

from ocr_engine_mcp.auth import (
    OCR_LIVE_PREFIX,
    McpTokenVerifier,
    api_key_for_request,
    auth_from_env,
    probe_ocr_api_key,
)
from ocr_engine_mcp.client import OcrApiError


class McpTokenVerifierTest(unittest.TestCase):
    def test_static_token_is_accepted_without_probing(self) -> None:
        probe = MagicMock(return_value=False)
        verifier = McpTokenVerifier(static_token="static-secret", probe=probe)
        token = asyncio.run(verifier.verify_token("static-secret"))
        self.assertIsNotNone(token)
        self.assertEqual(token.client_id, "ocr-mcp-static")
        self.assertEqual(token.token, "static-secret")
        probe.assert_not_called()

    def test_static_token_rejects_different_value(self) -> None:
        verifier = McpTokenVerifier(static_token="static-secret", probe=lambda _: False)
        self.assertIsNone(asyncio.run(verifier.verify_token("other-secret")))
        self.assertIsNone(asyncio.run(verifier.verify_token("")))

    def test_ocr_live_key_is_accepted_when_probe_succeeds(self) -> None:
        key = OCR_LIVE_PREFIX + "abc"
        probe = MagicMock(return_value=True)
        verifier = McpTokenVerifier(static_token="static-secret", probe=probe)
        token = asyncio.run(verifier.verify_token(key))
        self.assertIsNotNone(token)
        self.assertEqual(token.client_id, "ocr-live-client")
        self.assertEqual(token.token, key)
        self.assertEqual(token.claims["source"], "ocr_live")
        probe.assert_called_once_with(key)

    def test_ocr_live_key_is_rejected_when_probe_fails(self) -> None:
        verifier = McpTokenVerifier(static_token="static-secret", probe=lambda _: False)
        self.assertIsNone(asyncio.run(verifier.verify_token(OCR_LIVE_PREFIX + "nope")))

    def test_arbitrary_tokens_are_rejected(self) -> None:
        probe = MagicMock(return_value=True)
        verifier = McpTokenVerifier(static_token="static-secret", probe=probe)
        self.assertIsNone(asyncio.run(verifier.verify_token("totally-random-token")))
        probe.assert_not_called()

    def test_valid_live_key_is_cached(self) -> None:
        probe = MagicMock(return_value=True)
        verifier = McpTokenVerifier(static_token="static-secret", probe=probe, cache_ttl_seconds=60)
        key = OCR_LIVE_PREFIX + "cached"
        asyncio.run(verifier.verify_token(key))
        asyncio.run(verifier.verify_token(key))
        probe.assert_called_once_with(key)

    def test_cache_expires(self) -> None:
        probe = MagicMock(return_value=True)
        verifier = McpTokenVerifier(static_token="static-secret", probe=probe, cache_ttl_seconds=1)
        key = OCR_LIVE_PREFIX + "expired"
        cache_key = __import__("hashlib").sha256(key.encode()).hexdigest()
        verifier._cache[cache_key] = (True, time.monotonic() - 2)
        asyncio.run(verifier.verify_token(key))
        probe.assert_called_once_with(key)

    def test_probe_exceptions_fail_closed_and_are_not_cached(self) -> None:
        probe = MagicMock(side_effect=RuntimeError("api down"))
        verifier = McpTokenVerifier(static_token="static-secret", probe=probe, cache_ttl_seconds=60)
        key = OCR_LIVE_PREFIX + "down"
        self.assertIsNone(asyncio.run(verifier.verify_token(key)))
        self.assertIsNone(asyncio.run(verifier.verify_token(key)))
        self.assertEqual(probe.call_count, 2)

    def test_empty_token_is_rejected(self) -> None:
        verifier = McpTokenVerifier(static_token="static-secret", probe=lambda _: True)
        self.assertIsNone(asyncio.run(verifier.verify_token("")))


class ProbeOcrApiKeyTest(unittest.TestCase):
    def test_success_is_valid(self) -> None:
        with patch("ocr_engine_mcp.auth.OcrApiClient") as client_cls:
            client_cls.return_value.list_runs.return_value = {"runs": []}
            self.assertTrue(probe_ocr_api_key("ocr_live_ok", base_url="http://api.test"))
            client_cls.return_value.list_runs.assert_called_once_with(limit=1)

    def test_rate_limited_is_valid(self) -> None:
        with patch("ocr_engine_mcp.auth.OcrApiClient") as client_cls:
            client_cls.return_value.list_runs.side_effect = OcrApiError(429, "RATE_LIMITED", "slow down")
            self.assertTrue(probe_ocr_api_key("ocr_live_ok"))

    def test_unauthorized_is_invalid(self) -> None:
        with patch("ocr_engine_mcp.auth.OcrApiClient") as client_cls:
            client_cls.return_value.list_runs.side_effect = OcrApiError(401, "UNAUTHORIZED", "nope")
            self.assertFalse(probe_ocr_api_key("ocr_live_bad"))

    def test_server_error_is_raised(self) -> None:
        with patch("ocr_engine_mcp.auth.OcrApiClient") as client_cls:
            client_cls.return_value.list_runs.side_effect = OcrApiError(502, "HTTP_502", "bad gateway")
            with self.assertRaises(OcrApiError):
                probe_ocr_api_key("ocr_live_ok")


class ApiKeyForRequestTest(unittest.TestCase):
    def test_forwards_ocr_live_access_token(self) -> None:
        access = MagicMock(token="ocr_live_client-key")
        with patch("ocr_engine_mcp.auth.get_access_token", return_value=access):
            with patch.dict("os.environ", {"OCR_API_KEY": "env-key", "MCP_AUTH_TOKEN": "static"}, clear=False):
                self.assertEqual(api_key_for_request(), "ocr_live_client-key")

    def test_static_access_token_uses_env_api_key(self) -> None:
        access = MagicMock(token="static-token")
        with patch("ocr_engine_mcp.auth.get_access_token", return_value=access):
            with patch.dict("os.environ", {"OCR_API_KEY": "env-key", "MCP_AUTH_TOKEN": "static-token"}, clear=False):
                self.assertEqual(api_key_for_request(), "env-key")

    def test_falls_back_to_env_without_access_token(self) -> None:
        with patch("ocr_engine_mcp.auth.get_access_token", return_value=None):
            with patch.dict("os.environ", {"OCR_API_KEY": "env-key"}, clear=True):
                self.assertEqual(api_key_for_request(), "env-key")


class AuthFromEnvTest(unittest.TestCase):
    def test_disabled_outside_production_without_static_token(self) -> None:
        with patch.dict("os.environ", {"OCR_ENV": "development"}, clear=True):
            self.assertIsNone(auth_from_env())

    def test_enabled_when_static_token_set(self) -> None:
        with patch.dict("os.environ", {"OCR_ENV": "development", "MCP_AUTH_TOKEN": "static"}, clear=True):
            verifier = auth_from_env()
            self.assertIsInstance(verifier, McpTokenVerifier)
            self.assertEqual(verifier.static_token, "static")

    def test_disabled_in_production_without_static_token(self) -> None:
        with patch.dict("os.environ", {"OCR_ENV": "production"}, clear=True):
            self.assertIsNone(auth_from_env())


if __name__ == "__main__":
    unittest.main()
