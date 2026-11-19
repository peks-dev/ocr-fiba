[← Codebase Guide](../CODEBASE-GUIDE.md) | [← Previous: Mental Model](mental-model.md) | [Next: Core Pipeline →](core-pipeline.md)

# Repository Map

**Use this page to place new behavior in the right package before writing code.** Most architectural regressions happen when HTTP, Supabase, CLI, or MCP logic leaks into `ocr_engine_core`, or when domain logic is duplicated in adapters.

## Dependency direction (hard boundary)

```text
ocr-engine-core  ◄──  ocr-engine-api  ◄──  ocr-engine-mcp (over HTTP, zero Python import)
ocr-engine-core  ◄──  ocr-engine-cli
ocr-engine-web   ──►  ocr-engine-api  (independent Node/Next.js app over HTTP)
```

`ocr_engine_core` **must never** import `ocr_engine_api`, `ocr_engine_cli`, or `ocr_engine_mcp`.
`ocr_engine_mcp` **must never** import `ocr_engine_core`, `ocr_engine_api`, or `ocr_engine_cli`.

## Quick map

| If you need to... | Open first | Then check |
|---|---|---|
| Understand the product and run locally | [README.md](../../README.md) | [Mental Model](mental-model.md) |
| Understand end-to-end execution flows | [Architecture](../ARCHITECTURE.md) | [Codebase Guide](../CODEBASE-GUIDE.md) |
| Modify pipeline steps or atomic tools | `packages/core-engine/src/ocr_engine_core/toolbox.py` | `pipeline.py`, `types.py`, `artifacts.py`, `tracing.py` |
| Modify sheet isolation, cropping, enhancement, extraction, or output building | `packages/core-engine/src/ocr_engine_core/` (`preprocessor.py`, `cropper.py`, `enhancer.py`, `extractor.py`, `output_builder.py`) | `prompts/`, `resources/schemas/`, `utils/` |
| Modify model providers or token usage tracking | `packages/core-engine/src/ocr_engine_core/providers/__init__.py` | `providers/base.py`, `providers/http_base.py`, `providers/<name>.py` |
| Modify pipeline defaults or per-section overrides | `packages/core-engine/src/ocr_engine_core/config/pipeline_config.py` | `.env.example`, `packages/api/src/ocr_engine_api/pipeline_options.py` |
| Modify validation plugins or confidence scoring | `packages/core-engine/src/ocr_engine_core/validation/engine.py` | `validation/base.py`, `validation/registry.py`, `validation/plugins/` |
| Modify FastAPI app assembly, middleware, or settings | `packages/api/src/ocr_engine_api/main.py` | `settings.py`, `errors.py`, `responses.py` |
| Modify API routes (`/v1/runs`, `/v1/me`, `/v1/admin`) | `packages/api/src/ocr_engine_api/routes/` | `schemas.py`, `services/run_executor.py`, `services/run_repository.py` |
| Modify API auth or rate limiting | `packages/api/src/ocr_engine_api/auth_api_key.py` | `auth_supabase.py`, `auth.py`, `api_keys.py`, `rate_limit.py` |
| Modify CLI entry points | `packages/cli/src/ocr_engine_cli/` | `packages/cli/pyproject.toml` |
| Modify MCP server tools, resources, or prompts | `packages/mcp/src/ocr_engine_mcp/server.py` | `tools.py`, `client.py`, `auth.py`, [packages/mcp/docs/mcp-server.md](../../packages/mcp/docs/mcp-server.md) |
| Modify Next.js routes, auth gates, or demos | `packages/web/src/app/` | `packages/web/src/components/`, `packages/web/src/lib/`, [packages/web/README.md](../../packages/web/README.md) |
| Add or inspect Postgres schema/RLS/RPC migrations | `supabase/migrations/` | `packages/api/src/ocr_engine_api/supabase_client.py` |
| Run or extend evaluation scripts | [evaluation/README.md](../../evaluation/README.md) | `evaluation/evaluate_dataset.py` |
| Maintain Cloud Run / Cloud Build / local daemon scripts | `scripts/deploy_cloudrun.sh`, `cloudbuild.yaml`, `Dockerfile` | `scripts/serve.sh`, `scripts/smoke_async_*.py` |

## Package and area ownership

| Area | Responsibility | Should not do |
|---|---|---|
| `packages/core-engine/` (`ocr_engine_core`) | Pure OCR domain logic: 7-phase pipeline, `OcrToolbox`, providers, prompts, JSON schemas, validation engine + 13 plugins, confidence scoring, `RunTracer`, `ArtifactStore`, typed `OcrEngineError` hierarchy. | Import `api`, `cli`, or `mcp`; talk to Supabase; read FastAPI `Request`s; write into `outputs/` or another package's directory. |
| `packages/api/` (`ocr_engine_api`) | FastAPI composition root (`create_app`), layered bearer/JWT auth + caches, rate limiting, input upload/path validation, async `RunExecutor`, filesystem `RunRepository` + stale-run reconciliation, response sanitization, standard error envelopes. | Reimplement OCR/image/validation logic; import `cli` or `mcp`; return raw `HTTPException` or unsanitized host paths; store raw `ocr_live_` keys. |
| `packages/cli/` (`ocr_engine_cli`) | Thin `argparse` console wrappers (`ocr-run`, `ocr-dataset`, `ocr-binarize`, `ocr-progressive-score`) calling `ocr_engine_core`. | Import `api` or `mcp`; make direct HTTP calls to the API; embed core CV/extraction logic inside CLI files. |
| `packages/mcp/` (`ocr_engine_mcp`) | `FastMCP` server exposing tools, resources (`run://`, `result://`, `trace://`, `artifact://`), and prompts over stdio or streamable HTTP via `OcrApiClient` + bearer verification. | Import `core-engine`, `api`, or `cli`; access `runs/` directly from disk; let `OcrApiError` leak unhandled to MCP clients. |
| `packages/web/` (`web`) | Next.js 15 App Router UI: Supabase SSR login/invite/callback, `/admin` account & key management, role-gated tester demos (`/test/player`, `/test/referee`, `/test/club`), authenticated `/docs/quickstart`, Airtable league helper route. | Use `pages/` router; instantiate Supabase clients directly inside components; persist `ocr_live_` keys in browser storage; duplicate server auth checks inside leaf pages when layouts enforce them. |
| `supabase/` | Versioned Postgres SQL migrations for `accounts`, `api_keys`, `rate_limit_counters`, `handle_new_user()` trigger, RLS policies, and `private.consume_rate_limit` RPC. | Contain runtime application code. |
| `evaluation/` | Offline benchmark scripts comparing `dataset/results*` outputs against ground-truth scoresheets (`evaluate_dataset.py` + domain evaluators). | Mutate `core-engine` runtime behavior or production `runs/`. |
| `scripts/` | Operational utilities: Cloud Run deployment, background `serve.sh` runner, API/MCP smoke checks, admin/key provisioning, Graphify setup/update/check wrappers. | Hold core domain rules duplicated from packages. |
| `tests/` | Python workspace test suite (`pytest` / `unittest`) validating contracts across core, API, auth, repository, hardening, and MCP client/auth. | Depend on live remote APIs or unmocked paid model calls by default. |
| `skills/` | Centralized agent-facing guardrails and cookbooks (`skills/catalog.md`). | Replace specs, tests, or runtime checks. |
| `docs/` | Living architecture, codebase guides, Graphify workflow, deployment, and evaluation guides. | Document unimplemented aspirations as shipped behavior. |

## Golden placement rule

```text
Is it image preprocessing, cropping, extraction, prompts, or validation?  -> packages/core-engine
Is it an HTTP endpoint, auth check, rate limit, or run-state query?       -> packages/api
Is it a local terminal command or batch runner?                           -> packages/cli
Is it an MCP tool, resource, prompt, or MCP bearer verifier?              -> packages/mcp
Is it a web screen, React component, or Next.js route?                    -> packages/web
Is it a database table, RLS policy, trigger, or Postgres RPC?             -> supabase/migrations
Is it a ground-truth accuracy metric script?                              -> evaluation
Is it a deploy, smoke test, or repo maintenance script?                   -> scripts
```

When a feature spans multiple packages (for example, adding a new `PipelineConfig` option), implement inward-out:
1. Add and test the domain field in `packages/core-engine`.
2. Expose and validate it in `packages/api` (`pipeline_options.py` / `schemas.py`) and `packages/cli` if applicable.
3. Surface it in `packages/mcp` or `packages/web` if user-facing.
4. Update `.env.example`, docs, and Graphify (`./scripts/graphify-update && ./scripts/graphify-check`).

---

[← Previous: Mental Model](mental-model.md) | [Next: Core Pipeline →](core-pipeline.md)
