[← Codebase Guide](../CODEBASE-GUIDE.md) | [← Previous: Maintainer Playbook](maintainer-playbook.md)

# Reference Map

**Traceable index from documentation surfaces, skills, scripts, and tests to their purpose and source files.** Use [DOCS.md](../../DOCS.md) for canonical technical contracts.

## Documentation Surfaces

| Document | Purpose |
|---|---|
| [README.md](../../README.md) | Product landing, 30s diagram, quickstart, and docs navigation |
| [DOCS.md](../../DOCS.md) | Canonical technical reference + Documentation Authority + Surface Catalog |
| [CONTRIBUTING.md](../../CONTRIBUTING.md) | Trunk-based Git workflow, commits, testing, Graphify, skill standard |
| [AGENTS.md](../../AGENTS.md) | Agent entry contract, global invariants, and skill trigger table |
| [CLAUDE.md](../../CLAUDE.md) | Claude Code pointer (`@AGENTS.md`) |
| [docs/ARCHITECTURE.md](../ARCHITECTURE.md) | End-to-end flows, 7 pipeline phases, run lifecycle, auth, validation |
| [docs/CODEBASE-GUIDE.md](../CODEBASE-GUIDE.md) | Maintainer landing page, reading path, and quick map |
| [docs/DEPLOYMENT.md](../DEPLOYMENT.md) | `serve.sh`, Cloud Run (`deploy_cloudrun.sh`, `cloudbuild.yaml`), Vercel, Supabase ops |
| [docs/EVALUATION.md](../EVALUATION.md) | Full-sheet and focused ground-truth dataset evaluators |
| [docs/graphify.md](../graphify.md) | Pinned Graphify `0.9.26` setup, update, and check workflow |
| [docs/codebase/mental-model.md](mental-model.md) | What the engine is/is not, runtime split, codebase compass |
| [docs/codebase/repository-map.md](repository-map.md) | Dependency rule, package ownership, golden placement rule |
| [docs/codebase/core-pipeline.md](core-pipeline.md) | `OcrToolbox`, providers, `PipelineConfig`, validation plugins, `confidence`, `RunTracer` |
| [docs/codebase/api-and-auth.md](api-and-auth.md) | FastAPI composition, routes, layered auth, rate limits, `RunRepository`, Supabase schema |
| [docs/codebase/adapters-and-web.md](adapters-and-web.md) | CLI tools, MCP server/client/verifier, Next.js 15 routes and auth gates |
| [docs/codebase/maintainer-playbook.md](maintainer-playbook.md) | PR review path, hard questions, warning signs, ownership routing |

## Centralized Agent Skills

| Skill | Focus |
|---|---|
| [skills/catalog.md](../../skills/catalog.md) | Short index of all repository skills |
| [skills/architecture-guardrails/SKILL.md](../../skills/architecture-guardrails/SKILL.md) | Dependency direction, pure core, HTTP-only MCP, server-side enforcement |
| [skills/docs-alignment/SKILL.md](../../skills/docs-alignment/SKILL.md) | Living doc accuracy, `DOCS.md` authority, link checks, Graphify sync |
| [skills/commit-hygiene/SKILL.md](../../skills/commit-hygiene/SKILL.md) | `development`-based branching, `--ff-only`, conventional commits, excluded paths |
| [skills/testing-coverage/SKILL.md](../../skills/testing-coverage/SKILL.md) | Focused vs full `pytest`, web lint/test/build, smoke verification |
| [skills/project-structure/SKILL.md](../../skills/project-structure/SKILL.md) | Where new modules, routes, components, migrations, and docs belong |
| [skills/ocr-run-lifecycle/SKILL.md](../../skills/ocr-run-lifecycle/SKILL.md) | 7-phase run flow, `RunContext.create_run`, `RunTracer.step`, `PipelineConfig` |
| [skills/api-error-envelope/SKILL.md](../../skills/api-error-envelope/SKILL.md) | `error_response`, `engine_error_response`, middleware `JSONResponse` envelopes |
| [skills/api-key-auth/SKILL.md](../../skills/api-key-auth/SKILL.md) | `ocr_live_<64 hex>` keys, caches, invalidation, Supabase JWT layers |

## Scripts and Operational Files

| File | Purpose |
|---|---|
| `Dockerfile` | Multi-service Cloud Run container (`OCR_SERVICE=api\|mcp`) |
| `cloudbuild.yaml` | Cloud Build CD on push to `main` (swaps images + smoke tests) |
| `mcp_server.py` | Repo-root stdio wrapper delegating to `ocr_engine_mcp.server:run` |
| `scripts/deploy_cloudrun.sh` | Provisions Artifact Registry, GCS bucket, secrets, and deploys `ocr-api` + `ocr-mcp` |
| `scripts/serve.sh` | Local production-mode background supervisor (`api`, `mcp`, optional Cloudflare tunnel) |
| `scripts/create_admin_user.py` | Creates or promotes a Supabase Auth admin account (`app_metadata.role='admin'`) |
| `scripts/issue_api_key.py` | Provisions tester account and writes an `ocr_live_` key to `--output` (`chmod 600`) |
| `scripts/smoke_async_api.py` | End-to-end async HTTP API smoke test |
| `scripts/smoke_async_mcp.py` | End-to-end async MCP smoke test |
| `scripts/setup-graphify`, `scripts/graphify-update`, `scripts/graphify-check`, `scripts/graphify_check.py` | Pinned Graphify installation, update, and integrity checks |

## Key Source & Test Landmarks

| Area | Primary files | Test suite |
|---|---|---|
| Core engine | `packages/core-engine/src/ocr_engine_core/` (`toolbox.py`, `pipeline.py`, `config/pipeline_config.py`, `providers/`, `validation/`, `artifacts.py`, `tracing.py`, `types.py`, `exceptions.py`) | `tests/test_core_contracts.py`, `tests/test_toolbox.py`, `tests/test_validation_confidence.py`, `tests/test_provider_http_base.py`, `tests/test_grid_removal.py`, `tests/test_phase1_robustness.py`, `tests/test_phase2_quality.py` |
| HTTP API | `packages/api/src/ocr_engine_api/` (`main.py`, `settings.py`, `routes/`, `auth*.py`, `rate_limit.py`, `errors.py`, `responses.py`, `services/`) | `tests/test_api.py`, `tests/test_auth.py`, `tests/test_admin_api.py`, `tests/test_run_repository.py`, `tests/test_hardening.py`, `tests/test_phase3_api_mcp_hardening.py`, `tests/test_phase3_cleanup.py` |
| CLI | `packages/cli/src/ocr_engine_cli/` (`run_pipeline.py`, `run_dataset.py`, `binarize_image.py`, `cv_progressive_score.py`) | Covered via core contracts & CLI `--help` / smoke checks |
| MCP | `packages/mcp/src/ocr_engine_mcp/` (`server.py`, `tools.py`, `client.py`, `auth.py`) | `tests/test_mcp_client.py`, `tests/test_mcp_auth.py`, `tests/test_phase3_api_mcp_hardening.py` |
| Web | `packages/web/src/` (`app/`, `components/`, `lib/`, `middleware.ts`) | `packages/web/tests/web-logic.test.ts` + ESLint + `next build` |
| Database | `supabase/migrations/*.sql` (9 versioned migrations) | Verified against API auth/admin/rate-limit integration contracts |

---

[← Previous: Maintainer Playbook](maintainer-playbook.md) | [← Codebase Guide](../CODEBASE-GUIDE.md)
