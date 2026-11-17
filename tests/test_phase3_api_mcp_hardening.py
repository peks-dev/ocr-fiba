"""Unit tests for Phase 3 API & MCP hardening, concurrency, and error consistency."""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests
from fastapi import HTTPException
from fastapi.testclient import TestClient

from ocr_engine_api.auth_api_key import _cache, _cache_get, _cache_set, invalidate_api_key_cache
from ocr_engine_api.auth_supabase import _jwt_cache, _verify_with_supabase_auth_server
from ocr_engine_api.main import create_app
from ocr_engine_api.routes.runs import upload_and_create_run
from ocr_engine_api.services.run_repository import RunRepository, RunRepositoryError
from ocr_engine_core.types import Artifact, RunContext, ToolResult
from ocr_engine_mcp.auth import McpTokenVerifier
from ocr_engine_mcp.client import OcrApiClient, OcrApiError
from ocr_engine_mcp.server import create_mcp


PROD_ENV = {
    "OCR_ENV": "production",
    "OCR_ENGINE_API_KEY": "secret",
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_SERVICE_KEY": "service-role-key",
    "SUPABASE_JWT_SECRET": "jwt-secret-at-least-32-chars!!",
}


class FakeChunkedUploadFile:
    def __init__(self, filename: str, chunks: list[bytes], *, size: int | None = None) -> None:
        self.filename = filename
        self.size = size
        self._chunks = list(chunks)
        self.reads = 0

    async def read(self, size: int = -1) -> bytes:
        self.reads += 1
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


class _FakeToolbox:
    def __init__(self, config) -> None:
        self.config = config

    def run_full_pipeline(self, image_path, output_dir=None, *, run_id=None, runs_dir=Path("runs"), use_run_layout=False, progress_callback=None):
        context = RunContext.create_run(Path(image_path), Path(runs_dir), run_id=run_id)
        context.ensure_dirs()
        context.result_path.write_text(json.dumps({"match_status": "success"}), encoding="utf-8")
        context.trace_path.write_text(json.dumps({"run_id": context.run_id, "steps": []}), encoding="utf-8")
        return ToolResult(
            success=True,
            run_id=context.run_id,
            step="run_full_pipeline",
            status="completed",
            data={"result": {"match_status": "success"}},
            artifacts=[Artifact(name="result.json", path=context.result_path, kind="result")],
        )


class ApiHardeningPhase3Test(unittest.TestCase):
    def setUp(self) -> None:
        _cache.clear()
        _jwt_cache.clear()

    def test_duplicate_run_id_returns_409_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            existing_dir = Path(tmp) / "dup_run"
            existing_dir.mkdir(parents=True)
            marker = existing_dir / "result.json"
            marker.write_text(json.dumps({"match_status": "success"}), encoding="utf-8")

            upload = FakeChunkedUploadFile("sheet.jpg", [b"\xff\xd8\xff\xe0valid-jpeg"])
            with self.assertRaises(HTTPException) as exc:
                asyncio.run(upload_and_create_run(file=upload, run_id="dup_run", runs_dir=tmp))

            self.assertEqual(exc.exception.status_code, 409)
            self.assertEqual(exc.exception.detail["error"]["code"], "RUN_ALREADY_EXISTS")
            self.assertEqual(upload.reads, 0)
            self.assertEqual(json.loads(marker.read_text(encoding="utf-8"))["match_status"], "success")

    def test_chunked_upload_stops_immediately_when_exceeding_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Declared size over limit skips reading completely
            oversized = FakeChunkedUploadFile("sheet.jpg", [b"\xff\xd8\xff\xe0abc"], size=2 * 1024 * 1024)
            with patch.dict("os.environ", {"OCR_MAX_UPLOAD_MB": "1"}, clear=True):
                with self.assertRaises(HTTPException) as exc:
                    asyncio.run(upload_and_create_run(file=oversized, run_id="r_decl", runs_dir=tmp))
            self.assertEqual(exc.exception.status_code, 413)
            self.assertEqual(oversized.reads, 0)

            # Streaming chunks abort as soon as cumulative size crosses limit
            streaming = FakeChunkedUploadFile(
                "sheet.jpg",
                [b"\xff\xd8\xff\xe0" + b"a" * 600_000, b"b" * 600_000, b"c" * 600_000],
            )
            with patch.dict("os.environ", {"OCR_MAX_UPLOAD_MB": "1"}, clear=True):
                with self.assertRaises(HTTPException) as exc2:
                    asyncio.run(upload_and_create_run(file=streaming, run_id="r_stream", runs_dir=tmp))
            self.assertEqual(exc2.exception.status_code, 413)
            self.assertEqual(streaming.reads, 2)
            self.assertFalse((Path(tmp) / "r_stream").exists())

    def test_non_image_magic_bytes_rejected_before_creating_run_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_html = FakeChunkedUploadFile("evil.jpg", [b"<html><script>alert(1)</script></html>"])
            with self.assertRaises(HTTPException) as exc:
                asyncio.run(upload_and_create_run(file=fake_html, run_id="r_evil", runs_dir=tmp))

            self.assertEqual(exc.exception.status_code, 400)
            self.assertEqual(exc.exception.detail["error"]["code"], "INVALID_IMAGE_CONTENT")
            self.assertFalse((Path(tmp) / "r_evil").exists())

    def test_repository_reconciles_stalled_and_crashed_runs_and_skips_hidden_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".lost+found").mkdir()

            stalled_dir = Path(tmp) / "run_stalled"
            stalled_dir.mkdir()
            (stalled_dir / "status.json").write_text(
                json.dumps({"run_id": "run_stalled", "status": "running", "updated_at": time.time() - 1200}),
                encoding="utf-8",
            )

            recovered_dir = Path(tmp) / "run_recovered"
            recovered_dir.mkdir()
            (recovered_dir / "status.json").write_text(
                json.dumps({"run_id": "run_recovered", "status": "running", "updated_at": time.time() - 1200}),
                encoding="utf-8",
            )
            (recovered_dir / "result.json").write_text(
                json.dumps({"match_status": "success"}),
                encoding="utf-8",
            )

            repo = RunRepository(tmp, stale_run_seconds=60)
            listed = repo.list_runs()
            self.assertEqual(listed["count"], 2)
            self.assertEqual(repo.get_status("run_stalled")["status"], "failed")
            self.assertEqual(repo.get_status("run_stalled")["error"]["code"], "RUN_STALLED")
            self.assertEqual(repo.get_status("run_recovered")["status"], "completed")
            self.assertEqual(repo.get_result("run_recovered")["match_status"], "success")

            with self.assertRaises(RunRepositoryError) as exc:
                repo.resolve_run_dir("bad..id")
            self.assertEqual(exc.exception.code, "INVALID_RUN_ID")

    def test_me_routes_use_standard_error_envelope_and_invalidate_api_key_cache(self) -> None:
        _cache_set("hash-a", "acct-1", "active")
        _cache_set("hash-b", "acct-2", "active")

        with tempfile.TemporaryDirectory() as tmp:
            env = {**PROD_ENV, "OCR_RUNS_DIR": tmp}
            with patch.dict("os.environ", env, clear=True):
                with patch("ocr_engine_api.routes.me.get_account_by_supabase_user_id", return_value=None):
                    app = create_app()
                    from ocr_engine_api.auth_supabase import require_supabase_user

                    app.dependency_overrides[require_supabase_user] = lambda: {"sub": "u-missing"}
                    client = TestClient(app)
                    missing = client.get("/v1/me/api-keys", headers={"Authorization": "Bearer ej.a.b"})

                self.assertEqual(missing.status_code, 404)
                self.assertEqual(missing.json()["detail"]["error"]["code"], "ACCOUNT_NOT_FOUND")

                with patch(
                    "ocr_engine_api.routes.me.get_account_by_supabase_user_id",
                    return_value={"id": "acct-1", "status": "active"},
                ):
                    with patch("ocr_engine_api.routes.me.delete_api_key_record", return_value={"id": "k1"}):
                        app = create_app()
                        app.dependency_overrides[require_supabase_user] = lambda: {"sub": "u-1"}
                        client = TestClient(app)
                        deleted = client.delete("/v1/me/api-keys/k1", headers={"Authorization": "Bearer ej.a.b"})

        self.assertEqual(deleted.status_code, 200)
        self.assertIsNone(_cache_get("hash-a"))
        self.assertIsNotNone(_cache_get("hash-b"))

    def test_asymmetric_jwt_auth_caches_verified_claims_and_uses_standard_error_envelope(self) -> None:
        class FakeResp:
            def __init__(self, payload: dict) -> None:
                self._payload = payload

            def read(self) -> bytes:
                return json.dumps(self._payload).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

        with patch("ocr_engine_api.auth_supabase.urlopen", return_value=FakeResp({"id": "uid-1", "email": "a@b.c"})) as open_mock:
            c1 = _verify_with_supabase_auth_server("header.payload.sig", "https://ex.supabase.co", "pub-key")
            c2 = _verify_with_supabase_auth_server("header.payload.sig", "https://ex.supabase.co", "pub-key")

        self.assertEqual(c1["sub"], "uid-1")
        self.assertEqual(c2["sub"], "uid-1")
        open_mock.assert_called_once()

        with self.assertRaises(HTTPException) as exc:
            _verify_with_supabase_auth_server("tok", "https://ex.supabase.co", "")
        self.assertEqual(exc.exception.status_code, 500)
        self.assertEqual(exc.exception.detail["error"]["code"], "SUPABASE_NOT_CONFIGURED")


class McpHardeningPhase3Test(unittest.TestCase):
    def test_client_validates_run_id_and_handles_timeouts_and_closes_owned_session(self) -> None:
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.Timeout("timed out")

        with OcrApiClient("http://api.test", session=mock_session) as client:
            with self.assertRaises(OcrApiError) as bad_id:
                client.get_run("../escape")
            self.assertEqual(bad_id.exception.code, "INVALID_RUN_ID")

            with self.assertRaises(OcrApiError) as bad_art:
                client.get_artifact("run_1", "../secret.json")
            self.assertEqual(bad_art.exception.code, "INVALID_ARTIFACT_PATH")

            with self.assertRaises(OcrApiError) as timed_out:
                client.get_run("run_1")
            self.assertEqual(timed_out.exception.status_code, 504)
            self.assertEqual(timed_out.exception.code, "API_TIMEOUT")

        # External session should NOT be closed; owned session MUST be closed
        mock_session.close.assert_not_called()
        with patch("ocr_engine_mcp.client.requests.Session") as session_cls:
            with OcrApiClient("http://api.test"):
                pass
            session_cls.return_value.close.assert_called_once()

    def test_mcp_resource_returns_structured_error_instead_of_raising_raw_api_error(self) -> None:
        from fastmcp import Client

        with patch("ocr_engine_mcp.server.OcrApiClient.get_run", side_effect=OcrApiError(404, "RUN_NOT_FOUND", "missing")):
            mcp = create_mcp()

            async def read_res() -> str:
                async with Client(mcp) as client:
                    contents = await client.read_resource("run://run_missing")
                    return contents[0].text

            payload = json.loads(asyncio.run(read_res()))

        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"]["code"], "RUN_NOT_FOUND")

    def test_mcp_verifier_runs_probe_in_worker_thread(self) -> None:
        import threading

        caller_threads: list[int] = []

        def probe(_token: str) -> bool:
            caller_threads.append(threading.get_ident())
            return True

        main_thread = threading.get_ident()
        verifier = McpTokenVerifier(static_token="s", probe=probe)
        tok = asyncio.run(verifier.verify_token("ocr_live_threadcheck"))
        self.assertIsNotNone(tok)
        self.assertEqual(len(caller_threads), 1)
        self.assertNotEqual(caller_threads[0], main_thread)


if __name__ == "__main__":
    unittest.main()
