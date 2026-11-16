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
from ocr_engine_api.rate_limit import (
    MemoryRateLimitStore,
    RateLimitBackendError,
    RunRateLimiter,
    SupabaseRateLimitStore,
    client_key,
    is_run_creation,
    parse_consume_rate_limit_payload,
)
from ocr_engine_api.routes.runs import create_run
from ocr_engine_api.schemas import CreateRunRequest
from ocr_engine_api.settings import get_api_settings


PROD_ENV = {"OCR_ENV": "production", "OCR_ENGINE_API_KEY": "secret"}

SUPABASE_ENV = {
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_SERVICE_KEY": "service-role-key",
    "SUPABASE_JWT_SECRET": "jwt-secret-at-least-32-chars!!",
}


def _patch_memory_rate_limit_store():
    """Keep existing HTTP quota tests on the in-memory store despite Supabase env."""
    return patch("ocr_engine_api.main.create_rate_limit_store", return_value=MemoryRateLimitStore())


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

    def test_http_rate_limits_ocr_live_keys_independently_of_static_token(self) -> None:
        supabase_env = {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SERVICE_KEY": "service-role-key",
            "SUPABASE_JWT_SECRET": "jwt-secret-at-least-32-chars!!",
        }

        def accept_key(request):
            token = request.headers.get("authorization", "")
            request.state.account_id = "account-b" if "bbbbbbbb" in token else "account-a"
            return None

        with tempfile.TemporaryDirectory() as tmp:
            env = {
                **PROD_ENV,
                **supabase_env,
                "OCR_RUNS_DIR": tmp,
                "OCR_RATE_LIMIT_PER_MINUTE": "2",
            }
            with patch.dict("os.environ", env, clear=True):
                with patch("ocr_engine_api.main.validate_api_key", side_effect=accept_key):
                    with _patch_memory_rate_limit_store():
                        client = TestClient(create_app())
                    key_a = {"Authorization": "Bearer ocr_live_aaaaaaaa"}
                    key_b = {"Authorization": "Bearer ocr_live_bbbbbbbb"}
                    static = {"Authorization": "Bearer secret"}
                    codes_a = [
                        client.post("/v1/runs", json={"image_path": "/x.jpg"}, headers=key_a).status_code
                        for _ in range(3)
                    ]
                    first_b = client.post("/v1/runs", json={"image_path": "/x.jpg"}, headers=key_b)
                    first_static = client.post("/v1/runs", json={"image_path": "/x.jpg"}, headers=static)
                    listing = client.get("/v1/runs", headers=key_a)
        self.assertEqual(codes_a[:2], [403, 403], "path input is still blocked after auth")
        self.assertEqual(codes_a[2], 429, "ocr_live_ keys are rate limited")
        self.assertEqual(first_b.status_code, 403, "a second account has its own bucket")
        self.assertEqual(first_static.status_code, 403, "static fallback token still works")
        self.assertEqual(listing.status_code, 200, "reads are not rate limited")

    def test_ocr_pub_static_token_works_when_supabase_is_configured(self) -> None:
        supabase_env = {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SERVICE_KEY": "service-role-key",
            "SUPABASE_JWT_SECRET": "jwt-secret-at-least-32-chars!!",
        }
        static_token = "ocr_pub_shared-token"
        calls: list[str] = []

        def accept_live_key(request):
            calls.append(request.headers.get("authorization", ""))
            request.state.account_id = "account-1"
            return None

        with tempfile.TemporaryDirectory() as tmp:
            env = {
                **PROD_ENV,
                **supabase_env,
                "OCR_ENGINE_API_KEY": static_token,
                "OCR_RUNS_DIR": tmp,
            }
            with patch.dict("os.environ", env, clear=True):
                with patch("ocr_engine_api.main.validate_api_key", side_effect=accept_live_key):
                    client = TestClient(create_app())
                    static_ok = client.get("/v1/runs", headers={"Authorization": f"Bearer {static_token}"})
                    live_ok = client.get("/v1/runs", headers={"Authorization": "Bearer ocr_live_aaaaaaaa"})
                    wrong_static = client.get("/v1/runs", headers={"Authorization": "Bearer ocr_pub_other"})
        self.assertEqual(static_ok.status_code, 200, "ocr_pub_ uses the static OCR_ENGINE_API_KEY")
        self.assertEqual(live_ok.status_code, 200, "ocr_live_ still goes through Supabase validation")
        self.assertEqual(wrong_static.status_code, 401, "unknown ocr_pub_ tokens are not accepted")
        self.assertEqual(len(calls), 1, "validate_api_key is only called for ocr_live_")
        self.assertIn("ocr_live_aaaaaaaa", calls[0])

    def test_session_jwt_is_accepted_for_run_endpoints(self) -> None:
        supabase_env = {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SERVICE_KEY": "service-role-key",
            "SUPABASE_JWT_SECRET": "jwt-secret-at-least-32-chars!!",
        }
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEifQ.sig"

        def verify(token: str):
            if token != jwt:
                from fastapi import HTTPException
                raise HTTPException(status_code=401, detail="Invalid token")
            return {"sub": "user-1"}

        with tempfile.TemporaryDirectory() as tmp:
            env = {**PROD_ENV, **supabase_env, "OCR_RUNS_DIR": tmp}
            with patch.dict("os.environ", env, clear=True):
                with patch("ocr_engine_api.auth_supabase.verify_supabase_jwt", side_effect=verify):
                    with patch(
                        "ocr_engine_api.api_keys.get_account_by_supabase_user_id",
                        return_value={"id": "account-1", "status": "active", "role": "tester"},
                    ):
                        client = TestClient(create_app())
                        listing = client.get("/v1/runs", headers={"Authorization": f"Bearer {jwt}"})
                        rejected = client.get("/v1/runs", headers={"Authorization": "Bearer eyJhbGciOiJ.bad.sig"})
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(rejected.status_code, 401)

    def test_inactive_session_account_is_forbidden(self) -> None:
        supabase_env = {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SERVICE_KEY": "service-role-key",
            "SUPABASE_JWT_SECRET": "jwt-secret-at-least-32-chars!!",
        }
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEifQ.sig"
        with tempfile.TemporaryDirectory() as tmp:
            env = {**PROD_ENV, **supabase_env, "OCR_RUNS_DIR": tmp}
            with patch.dict("os.environ", env, clear=True):
                with patch(
                    "ocr_engine_api.auth_supabase.verify_supabase_jwt",
                    return_value={"sub": "user-1"},
                ):
                    with patch(
                        "ocr_engine_api.api_keys.get_account_by_supabase_user_id",
                        return_value={"id": "account-1", "status": "invited", "role": "tester"},
                    ):
                        client = TestClient(create_app())
                        response = client.get("/v1/runs", headers={"Authorization": f"Bearer {jwt}"})
        self.assertEqual(response.status_code, 403)

    def test_session_jwt_and_ocr_live_key_share_account_quota(self) -> None:
        supabase_env = {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SERVICE_KEY": "service-role-key",
            "SUPABASE_JWT_SECRET": "jwt-secret-at-least-32-chars!!",
        }
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEifQ.sig"

        def accept_key(request):
            request.state.account_id = "account-1"
            return None

        with tempfile.TemporaryDirectory() as tmp:
            env = {
                **PROD_ENV,
                **supabase_env,
                "OCR_RUNS_DIR": tmp,
                "OCR_RATE_LIMIT_PER_MINUTE": "2",
            }
            with patch.dict("os.environ", env, clear=True):
                with patch("ocr_engine_api.main.validate_api_key", side_effect=accept_key):
                    with patch(
                        "ocr_engine_api.auth_supabase.verify_supabase_jwt",
                        return_value={"sub": "user-1"},
                    ):
                        with patch(
                            "ocr_engine_api.api_keys.get_account_by_supabase_user_id",
                            return_value={"id": "account-1", "status": "active", "role": "tester"},
                        ):
                            with _patch_memory_rate_limit_store():
                                client = TestClient(create_app())
                            first = client.post(
                                "/v1/runs",
                                json={"image_path": "/x.jpg"},
                                headers={"Authorization": f"Bearer {jwt}"},
                            )
                            second = client.post(
                                "/v1/runs",
                                json={"image_path": "/x.jpg"},
                                headers={"Authorization": "Bearer ocr_live_aaaaaaaa"},
                            )
                            third = client.post(
                                "/v1/runs",
                                json={"image_path": "/x.jpg"},
                                headers={"Authorization": f"Bearer {jwt}"},
                            )
        self.assertEqual(first.status_code, 403)
        self.assertEqual(second.status_code, 403)
        self.assertEqual(third.status_code, 429, "JWT and ocr_live_ for the same account share the quota")


class SupabaseRateLimitStoreTest(unittest.TestCase):
    def test_has_supabase_service_does_not_require_jwt_secret(self) -> None:
        with patch.dict(
            "os.environ",
            {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_SERVICE_KEY": "service-role-key"},
            clear=True,
        ):
            settings = get_api_settings()
        self.assertTrue(settings.has_supabase_service)
        self.assertFalse(settings.has_supabase)

    def test_parse_rpc_payload_maps_allowed_and_denied_rows(self) -> None:
        allowed = parse_consume_rate_limit_payload(
            [{"allowed": True, "limit_window": None, "retry_after_seconds": 0, "remaining_minute": 2, "remaining_day": 49}]
        )
        self.assertTrue(allowed.allowed)
        self.assertIsNone(allowed.window)
        self.assertEqual(allowed.retry_after, 0)
        self.assertEqual(allowed.remaining_minute, 2)
        denied = parse_consume_rate_limit_payload(
            {"allowed": False, "limit_window": "minute", "retry_after_seconds": 12, "remaining_minute": 0, "remaining_day": 48}
        )
        self.assertFalse(denied.allowed)
        self.assertEqual(denied.window, "minute")
        self.assertEqual(denied.retry_after, 12)

    def test_parse_rpc_payload_fails_closed_on_empty_or_invalid(self) -> None:
        with self.assertRaises(RateLimitBackendError):
            parse_consume_rate_limit_payload([])
        with self.assertRaises(RateLimitBackendError):
            parse_consume_rate_limit_payload({"limit_window": "minute"})
        with self.assertRaises(RateLimitBackendError):
            parse_consume_rate_limit_payload([{"allowed": True, "retry_after_seconds": "nope"}])

    def test_store_consume_calls_rpc_with_bucket_key_and_limits(self) -> None:
        class FakeRpc:
            def __init__(self) -> None:
                self.params = None

            def rpc(self, name, params):
                self.name = name
                self.params = params
                return self

            def execute(self):
                return type("Resp", (), {"data": [{"allowed": True, "limit_window": None, "retry_after_seconds": 0, "remaining_minute": 1, "remaining_day": 49}]})()

        client = FakeRpc()
        with patch("ocr_engine_api.supabase_client.get_supabase_client", return_value=client):
            decision = SupabaseRateLimitStore().consume("acct:account-1", 3, 50)
        self.assertEqual(client.name, "consume_rate_limit")
        self.assertEqual(client.params, {"p_key": "acct:account-1", "p_per_minute": 3, "p_per_day": 50})
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.remaining_minute, 1)

    def test_store_consume_fails_closed_when_rpc_raises(self) -> None:
        with patch("ocr_engine_api.supabase_client.get_supabase_client", side_effect=RuntimeError("network down")):
            with self.assertRaises(RateLimitBackendError):
                SupabaseRateLimitStore().consume("acct:account-1", 3, 50)

    def test_limiter_uses_injected_store_and_preserves_tuple(self) -> None:
        class FakeStore:
            def consume(self, key, per_minute, per_day):
                self.seen = (key, per_minute, per_day)
                return parse_consume_rate_limit_payload(
                    [{"allowed": False, "limit_window": "day", "retry_after_seconds": 30, "remaining_minute": 3, "remaining_day": 0}]
                )

        store = FakeStore()
        limiter = RunRateLimiter(3, 50, store=store)
        allowed, window, retry = limiter.check("tok:abcd")
        self.assertFalse(allowed)
        self.assertEqual(window, "day")
        self.assertEqual(retry, 30)
        self.assertEqual(store.seen, ("tok:abcd", 3, 50))

    def test_http_uses_supabase_rpc_decision_for_429(self) -> None:
        class FakeRpc:
            def __init__(self) -> None:
                self.calls = 0

            def rpc(self, name, params):
                self.calls += 1
                self.last = (name, params)
                return self

            def execute(self):
                if self.calls <= 2:
                    data = [{"allowed": True, "limit_window": None, "retry_after_seconds": 0, "remaining_minute": 2 - self.calls, "remaining_day": 49}]
                else:
                    data = [{"allowed": False, "limit_window": "minute", "retry_after_seconds": 12, "remaining_minute": 0, "remaining_day": 48}]
                return type("Resp", (), {"data": data})()

        rpc = FakeRpc()
        with tempfile.TemporaryDirectory() as tmp:
            env = {**PROD_ENV, **SUPABASE_ENV, "OCR_RUNS_DIR": tmp, "OCR_RATE_LIMIT_PER_MINUTE": "2"}
            with patch.dict("os.environ", env, clear=True):
                with patch("ocr_engine_api.supabase_client.get_supabase_client", return_value=rpc):
                    client = TestClient(create_app())
                    headers = {"Authorization": "Bearer secret"}
                    codes = [
                        client.post("/v1/runs", json={"image_path": "/x.jpg"}, headers=headers).status_code
                        for _ in range(2)
                    ]
                    denied = client.post("/v1/runs", json={"image_path": "/x.jpg"}, headers=headers)
        self.assertEqual(codes, [403, 403])
        self.assertEqual(denied.status_code, 429)
        self.assertEqual(denied.headers["Retry-After"], "12")
        self.assertEqual(denied.json()["error"]["code"], "RATE_LIMITED")
        self.assertEqual(rpc.calls, 3)
        self.assertEqual(rpc.last[0], "consume_rate_limit")
        self.assertEqual(rpc.last[1]["p_per_minute"], 2)
        self.assertEqual(rpc.last[1]["p_per_day"], 50)
        self.assertTrue(rpc.last[1]["p_key"].startswith("tok:"))

    def test_http_fails_closed_with_503_when_rpc_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {**PROD_ENV, **SUPABASE_ENV, "OCR_RUNS_DIR": tmp, "OCR_RATE_LIMIT_PER_MINUTE": "2"}
            with patch.dict("os.environ", env, clear=True):
                with patch("ocr_engine_api.supabase_client.get_supabase_client", side_effect=RuntimeError("backend down")):
                    client = TestClient(create_app())
                    response = client.post(
                        "/v1/runs",
                        json={"image_path": "/x.jpg"},
                        headers={"Authorization": "Bearer secret"},
                    )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["Retry-After"], "5")
        self.assertEqual(response.json()["error"]["code"], "RATE_LIMIT_UNAVAILABLE")
        self.assertTrue(response.json()["error"]["retryable"])


class CorsOriginsTest(unittest.TestCase):
    def test_parse_cors_origins_supports_a_list(self) -> None:
        from ocr_engine_api.settings import parse_cors_origins

        self.assertEqual(
            parse_cors_origins("https://ocr-fiba.vercel.app,https://ocr-fiba-git-main-peks.vercel.app"),
            ("https://ocr-fiba.vercel.app", "https://ocr-fiba-git-main-peks.vercel.app"),
        )
        self.assertEqual(parse_cors_origins(""), ())
        self.assertEqual(parse_cors_origins(" https://a.example , https://b.example "), ("https://a.example", "https://b.example"))


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
