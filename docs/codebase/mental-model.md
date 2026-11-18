[← Codebase Guide](../CODEBASE-GUIDE.md) | [Next: Repository Map →](repository-map.md)

# Mental Model

**FIBA OCR Engine turns raw scoresheet photos into validated, confidence-scored JSON through an isolated seven-phase pipeline, exposed uniformly across CLI, HTTP API, MCP, and Web.**

## What FIBA OCR Engine is

| It is | What that means in the code |
|---|---|
| **A pure OCR domain library at the center** | `packages/core-engine/` (`ocr-engine-core`) owns preprocessing, section cropping, enhancement, extraction, normalization, validation, tracing, and artifact storage with zero dependencies on `api`, `cli`, `mcp`, or `web`. |
| **A model-agnostic extraction pipeline** | `OcrToolbox` and `FibaOcrPipeline` route provider calls through `ModelProvider` (`interfaze`, `gemini`, `glm`, `docstrange`, `qubrid`, `openrouter`) configured via `PipelineConfig` and `SectionOverride`. |
| **Deterministic validation on top of VLM/OCR output** | `ValidationEngine` runs registered plugins (`core`, `fiba_rules`, `referee`) to emit `validation_warnings`, `match_status`, and a weighted `confidence` object rather than trusting raw model output blindly. |
| **Filesystem-canonical run execution** | Runs execute under `runs/<run_id>/` (`input/`, `artifacts/`, `raw/`, `status.json`, `trace.json`, `result.json`) so API polling, CLI inspection, and MCP resources read one shared structure. |
| **Thin delivery adapters** | `packages/api` serves HTTP + auth + rate limits + sanitization; `packages/cli` wraps core workflows for local scripts; `packages/mcp` acts purely as an HTTP client of the API; `packages/web` is an independent Next.js 15 UI over HTTP + Supabase. |
| **Dual-mode auth (local dev vs Supabase)** | Local development can run with static bearer fallback (`OCR_ENGINE_API_KEY`); Supabase-enabled deployments unlock per-account `ocr_live_` keys, JWT sessions, admin invites, demo gating, and Postgres-backed rate limits. |

## What FIBA OCR Engine is not

| It is not | Why that matters |
|---|---|
| **Not a direct-to-VLM prompt wrapper** | Every scoresheet goes through sheet isolation, section cropping (including team-foul sub-crops), enhancement, extraction, normalization, and domain validation. |
| **Not a core library inside MCP or Web** | `packages/mcp` and `packages/web` must **never** import or invoke `ocr_engine_core`. All remote OCR execution goes through `ocr-engine-api`. |
| **Not a raw internal-state API** | Public HTTP responses are sanitized via `sanitize_for_public_response` and errors via `error_response` / `engine_error_response` so local paths, provider secrets, and tracebacks never leak. |
| **Not a client-enforced permission model** | Admin roles (`public.accounts.role == 'admin'`), active account status, assigned tester demos, and `ocr_live_` key checks are enforced server-side in FastAPI dependencies/middleware, Next.js server layouts/middleware, and Supabase RLS. |
| **Not a database-stored artifact blob engine** | Supabase stores accounts, SHA-256 key hashes, and rate-limit counters; run files and artifacts live on the API host's `OCR_RUNS_DIR` filesystem (mounted to GCS `/mnt/data` in Cloud Run). |

## Architecture in 90 seconds

```text
                ┌──────────────────────────┐
                │  Web App (packages/web)  │  Next.js 15 + Supabase SSR
                │  /admin · /test/* · /docs│  Sends Supabase session JWT
                └─────────────┬────────────┘
                              │ HTTPS (Bearer JWT)
                              ▼
┌───────────────┐   HTTP    ┌──────────────────────────────┐
│  MCP Server   ├──────────►│  FastAPI (packages/api)      │
│ (packages/mcp)│  Bearer   │  create_app()                │
│  stdio / HTTP │  ocr_live_│   ├─ api_key_auth middleware │◄──► Supabase
│  (zero core)  │  or static│   ├─ RunRateLimiter          │     accounts, api_keys,
└───────────────┘           │   ├─ /v1/runs/*              │     consume_rate_limit RPC
                            │   ├─ /v1/me/*   (if supa)    │
                            │   └─ /v1/admin/*(if supa)    │
                            └──────────────┬───────────────┘
                                           │ RunExecutor -> OcrToolbox
┌───────────────┐                          ▼
│  CLI Scripts  │  direct   ┌──────────────────────────────┐
│(packages/cli) ├──────────►│ Core Engine (core-engine)    │
│ ocr-run, ...  │  imports  │ FibaOcrPipeline / OcrToolbox │
└───────────────┘           │ Providers + ValidationEngine │
                            └──────────────┬───────────────┘
                                           │
                                           ▼
                            runs/<run_id>/ (input, artifacts, raw,
                                            status.json, trace.json, result.json)
```

## Runtime split

The workspace runs as distinct processes with clear boundaries:

| Runtime | Entry point | Main packages | Primary state / I/O |
|---|---|---|---|
| **HTTP API** | `ocr-api` (`ocr_engine_api.main:run`) | `ocr-engine-api`, `ocr-engine-core` | `OCR_RUNS_DIR` filesystem (`runs/`) + optional Supabase |
| **MCP server (stdio / HTTP)** | `python mcp_server.py` or `ocr-mcp` | `ocr-engine-mcp` | Stateless HTTP client calling `OCR_API_BASE_URL` |
| **CLI tools** | `ocr-run`, `ocr-dataset`, `ocr-binarize`, `ocr-progressive-score` | `ocr-engine-cli`, `ocr-engine-core` | Local images, `runs/` or caller-provided output dir |
| **Web frontend** | `npm run dev` / Vercel (`packages/web`) | `web` (Next.js 15) | Supabase Auth/DB + HTTP calls to `NEXT_PUBLIC_OCR_API_URL` |
| **Evaluation suite** | `python evaluation/evaluate_dataset.py` | `evaluation/`, `dataset/` | Compares `dataset/results*` against ground truth JSON |

## Codebase compass

```text
Core stays pure: domain in core-engine, delivery in adapters.
Depend strictly inward: adapters -> api/core, never core -> adapters.
Filesystem is truth for runs; Supabase is truth for identity and quotas.
Validate and score deterministically; never trust raw extraction alone.
Sanitize every external boundary: envelopes for errors, hashes for keys.
Update Graphify and docs alongside behavioral changes.
```

---

[← Codebase Guide](../CODEBASE-GUIDE.md) | [Next: Repository Map →](repository-map.md)
