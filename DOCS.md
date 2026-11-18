[← Back to README](README.md)

# FIBA OCR Engine — Technical Reference

**Complete canonical contract reference for `ocr-engine`.**

For product overview and quickstart, see [README.md](README.md). For package ownership and internal design, see [Codebase Guide](docs/CODEBASE-GUIDE.md) and [Architecture](docs/ARCHITECTURE.md).

---

## Quick Navigation

| Section | What you'll find |
|---|---|
| [Documentation Authority](#documentation-authority) | Which doc surface owns each contract and what must change together |
| [Documentation Surface Catalog](#documentation-surface-catalog) | Audience, authority, and status of tracked Markdown files |
| [Environment Variables](#environment-variables) | Core, API, MCP, Web, and deployment variables with defaults |
| [Core Pipeline & Validation](#core-pipeline--validation) | Phases, `PipelineConfig`, providers, 13 validation plugins, `confidence`, and errors |
| [Canonical Run Layout](#canonical-run-layout) | Directory and file contract under `runs/<run_id>/` |
| [HTTP API Endpoints](#http-api-endpoints) | All FastAPI routes, status codes, auth surfaces, quotas, and error envelopes |
| [MCP Surface](#mcp-surface) | Transports, auth verifier, 10 tools, 4 resources, and 3 prompts |
| [CLI Reference](#cli-reference) | Console scripts and key flags |
| [Supabase Schema](#supabase-schema) | Tables, triggers, RLS policies, and rate-limit RPCs |

---

## Documentation Authority

When prose and implementation disagree, code and tests win. This table defines the canonical documentation surface, the authoritative source code, and sibling files that must stay synchronized when a contract changes.

| Contract | Canonical doc surface | Code authority | Must change together |
|---|---|---|---|
| Core pipeline, `PipelineConfig`, providers, validation plugins, confidence | `DOCS.md` (§ Core Pipeline & Validation) | `packages/core-engine/src/ocr_engine_core/` | `docs/codebase/core-pipeline.md`, `docs/ARCHITECTURE.md`, `skills/ocr-run-lifecycle/SKILL.md`, `.env.example` |
| HTTP endpoints, layered auth, rate limit, error envelopes | `DOCS.md` (§ HTTP API Endpoints) | `packages/api/src/ocr_engine_api/` | `docs/codebase/api-and-auth.md`, `skills/api-error-envelope/SKILL.md`, `skills/api-key-auth/SKILL.md` |
| MCP tools, resources, prompts, transport auth | `DOCS.md` (§ MCP Surface) | `packages/mcp/src/ocr_engine_mcp/` | `docs/codebase/adapters-and-web.md`, `packages/mcp/docs/mcp-server.md` |
| CLI console scripts and flags | `DOCS.md` (§ CLI Reference) | `packages/cli/pyproject.toml`, `packages/cli/src/ocr_engine_cli/` | `docs/codebase/adapters-and-web.md`, `README.md` |
| Environment variables | `DOCS.md` (§ Environment Variables) | `settings.py`, `pipeline_config.py`, `image_utils.py`, `packages/web/src/lib/env.ts`, `.env.example`, `packages/web/.env.local.example` | `docs/DEPLOYMENT.md`, `packages/web/README.md` |
| Supabase tables, RLS, triggers, RPCs | `DOCS.md` (§ Supabase Schema) | `supabase/migrations/*.sql` | `docs/codebase/api-and-auth.md`, `docs/DEPLOYMENT.md` |
| Package boundaries and ownership | [docs/codebase/repository-map.md](docs/codebase/repository-map.md) | Package `pyproject.toml` files & import structure | `docs/CODEBASE-GUIDE.md`, `skills/architecture-guardrails/SKILL.md` |
| Git, testing, Graphify, skill rules | [CONTRIBUTING.md](CONTRIBUTING.md) | `scripts/graphify-*`, `pyproject.toml` | `AGENTS.md`, `skills/commit-hygiene/SKILL.md`, `skills/testing-coverage/SKILL.md` |

### Documentation Surface Catalog

| Surface | Audience | Authority | Status |
|---|---|---|---|
| [README.md](README.md) | New users, developers | Guide: overview & quickstart | Living |
| [DOCS.md](DOCS.md) | Users, integrators, maintainers | Canonical: technical reference & authority | Living |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contributors, maintainers | Policy: git, testing, Graphify, skills | Living |
| [AGENTS.md](AGENTS.md) | Repository AI agents | Instruction: guardrails & skill index | Living |
| [CLAUDE.md](CLAUDE.md) | Claude Code | Instruction: includes `@AGENTS.md` | Living |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Maintainers, contributors | Guide: end-to-end architecture & flows | Living |
| [docs/CODEBASE-GUIDE.md](docs/CODEBASE-GUIDE.md) | Maintainers, agents | Canonical: navigation & mental model entry | Living |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Operators | Guide: Cloud Run, Vercel, Supabase, `serve.sh` | Living |
| [docs/EVALUATION.md](docs/EVALUATION.md) | ML/OCR engineers | Guide: dataset ground-truth benchmarks | Living |
| [docs/graphify.md](docs/graphify.md) | Contributors, agents | Guide: Graphify knowledge graph workflow | Living |
| [docs/codebase/*.md](docs/codebase/mental-model.md) | Maintainers, agents | Guide/Canonical: per-domain ownership & playbooks | Living |
| [skills/catalog.md](skills/catalog.md) & `skills/*/SKILL.md` | Repository AI agents | Instruction: modular domain & workflow skills | Living |
| `packages/*/AGENTS.md` | Subdirectory agents | Instruction: lightweight package guardrails | Living |
| [packages/mcp/docs/mcp-server.md](packages/mcp/docs/mcp-server.md) | MCP users/operators | Guide: MCP config & transport summary | Living |
| [packages/web/README.md](packages/web/README.md) | Web contributors | Guide: Next.js local setup & env summary | Living |
| [evaluation/README.md](evaluation/README.md) | Benchmark runners | Guide: quick evaluation commands | Living |

---

## Environment Variables

### Core Engine Provider Keys (`ocr_engine_core.utils.image_utils.PROVIDER_API_KEY_ENV_NAMES`)

Resolved in priority order per provider:

| Provider | Env vars (checked in order) |
|---|---|
| `openrouter` | `OPENROUTER_API_KEY` |
| `gemini` | `GOOGLE_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_GENAI_API_KEY` |
| `glm` | `GLM_API_KEY`, `ZAI_API_KEY` |
| `interfaze` | `INTERFAZE_API_KEY`, `INTERFAZE_KEY` |
| `docstrange` | `DOCSTRANGE_API_KEY` |
| `qubrid` | `QUBRID_API_KEY` |

### Core & API Pipeline Defaults (`pipeline_config.py`, `settings.py`)

| Variable | Default (dev / prod) | Notes |
|---|---|---|
| `OCR_DEFAULT_EXTRACTOR_PROVIDER` | `openrouter` | Default extractor provider when client omits it. |
| `OCR_DEFAULT_EXTRACTOR_MODEL` | `google/gemini-4-carbon` (`nanonets-ocr-3` when `docstrange`) | Default extractor model. |
| `OCR_DEFAULT_EXTRACTOR_REASONING` | `{"effort":"low","exclude":true}` (for `openrouter` + `google/gemini-4-carbon`) | Accepts JSON object, effort (`max`/`xhigh`/`high`/`medium`/`low`/`minimal`/`none`), or `off`/`false`/`disabled`. |

### HTTP API (`packages/api/src/ocr_engine_api/settings.py`, `main.py`)

| Variable | Dev default | Prod default (`OCR_ENV=production`) | Notes |
|---|---|---|---|
| `OCR_ENV` | `development` | `production` | Enables path sanitization, enforces `OCR_RUNS_DIR`, tightens defaults. |
| `OCR_ENGINE_API_KEY` | `None` (no check if unset) | **Required** | Static bearer fallback token. |
| `OCR_RUNS_DIR` | `runs` | `runs` (forced in prod) | Base directory for run folders. |
| `OCR_MAX_UPLOAD_MB` | `20` | `20` | Must be `>= 1`. |
| `OCR_CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Explicit origin list | Comma-separated origins for `CORSMiddleware`. |
| `OCR_ALLOW_PATH_INPUT` | `true` | `false` | Controls `POST /v1/runs {image_path}`. |
| `OCR_RATE_LIMIT_PER_MINUTE` | `0` (off) | `3` | Run-creation cap per minute (`>= 0`). |
| `OCR_RATE_LIMIT_PER_DAY` | `0` (off) | `50` | Run-creation cap per rolling 24h (`>= 0`). |
| `OCR_RATE_LIMIT_STATE_FILE` | `None` | `None` | Optional JSON persistence path for `MemoryRateLimitStore`. |
| `OCR_STALE_RUN_SECONDS` | `900` | `900` | Active-run stall reconciliation threshold (`0` disables). |
| `OCR_API_HOST` / `OCR_API_PORT` (`PORT`) | `0.0.0.0` / `8000` | `0.0.0.0` / `8080` (Docker) | Uvicorn bind settings in `ocr-api`. |
| `SUPABASE_URL` | `""` | Project URL | Needed for `has_supabase` & `has_supabase_service`. |
| `SUPABASE_SERVICE_KEY` | `""` | Secret | Server-only service role key (`has_supabase_service`). |
| `SUPABASE_PUBLISHABLE_KEY` | Fallback: `SUPABASE_ANON_KEY`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Publishable/anon key | Used for asymmetric JWT `/auth/v1/user` verification. |
| `SUPABASE_JWT_SECRET` | `""` | Secret | Required for `has_supabase` and HS256 JWT verification. |

### MCP Server (`packages/mcp/src/ocr_engine_mcp/`)

| Variable | Default | Notes |
|---|---|---|
| `OCR_API_BASE_URL` | `http://127.0.0.1:8000` | Base URL of `ocr-engine-api`. |
| `OCR_API_KEY` | `None` | Bearer key used on stdio and when static `MCP_AUTH_TOKEN` is presented. |
| `OCR_API_TIMEOUT_SECONDS` | `300` | HTTP request timeout for `OcrApiClient`. |
| `MCP_TRANSPORT` | `stdio` | `stdio` or `http`. |
| `MCP_HOST` / `MCP_PORT` (`PORT`) | `127.0.0.1` / `8001` | HTTP bind host/port (`8080` in Docker). |
| `MCP_AUTH_TOKEN` | `None` (auth off) | Enables `McpTokenVerifier` on HTTP (accepts static token or per-client `ocr_live_` keys). |
| `MCP_ALLOW_PATH_INPUT` | Derived (`OCR_ENV != "production"`) | Registers/hides `submit_scoresheet_from_path`. |
| `FASTMCP_STATELESS_HTTP` | — (`true` in Cloud Run) | Stateless Streamable HTTP mode for Cloud Run. |

### Web App (`packages/web/src/lib/env.ts`, `api/league/submissions/route.ts`)

| Variable | Scope | Notes |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Browser + Server | Required. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Browser + Server | Required (or `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`). |
| `NEXT_PUBLIC_OCR_API_URL` | Browser + Server | Defaults to `http://localhost:8000` locally. |
| `NEXT_PUBLIC_SITE_URL` | Browser + Server | Optional canonical origin for invite `redirectTo`. |
| `SUPABASE_SERVICE_KEY` | Server only | Required for `/admin` & invite acceptance (`createAdminClient`). |
| `AIRTABLE_TOKEN`, `AIRTABLE_BASE_ID`, `AIRTABLE_LEAGUE_TABLE` | Server only | Optional; powers `/api/league/submissions` (default table: `"League Submissions"`). |

---

## Core Pipeline & Validation

- **Seven ordered steps (`OcrToolbox.run_full_pipeline` / `FibaOcrPipeline`):**
  1. `preprocess_sheet` — sheet isolation & perspective warp (`meta.preprocess_fallback = True` on `ValueError` fallback)
  2. `detect_sections` — 5 main sections (`header`, `team_a`, `team_b`, `progressive_score`, `footer`) via cropper (`openrouter` / `google/gemini-3-flash-preview` by default)
  3. `crop_team_fouls` — sub-crops `team_a_fouls` and `team_b_fouls`
  4. `enhance_sections` — gamma (`0.7`) + CLAHE + optional `grid_removal` (`False` | `"inpaint"` | `"handwriting"`)
  5. `extract_sections` — parallel extraction (`extractor_max_workers=7`) across 7 `TARGETS` (`header`, `team_a`, `team_b`, `team_a_fouls`, `team_b_fouls`, `progressive_score`, `footer`), honoring `SectionOverride` and bumping `max_tokens >= 16000` when `reasoning` is active
  6. `build_final_output` — normalization, foul/entry derivations, running-score points, `meta`
  7. `validate_result` — plugin validation + `match_status` + `confidence`
- **Validation plugins (13 total, `validation/plugins/`):**
  - `CATEGORY_CORE` (**11 run by default** when `validation_plugins=None`): `core_quarter_sums`, `core_duplicate_numbers`, `core_ghost_players`, `core_progressive_vs_final`, `core_player_vs_progressive`, `core_progressive_sequence`, `core_entry_and_fouls_consistency`, `core_illegible_marks`, `core_preprocess_fallback`, `referee_player_points_sum`, `referee_winner_consistency`.
  - `CATEGORY_SPORT_RULES` (**2 opt-in**, enabled by name or `"all"`): `fiba_player_fouls`, `fiba_team_fouls`.
- **Confidence object (`validation/base.py`):** `{ score, level, sections: { header: 0.10w, team_a: 0.25w, team_b: 0.25w, progressive_score: 0.25w, footer: 0.15w }, warning_counts: { critical, high, medium, low } }`. Caps global score at `0.49` (`error`) and `0.89` (`needs_review`).
- **Typed exceptions (`exceptions.py`):** `OcrEngineError` → `ConfigurationError`, `InputError`, `PipelineError` (`CroppingError`, `ExtractionError`), `ProviderError` (`ProviderAuthError`, `ProviderRateLimitError`, `ProviderTimeoutError`, `ProviderServerError`, `ProviderConnectionError`, `ProviderInvalidResponseError`), `ValidationEngineError`.

For deep implementation details, see [docs/codebase/core-pipeline.md](docs/codebase/core-pipeline.md).

---

## Canonical Run Layout

Created by `RunContext.create_run` (`use_run_layout=True`) and managed by API `RunRepository`:

```text
runs/<run_id>/
├── input/         # Source/uploaded image
├── artifacts/     # Preprocessed sheet, boxes*.json, cropped & enhanced PNGs
├── raw/           # Raw response directory
├── status.json    # Atomic API status: queued | running | completed | failed | cancelled
├── trace.json     # RunTracer step timings, token usage, artifacts, summary
└── result.json    # Final validated FIBA scoresheet JSON
```

`run_id` must match `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$` (no `..`).

---

## HTTP API Endpoints

### Error Envelopes

- **Middleware / rate-limiter / 500 handler (`JSONResponse`):** top-level `{"success": false, "error": {"code": "...", "message": "...", "retryable": bool, "details"?: {...}}}`.
- **Route/dependency errors (`error_response` / `engine_error_response`):** FastAPI `HTTPException(detail={"success": false, "error": {...}})` serialized under `"detail"`.

### Routes

| Method & Path | Auth | Success Status | Key Query / Body / Error Codes |
|---|---|---|---|
| `GET /health` | Exempt | `200` | Returns `{"status": "ok"}`. |
| `POST /v1/runs` | Middleware + Rate Limit | `200` | JSON `CreateRunRequest` (`image_path`, `run_id?`, `runs_dir?`, `options?`). `403 PATH_INPUT_DISABLED`, `404 INPUT_IMAGE_NOT_FOUND`, `409 RUN_ALREADY_EXISTS`, `429 RATE_LIMITED`, `503 RATE_LIMIT_UNAVAILABLE`. |
| `POST /v1/runs/upload` | Middleware + Rate Limit | `200` | Multipart `file` (`.jpg/.jpeg/.png/.webp`, magic-byte checked), `run_id?`, `runs_dir?`, `options_json?`. `400 EMPTY_UPLOAD` / `UNSUPPORTED_UPLOAD_TYPE` / `INVALID_IMAGE_CONTENT` / `INVALID_OPTIONS_JSON`, `413 UPLOAD_TOO_LARGE`, `409 RUN_ALREADY_EXISTS`. |
| `GET /v1/runs` | Middleware | `200` | Query `runs_dir` (`"runs"`), `limit` (`1..200`, default `50`). |
| `GET /v1/runs/{run_id}` | Middleware | `200` | Query `runs_dir`. Returns run summary + up to 20 artifacts. `404 RUN_NOT_FOUND`. |
| `DELETE /v1/runs/{run_id}` | Middleware | `200` | Query `runs_dir`. Deletes run directory recursively. |
| `GET /v1/runs/{run_id}/trace` | Middleware | `200` | Query `runs_dir`. Returns `trace.json` (`404 RUN_FILE_NOT_FOUND`). |
| `GET /v1/runs/{run_id}/result` | Middleware | `200` | Query `runs_dir`. `409 RUN_NOT_COMPLETED`, `422 RUN_FAILED`, `404 RUN_FILE_NOT_FOUND`. |
| `GET /v1/runs/{run_id}/artifacts` | Middleware | `200` | Query `runs_dir`, `limit` (`1..500`, default `200`). |
| `GET /v1/runs/{run_id}/artifacts/{name:path}` | Middleware | `200` | Query `runs_dir`. `FileResponse` (`400 INVALID_ARTIFACT_PATH`, `404 ARTIFACT_NOT_FOUND`). |
| `POST /v1/me/api-keys/bootstrap` | Supabase JWT (`has_supabase`) | `200` | Issues first `ocr_live_<64 hex>` key once (`409 API_KEY_ALREADY_EXISTS`). |
| `GET /v1/me/api-keys` | Supabase JWT (`has_supabase`) | `200` | Lists caller's keys (metadata + `key_prefix` only). |
| `POST /v1/me/api-keys` | Supabase JWT (`has_supabase`) | `200` | Query `name` (`"default"`). Issues additional key once. |
| `DELETE /v1/me/api-keys/{key_id}` | Supabase JWT (`has_supabase`) | `200` | Hard-deletes key + invalidates cache (`404 API_KEY_NOT_FOUND`). |
| `GET /v1/admin/accounts` | Admin JWT (`has_supabase`) | `200` | Lists all `public.accounts` (`403 FORBIDDEN` if not active admin). |
| `GET /v1/admin/accounts/{account_id}/api-keys` | Admin JWT (`has_supabase`) | `200` | Lists target account's keys (`404 ACCOUNT_NOT_FOUND`). |
| `POST /v1/admin/accounts/{account_id}/api-keys` | Admin JWT (`has_supabase`) | `200` | Query `name` (`"default"`). Issues key once (`403 FORBIDDEN` if target inactive). |
| `DELETE /v1/admin/accounts/{account_id}/api-keys/{key_id}` | Admin JWT (`has_supabase`) | `200` | Hard-deletes target key + invalidates cache. |

In `OCR_ENV=production`, all `/v1/runs*` JSON payloads pass through `sanitize_for_public_response`, stripping filesystem path fields and populating `links`.

---

## MCP Surface

Registered by `create_mcp()` in `packages/mcp/src/ocr_engine_mcp/server.py` (all calls route over HTTP through `OcrApiClient`):

- **Tools (10):**
  - `submit_scoresheet_from_path(image_path, run_id?, options?)` *(only registered when `path_input_allowed()` is true)*
  - `submit_scoresheet_base64(image_base64, filename="scoresheet.jpg", run_id?, options?)`
  - `poll_run(run_id)`
  - `wait_for_run(run_id, timeout_seconds=300, poll_interval_seconds=2)`
  - `list_runs(limit=20)`
  - `inspect_run(run_id)`
  - `get_run_result(run_id)`
  - `get_run_trace(run_id)`
  - `list_run_artifacts(run_id, limit=200)`
  - `get_artifact(run_id, artifact_name)`
- **Resources (`application/json`):** `run://{run_id}`, `result://{run_id}`, `trace://{run_id}`, `artifact://{run_id}/{artifact_name}`.
- **Prompts:** `review_extraction(run_id)`, `suggest_retry_strategy(run_id)`, `explain_validation_warnings(run_id)`.

---

## CLI Reference

Console scripts in `packages/cli/pyproject.toml`:

| Script | Signature & key flags |
|---|---|
| `ocr-run` | `ocr-run <image> [--output-dir DIR \| --run-layout --runs-dir DIR --run-id ID] [--cropper ...] [--cropper-model ...] [--extractor ...] [--extractor-model ...] [--extractor-reasoning-effort ...] [--extractor-max-workers N] [--validation all\|NAMES...] [--override-section SECTION:PROVIDER:MODEL] [--override-reasoning-effort ...] [--grid-removal inpaint\|handwriting] [--json]` |
| `ocr-dataset` | `ocr-dataset [--only SHEETS...] [--skip SHEETS...] [--output-dir DIR \| --run-layout --runs-dir DIR] [--grid-removal ...] [--gamma FLOAT] [--cropper ...] [--cropper-model ...] [--extractor ...] [--extractor-model ...] [--extractor-reasoning-effort ...]` |
| `ocr-binarize` | `ocr-binarize <input> [output] [--method adaptive\|otsu\|both] [--block-size 15] [--c 10]` |
| `ocr-progressive-score` | `ocr-progressive-score <image> [--gt GROUND_TRUTH_JSON]` |

---

## Supabase Schema

Defined in `supabase/migrations/*.sql`:

| Object | Columns / Signature | Access & Security |
|---|---|---|
| `public.accounts` | `id`, `supabase_user_id` (unique FK → `auth.users`), `email`, `status`, `plan`, `role` (`admin \| tester`), `assigned_demo` (`referee \| player \| club \| null`), `invited_by`, `invited_at`, `accepted_at`, timestamps | RLS: user reads own row; `service_role` full access. Testers must have non-null `assigned_demo`. |
| `public.api_keys` | `id`, `account_id` (FK → `accounts`), `key_hash` (unique), `key_prefix`, `name`, `status`, `created_at`, `last_used_at`, `revoked_at` | RLS: `service_role` full access. Only SHA-256 hashes stored. |
| `public.admin_invitations` | `id`, `email`, `assigned_demo`, `status` (`invited \| accepted \| cancelled \| failed`), `invited_by`, `invited_user_id`, `error_message`, timestamps | RLS: `service_role` full access. |
| `public.handle_new_user()` | Trigger `on_auth_user_created` (`auth.users` after insert) | `SECURITY DEFINER`, `search_path = ''`, execute revoked from `public`/`anon`/`authenticated`. Reads `role='admin'` **only** from `raw_app_meta_data`. |
| `private.rate_limit_events` | `id`, `bucket_key`, `consumed_at` | RLS deny-all; all grants revoked from `public`/`anon`/`authenticated`. |
| `public.consume_rate_limit(p_key, p_per_minute, p_per_day)` | `SECURITY INVOKER` wrapper → `private.consume_rate_limit(...)` | Advisory-locked per-key sliding window + opportunistic 2-day cleanup via `private.cleanup_rate_limit_events()`. Callable by `service_role`. |

---

[← Back to README](README.md) · [Codebase Guide →](docs/CODEBASE-GUIDE.md)
