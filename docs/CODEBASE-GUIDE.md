[← Back to README](../README.md)

# FIBA OCR Engine Codebase Guide

**This guide is for maintainers and contributors who need to understand where responsibilities live in `ocr-engine`, which architectural boundaries are non-negotiable, and which file to open when something needs to change.**

FIBA OCR Engine extracts structured basketball game data from FIBA scoresheet images. The center of the product is a pure-Python domain library (`ocr-engine-core`); the FastAPI HTTP server, CLI scripts, MCP server, and Next.js web app are adapters and interfaces around that core.

## 90-second mental model

```text
Callers & Interfaces
  Browser (packages/web)     Agent (Claude/Cursor/etc.)     Local Operator
         │                            │                           │
         │ HTTP + Supabase JWT        │ MCP (stdio / HTTP)        │ CLI flags
         ▼                            ▼                           ▼
  packages/api (ocr-api) ◄──── packages/mcp (ocr-mcp)      packages/cli (ocr-run, ...)
    FastAPI composition          Pure HTTP client            Direct core caller
    Auth · Rate limit ·          (never imports core)
    Sanitization · RunRepository
         │                                                        │
         └──────────────────────────┬─────────────────────────────┘
                                    ▼
                     packages/core-engine (ocr_engine_core)
                       OcrToolbox · FibaOcrPipeline · PipelineConfig
                       Preprocessor · Cropper · Enhancer · Extractor
                       ModelProviders · OutputBuilder · ValidationEngine
                                    │
                                    ▼
                     runs/<run_id>/ (canonical run layout)
                       input/ · artifacts/ · raw/ · status.json · trace.json · result.json

Supporting Persistence & Ops
  Supabase (supabase/migrations/) ── accounts · api_keys · RLS · rate_limit_counters
  Evaluation (evaluation/)         ── ground-truth dataset benchmarks
  Graphify (docs/graphify.md)      ── versioned repository knowledge graph (graphify-out/)
```

The rule that organizes the whole monorepo:

> **The core engine is pure OCR domain logic; API, CLI, MCP, and Web are thin adapters around the canonical run.**

## Recommended reading path

| Step | Page | Read this when... |
|---|---|---|
| 1 | [Mental Model](codebase/mental-model.md) | You need the product shape, runtime split, and design compass before opening code. |
| 2 | [Repository Map](codebase/repository-map.md) | You need to decide which package owns a change before writing code. |
| 3 | [Architecture](ARCHITECTURE.md) | You need end-to-end flows: 7-phase pipeline, async run lifecycle, auth layers, and validation/confidence. |
| 4 | [Graphify Guide](graphify.md) | You are mapping dependencies or updating the repository knowledge graph after code/doc changes. |
| 5 | [Core Pipeline](codebase/core-pipeline.md) | You are touching `FibaOcrPipeline`, `OcrToolbox`, providers, `PipelineConfig`, validation plugins, or artifacts. |
| 6 | [Dataset Evaluation](EVALUATION.md) | You are running or modifying ground-truth accuracy benchmarks under `evaluation/`. |
| 7 | [API, Auth & Supabase](codebase/api-and-auth.md) | You are touching FastAPI routes, layered auth, rate limiting, error envelopes, `RunRepository`, or Supabase migrations. |
| 8 | [Adapters & Web](codebase/adapters-and-web.md) | You are touching CLI scripts, MCP tools/resources/prompts, or the Next.js admin/tester app. |
| 9 | [Deployment & Ops](DEPLOYMENT.md) | You are deploying to Cloud Run / Vercel, running `scripts/serve.sh`, or configuring secrets/migrations. |
| 10 | [Maintainer Playbook](codebase/maintainer-playbook.md) | You are reviewing a PR, planning a cross-package change, or checking warning signs. |
| 11 | [Reference Map](codebase/reference-map.md) | You need a traceable index from documentation surfaces and scripts to source files. |

## Quick map: if you need X, read Y

| If you need to... | Open first | Then check |
|---|---|---|
| Understand the product and quickstart | [README.md](../README.md) | [Mental Model](codebase/mental-model.md) · [DOCS.md](../DOCS.md) |
| Place new code in the right package | [Repository Map](codebase/repository-map.md) | Package `AGENTS.md` in target package |
| Change pipeline phases or `OcrToolbox` | `packages/core-engine/src/ocr_engine_core/toolbox.py` | `pipeline.py`, `types.py`, `tests/test_toolbox.py` |
| Add or modify a model provider | `packages/core-engine/src/ocr_engine_core/providers/__init__.py` | `providers/base.py`, `providers/http_base.py`, `tests/test_core_contracts.py` |
| Change default models or `PipelineConfig` | `packages/core-engine/src/ocr_engine_core/config/pipeline_config.py` | `.env.example`, `packages/api/src/ocr_engine_api/pipeline_options.py` |
| Add or adjust validation plugins or confidence | `packages/core-engine/src/ocr_engine_core/validation/engine.py` | `validation/plugins/`, `tests/test_validation_confidence.py` |
| Change HTTP endpoints or composition root | `packages/api/src/ocr_engine_api/main.py` | `routes/runs.py`, `routes/me.py`, `routes/admin.py`, `tests/test_api.py` |
| Change auth (`ocr_live_`, JWT, static bearer) or rate limits | `packages/api/src/ocr_engine_api/auth_api_key.py` | `auth_supabase.py`, `auth.py`, `rate_limit.py`, `tests/test_auth.py` |
| Change async execution or run storage (`runs/`) | `packages/api/src/ocr_engine_api/services/run_executor.py` | `services/run_repository.py`, `tests/test_run_repository.py` |
| Change CLI commands (`ocr-run`, `ocr-dataset`, etc.) | `packages/cli/pyproject.toml` | `packages/cli/src/ocr_engine_cli/` |
| Change MCP tools, resources, or prompts | `packages/mcp/src/ocr_engine_mcp/server.py` | `tools.py`, `client.py`, `auth.py`, [packages/mcp/docs/mcp-server.md](../packages/mcp/docs/mcp-server.md) |
| Change web UI, admin, or tester demos | `packages/web/src/app/` | `packages/web/src/lib/api.ts`, `packages/web/src/lib/auth/account.ts`, [packages/web/README.md](../packages/web/README.md) |
| Inspect DB schema, RLS, or rate-limit RPCs | `supabase/migrations/` | `packages/api/src/ocr_engine_api/supabase_client.py` |
| Run dataset accuracy benchmarks | [Dataset Evaluation](EVALUATION.md) | `evaluation/evaluate_dataset.py` |
| Deploy API/MCP or update Graphify | [Deployment & Ops](DEPLOYMENT.md) | `scripts/deploy_cloudrun.sh`, `cloudbuild.yaml`, [Graphify Guide](graphify.md) |

---

[Next: Mental Model →](codebase/mental-model.md)
