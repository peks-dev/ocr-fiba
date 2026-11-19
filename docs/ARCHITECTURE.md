[← Back to README](../README.md) | [← Codebase Guide](CODEBASE-GUIDE.md)

# Architecture

**FIBA OCR Engine combines a deterministic computer-vision and validation pipeline with model-agnostic VLM/OCR extraction, exposing asynchronous runs over a canonical filesystem layout.**

- [End-to-End System Flow](#end-to-end-system-flow)
- [Seven-Phase OCR Pipeline](#seven-phase-ocr-pipeline)
- [Canonical Run Layout and Lifecycle](#canonical-run-layout-and-lifecycle)
- [Asynchronous Execution and Stale-Run Recovery](#asynchronous-execution-and-stale-run-recovery)
- [Layered Authentication and Quotas](#layered-authentication-and-quotas)
- [Validation and Confidence Model](#validation-and-confidence-model)
- [Repository Layout](#repository-layout)

---

## End-to-End System Flow

```text
  Client (Web Browser / MCP Client / curl / Smoke Script)
     │
     │  POST /v1/runs or POST /v1/runs/upload
     │  (Authorization: Bearer <ocr_live_... | Supabase JWT | static token>)
     ▼
  FastAPI Middleware (api_key_auth)
     ├─ Validates token against Supabase (60s API key cache / 30s JWT cache) or static fallback
     └─ Checks RunRateLimiter (per-minute / rolling 24h via Supabase RPC or local store)
     │
     ▼
  Route Handler (routes/runs.py)
     ├─ Validates input (path input guard when OCR_ALLOW_PATH_INPUT=false, upload size + magic bytes)
     ├─ Reserves runs/<run_id>/ atomically via RunRepository (409 on collision)
     ├─ Writes initial status.json ("queued") and copies/saves input image
     └─ Enqueues RunExecutor.submit_full_pipeline -> ThreadPoolExecutor(max_workers=2)
     │
     ▼  HTTP 200 OK { success: true, run_id, status: "queued", links }
  Background Worker (RunExecutor)
     └─ OcrToolbox.run_full_pipeline(..., use_run_layout=True)
          ├─ Updates status.json on step progress -> "running"
          ├─ Writes artifacts/, raw/, trace.json, result.json
          └─ Marks status.json -> "completed" (or "failed" with sanitized error)
     │
     ▼
  Client polls GET /v1/runs/{run_id}, then reads /result, /trace, or /artifacts/{name}
  (in production, responses pass through sanitize_for_public_response to strip local paths)
```

---

## Seven-Phase OCR Pipeline

Both `FibaOcrPipeline.process` (used by CLI) and `RunExecutor` (used by the API) execute the same ordered pipeline through `OcrToolbox.run_full_pipeline`:

```text
1. preprocess_sheet    -> Isolate scoresheet and correct perspective (Preprocessor)
2. detect_sections     -> Detect and crop major scoresheet regions (Cropper + cropping prompt)
3. crop_team_fouls     -> Sub-crop team foul boxes (Cropper + team_fouls_cropping prompt)
4. enhance_sections    -> Contrast/threshold enhancement for downstream OCR (Enhancer)
5. extract_sections    -> Extract structured fields per section via ModelProviders (Extractor)
6. build_final_output  -> Normalize sections into unified FIBA game JSON (OutputBuilder)
7. validate_result     -> Run selected validation plugins + compute confidence (ValidationEngine)
```

Key architectural properties:

- **Model-agnostic providers:** `providers/__init__.py` (`create_provider`) instantiates `ModelProvider` implementations (`interfaze`, `gemini`, `glm`, `docstrange`, `qubrid`, `openrouter`). Each phase and section can override the provider/model/reasoning settings via `PipelineConfig` and `SectionOverride`.
- **Single-responsibility core:** `OcrToolbox` exposes atomic step methods returning structured `ToolResult` payloads (`success`, `run_id`, `step`, `status`, `data`, `artifacts`, `warnings`, `usage`, `trace`, `error`), so higher-level workflows and agent callers share one contract.

---

## Canonical Run Layout and Lifecycle

When `use_run_layout=True` (`RunContext.create_run`), every run stores all inputs, intermediates, and outputs under `<runs_dir>/<run_id>/`:

```text
runs/<run_id>/
├── input/         # Source or uploaded scoresheet image
├── artifacts/     # Preprocessed sheet, section crops, enhanced images, JSON step artifacts
├── raw/           # Raw provider payloads/responses
├── status.json    # API-managed run state (queued | running | completed | failed | cancelled)
├── trace.json     # Step-by-step RunTracer audit log (timings, usage, warnings, errors)
└── result.json    # Final normalized and validated FIBA scoresheet output
```

> **Legacy note:** Direct local invocations with `use_run_layout=False` (`RunContext.create`) place outputs in a caller-provided directory without the `runs/<run_id>/artifacts/` nesting. Production API runs (`OCR_ENV=production`) ignore client-supplied `runs_dir` and enforce `OCR_RUNS_DIR`.

---

## Asynchronous Execution and Stale-Run Recovery

`RunRepository` (`packages/api/src/ocr_engine_api/services/run_repository.py`) owns run state on disk without an external job broker:

- **Atomic reservation and status writes:** `reserve_run_dir` atomically allocates `runs/<run_id>/` (failing with `409 RUN_ALREADY_EXISTS` on collision), and status updates write via temp file + `os.replace`.
- **Crash and stall reconciliation:** When reading run status, `RunRepository` reconciles active (`queued` / `running`) runs:
  - If `result.json` already exists on disk after a process interruption, state recovers cleanly.
  - If an active run has had no status activity longer than `OCR_STALE_RUN_SECONDS` (default `900` seconds), it is marked `failed` with `RUN_STALLED`.

---

## Layered Authentication and Quotas

Authentication is split cleanly across transport surfaces and runtime modes:

| Surface | Auth mechanism | Notes |
|---|---|---|
| `GET /health` | Exempt | Used by load balancers, Cloud Run, and smoke checks. |
| `/v1/runs/*` | `api_key_auth` middleware | Accepts `ocr_live_<64 hex>` API keys (SHA-256 hashed in DB, 60s in-memory cache), Supabase session JWTs (30s asymmetric/JWKS cache or HS256), or static bearer token (`OCR_ENGINE_API_KEY`) fallback. |
| `/v1/me/*` | `require_supabase_user` | Mounted only when `settings.has_supabase` is true. Self-service key bootstrap/list/create/delete. |
| `/v1/admin/*` | `require_admin_account` | Mounted only when `settings.has_supabase` is true. Requires active `public.accounts` row with `role == 'admin'`. |
| MCP HTTP (`ocr-mcp`) | Optional `MCP_AUTH_TOKEN` | Accepts static `MCP_AUTH_TOKEN` (forwards `OCR_API_KEY` to API) or per-client `ocr_live_` keys (probed against `GET /v1/runs?limit=1` and forwarded per client). |
| Web (`packages/web`) | Supabase SSR + Next.js middleware | Server layouts enforce `requireAdminAccount()` on `/admin/*`, `requireDemoAccess()` on `/test/{player,referee,club}`, and `requireCurrentUserAccount()` on `/docs/*`. |

Run-creation quotas (`RunRateLimiter`) apply on `POST /v1/runs` and `POST /v1/runs/upload` keyed by account (`acct:{id}` when authenticated via Supabase key/JWT) or token/client fallback, backed either by Supabase's atomic `private.consume_rate_limit` RPC or a local/file-backed store.

---

## Validation and Confidence Model

The core engine pairs LLM/VLM extraction with deterministic basketball-domain checks in `packages/core-engine/src/ocr_engine_core/validation/`:

- **Plugins (13 total across 2 categories / 3 plugin modules):**
  - `core` (`CATEGORY_CORE`, **11 plugins enabled by default** when `validation_plugins=None`): 9 extraction-consistency checks (`plugins/core.py`: quarter sums, duplicate numbers, ghost players, progressive vs final, player vs progressive, progressive sequence, entry and fouls consistency, illegible marks, preprocess fallback) plus 2 referee checks (`plugins/referee.py`: player points sum, winner consistency).
  - `sport_rules` (`CATEGORY_SPORT_RULES`, **2 opt-in plugins** in `plugins/fiba_rules.py`, enabled by name or `"all"`): player fouls, team fouls.
- **Outputs:** Plugins emit typed `validation_warnings`, derive `match_status`, and feed `compute_confidence` to attach a structured `confidence` score (`score`, `level`, `sections`, `warning_counts`) to the final result.

---

## Repository Layout

```text
.
├── packages/
│   ├── core-engine/   # Pure domain library (pipeline, toolbox, providers, validation, tracing)
│   ├── api/           # FastAPI HTTP service (auth, rate limit, runs, /v1/me, /v1/admin)
│   ├── cli/           # Console tools (ocr-run, ocr-dataset, ocr-binarize, ocr-progressive-score)
│   ├── mcp/           # FastMCP adapter (pure HTTP client of ocr-engine-api)
│   └── web/           # Next.js 15 App Router UI (Supabase auth, admin panel, tester demos)
├── supabase/
│   └── migrations/    # 9 versioned SQL migrations (accounts, api_keys, RLS, rate limits)
├── evaluation/        # Dataset evaluators comparing outputs vs ground truth
├── scripts/           # Cloud Run deploy, local daemon runner, smoke tests, Graphify wrappers
├── tests/             # Workspace pytest/unittest suite
├── docs/              # Architecture, codebase guide, deployment, Graphify docs
├── graphify-out/      # Versioned repository knowledge graph
├── Dockerfile         # Container build for Cloud Run (API & MCP)
└── cloudbuild.yaml    # CI/CD rollout on pushes to main
```

---

[← Codebase Guide](CODEBASE-GUIDE.md) | [Repository Map →](codebase/repository-map.md)
