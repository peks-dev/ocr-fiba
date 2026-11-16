from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from ocr_engine_api.main import create_app
from ocr_engine_api.pipeline_options import build_config, parse_options_json
from ocr_engine_api.rate_limit import RunRateLimiter, client_key, is_run_creation
from ocr_engine_api.routes.runs import create_run
from ocr_engine_api.schemas import CreateRunRequest
from ocr_engine_api.settings import get_api_settings


PROD_ENV = {"OCR_ENV": "production", "OCR_ENGINE_API_KEY": "secret"}


class PathInputTest(unittest.TestCase):
    def test_path_input_disabled_by_default_in_production(self) -> None:
        with patch.dict("os.environ", PROD_ENV, clear=True):
            self.assertFalse(get_api_settings().allow_path_input)

    def test_path_input_enabled_by_default_in_development(self) -> None:
        with patch.dict("os.environ", {"OCR_ENV": "development"}, clear=True):
            self.assertTrue(get_api_settings().allow_path_input)

    def test_path_input_can_be_reenabled_explicitly(self) -> None:
        with patch.dict("os.environ", {**PROD_ENV, "OCR_ALLOW_PATH_INPUT": "true"}, clear=True):
            self.assertTrue(get_api_settings().allow_path_input)

    def test_create_run_from_path_rejected_in_production(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "sheet.jpg"
            image.write_bytes(b"image")
            with patch.dict("os.environ", {**PROD_ENV, "OCR_RUNS_DIR": tmp}, clear=True):
                with self.assertRaises(HTTPException) as exc:
                    asyncio.run(create_run(CreateRunRequest(image_path=str(image), run_id="r1")))
            self.assertEqual(exc.exception.status_code, 403)
            self.assertEqual(exc.exception.detail["error"]["code"], "PATH_INPUT_DISABLED")
            self.assertFalse((Path(tmp) / "r1").exists())

    def test_create_run_from_path_rejected_over_http_in_production(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {**PROD_ENV, "OCR_RUNS_DIR": tmp}, clear=True):
                client = TestClient(create_app())
                response = client.post(
                    "/v1/runs",
                    json={"image_path": "/etc/passwd"},
                    headers={"Authorization": "Bearer secret"},
                )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"]["error"]["code"], "PATH_INPUT_DISABLED")


class RateLimiterTest(unittest.TestCase):
    def test_per_minute_window(self) -> None:
        now = [1000.0]
        limiter = RunRateLimiter(2, 0, clock=lambda: now[0])
        self.assertTrue(limiter.check("a")[0])
        self.assertTrue(limiter.check("a")[0])
        allowed, window, retry = limiter.check("a")
        self.assertFalse(allowed)
        self.assertEqual(window, "minute")
        self.assertGreater(retry, 0)
        self.assertTrue(limiter.check("b")[0], "buckets are per key")
        now[0] += 61
        self.assertTrue(limiter.check("a")[0])

    def test_per_day_window(self) -> None:
        now = [0.0]
        limiter = RunRateLimiter(0, 3, clock=lambda: now[0])
        for _ in range(3):
            self.assertTrue(limiter.check("a")[0])
            now[0] += 120
        allowed, window, _ = limiter.check("a")
        self.assertFalse(allowed)
        self.assertEqual(window, "day")
        now[0] += 86400
        self.assertTrue(limiter.check("a")[0])

    def test_state_file_persists_daily_count_across_restarts(self) -> None:
        now = [5000.0]
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "quota" / "state.json"
            first = RunRateLimiter(0, 2, state_file=state, clock=lambda: now[0])
            self.assertTrue(first.check("a")[0])
            self.assertTrue(first.check("a")[0])
            self.assertTrue(state.exists())
            restarted = RunRateLimiter(0, 2, state_file=state, clock=lambda: now[0])
            self.assertFalse(restarted.check("a")[0])
            now[0] += 86401
            expired = RunRateLimiter(0, 2, state_file=state, clock=lambda: now[0])
            self.assertTrue(expired.check("a")[0])

    def test_corrupt_state_file_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state.json"
            state.write_text("{not json")
            limiter = RunRateLimiter(1, 0, state_file=state)
            self.assertTrue(limiter.check("a")[0])

    def test_zero_limits_disable(self) -> None:
        limiter = RunRateLimiter(0, 0)
        self.assertFalse(limiter.enabled)
        for _ in range(100):
            self.assertTrue(limiter.check("a")[0])

    def test_client_key_hashes_token(self) -> None:
        key = client_key("Bearer supersecret", "1.2.3.4")
        self.assertTrue(key.startswith("tok:"))
        self.assertNotIn("supersecret", key)
        self.assertEqual(client_key("", "1.2.3.4"), "ip:1.2.3.4")

    def test_only_run_creation_is_limited(self) -> None:
        self.assertTrue(is_run_creation("POST", "/v1/runs"))
        self.assertTrue(is_run_creation("POST", "/v1/runs/upload"))
        self.assertFalse(is_run_creation("GET", "/v1/runs"))
        self.assertFalse(is_run_creation("POST", "/v1/runs/abc/cancel"))

    def test_production_defaults(self) -> None:
        with patch.dict("os.environ", PROD_ENV, clear=True):
            settings = get_api_settings()
        self.assertEqual(settings.rate_limit_per_minute, 3)
        self.assertEqual(settings.rate_limit_per_day, 50)

    def test_negative_limits_rejected(self) -> None:
        with patch.dict("os.environ", {"OCR_RATE_LIMIT_PER_DAY": "-1"}, clear=True):
            with self.assertRaises(RuntimeError):
                get_api_settings()

    def test_http_returns_429_after_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {**PROD_ENV, "OCR_RUNS_DIR": tmp, "OCR_RATE_LIMIT_PER_MINUTE": "2"}
            with patch.dict("os.environ", env, clear=True):
                client = TestClient(create_app())
                headers = {"Authorization": "Bearer secret"}
                codes = [
                    client.post("/v1/runs", json={"image_path": "/x.jpg"}, headers=headers).status_code
                    for _ in range(3)
                ]
                unauth = client.post("/v1/runs", json={"image_path": "/x.jpg"})
                listing = client.get("/v1/runs", headers=headers)
        self.assertEqual(codes[:2], [403, 403])
        self.assertEqual(codes[2], 429)
        self.assertEqual(unauth.status_code, 401, "auth is checked before quota")
        self.assertEqual(listing.status_code, 200, "reads are not rate limited")


class ServerDefaultsTest(unittest.TestCase):
    def test_env_default_extractor_applies_when_unset(self) -> None:
        env = {
            "OCR_DEFAULT_EXTRACTOR_PROVIDER": "openrouter",
            "OCR_DEFAULT_EXTRACTOR_MODEL": "google/gemini-3-flash-preview",
        }
        with patch.dict("os.environ", env, clear=True):
            config = build_config(parse_options_json(None))
            self.assertEqual(config.extractor_provider, "openrouter")
            self.assertEqual(config.extractor_model, "google/gemini-3-flash-preview")

            explicit = build_config(
                parse_options_json('{"extractor_provider": "docstrange", "extractor_model": "nanonets-ocr-3"}')
            )
            self.assertEqual(explicit.extractor_provider, "docstrange")
            self.assertEqual(explicit.extractor_model, "nanonets-ocr-3")

            other_option = build_config(parse_options_json('{"gamma": 0.5}'))
            self.assertEqual(other_option.extractor_provider, "openrouter")
            self.assertEqual(other_option.gamma, 0.5)

    def test_without_env_keeps_schema_defaults(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            config = build_config(parse_options_json(None))
        self.assertEqual(config.extractor_provider, "docstrange")


class McpPathToolTest(unittest.TestCase):
    def _tool_names(self, env: dict[str, str]) -> set[str]:
        from fastmcp import Client

        from ocr_engine_mcp.server import create_mcp

        async def names() -> set[str]:
            async with Client(create_mcp()) as client:
                return {tool.name for tool in await client.list_tools()}

        with patch.dict("os.environ", env, clear=True):
            return asyncio.run(names())

    def test_path_tool_hidden_in_production(self) -> None:
        names = self._tool_names({"OCR_ENV": "production"})
        self.assertNotIn("submit_scoresheet_from_path", names)
        self.assertIn("submit_scoresheet_base64", names)

    def test_path_tool_available_in_development(self) -> None:
        self.assertIn("submit_scoresheet_from_path", self._tool_names({"OCR_ENV": "development"}))

    def test_path_tool_override(self) -> None:
        names = self._tool_names({"OCR_ENV": "development", "MCP_ALLOW_PATH_INPUT": "false"})
        self.assertNotIn("submit_scoresheet_from_path", names)


if __name__ == "__main__":
    unittest.main()
