[← Codebase Guide](../CODEBASE-GUIDE.md) | [← Previous: Adapters & Web](adapters-and-web.md) | [Next: Reference Map →](reference-map.md)

# Maintainer Playbook

**Use this page when reviewing changes, planning cross-package features, or verifying that code, boundaries, tests, and docs still align.**

## Main product capabilities

| Capability | What it does | Where it lives |
|---|---|---|
| Scoresheet pipeline | 7-phase isolation, cropping, enhancement, extraction, normalization, validation | `packages/core-engine/` (`OcrToolbox`, `FibaOcrPipeline`) |
| Multi-provider extraction | Uniform `ModelProvider` + `HttpJsonProvider` retry/backoff across 6 providers | `packages/core-engine/.../providers/` |
| Validation & confidence | 13 plugins (11 default core, 2 opt-in FIBA rules) + weighted section confidence | `packages/core-engine/.../validation/` |
| Run auditability | Canonical `runs/<run_id>/` layout (`input/`, `artifacts/`, `raw/`, `trace.json`, `result.json`) | `packages/core-engine/` (`types.py`, `artifacts.py`, `tracing.py`) |
| HTTP run API | Async execution (`ThreadPoolExecutor`), `RunRepository`, stale-run recovery, sanitization | `packages/api/` (`routes/runs.py`, `services/`) |
| Layered auth & quotas | Static bearer fallback, `ocr_live_` SHA-256 keys, Supabase JWTs, advisory-locked RPC limits | `packages/api/` (`auth*.py`, `rate_limit.py`), `supabase/migrations/` |
| CLI tools | Local `ocr-run`, batch `ocr-dataset`, `ocr-binarize`, `ocr-progressive-score` | `packages/cli/` |
| MCP server | 10 tools, 4 JSON resources, 3 prompts over stdio or HTTP (`McpTokenVerifier`) | `packages/mcp/` |
| Web console & demos | Admin invites & API keys, `/test/{player,referee,club}` demos, Airtable league proxy | `packages/web/` |
| Dataset evaluation | Full-sheet and 6 focused metric scripts against `dataset/` ground truth | `evaluation/` |
| Cloud Run & Vercel ops | Single multi-service Docker image, Cloud Build CD, Vercel web deploy | `Dockerfile`, `cloudbuild.yaml`, `scripts/deploy_cloudrun.sh` |

---

## PR Review Path

```text
1. Which package(s) own the behavior? (Check Repository Map)
2. Are hard dependency boundaries intact? (core pure; MCP HTTP-only)
3. Is auth/policy enforced on the server/DB, not only in UI or client code?
4. Are errors shaped via error_response / engine_error_response / handle_api_error?
5. Are production responses sanitized and secrets excluded from logs/client storage?
6. Do unit/contract tests cover the affected boundary?
7. Did DOCS.md, domain docs, and Graphify stay synchronized with shipped behavior?
```

---

## Maintainer Hard Questions

Before approving any non-trivial change, ask:

1. **Did domain logic leak outward or adapter logic leak inward?** (`ocr_engine_core` must stay pure; `ocr_engine_mcp` must stay an HTTP client).
2. **Where is the permission enforced?** Tester/admin checks must live in Next.js server layouts/routes (`requireAdminAccount`, `requireDemoAccess`, `authorizeDemoApiAccess`), FastAPI auth/dependencies, and Supabase RLS/`raw_app_meta_data` — never only in client components.
3. **What happens in `OCR_ENV=production`?** Does `resolve_runs_dir` override `runs_dir`, does `sanitize_for_public_response` strip paths, is path input disabled (`OCR_ALLOW_PATH_INPUT=false`, `MCP_ALLOW_PATH_INPUT=false`), and do rate limits fail closed (`503`)?
4. **Can a secret leak?** Raw `ocr_live_` keys must only leave the API once at creation, never enter `public.api_keys`, logs, or `localStorage`, and key deletions must call `invalidate_api_key_cache`.
5. **Do docs match code and tests?** Check [DOCS.md § Documentation Authority](../../DOCS.md#documentation-authority) for which sibling files must change together.

---

## Warning Signs

| Smell | Probable problem | Expected correction |
|---|---|---|
| `from ocr_engine_api` or `from ocr_engine_mcp` inside `core-engine` | Inverted dependency boundary | Keep domain types/logic in `core-engine`; map in `api` or `mcp`. |
| `from ocr_engine_core` inside `packages/mcp` | Bypassing API boundary | Route through `OcrApiClient` and HTTP endpoints. |
| Raw `HTTPException(status_code=..., detail="...")` in `packages/api` | Breaks client error contract | Replace with `error_response` or `engine_error_response`. |
| New `runs/<run_id>/` file read by `api`/`mcp` outside `artifacts/` or root JSONs | Layout drift | Register via `ArtifactStore` / `RunContext` and update `RunRepository` + `skills/ocr-run-lifecycle/`. |
| Reading `raw_user_meta_data ->> 'role'` in SQL or client claims | Privilege escalation vector | Read `role` exclusively from `raw_app_meta_data` and `public.accounts`. |
| `NEXT_PUBLIC_` prefix on `SUPABASE_SERVICE_KEY` or `AIRTABLE_TOKEN` | Secret leaked to browser bundle | Keep server-only env vars without `NEXT_PUBLIC_` and proxy through Server Components/API routes. |
| `useEffect` depending on `session` object in `packages/web` | Infinite re-fetch loop | Fetch once on mount and refresh explicitly on user mutations. |
| `DELETE /v1/me/api-keys/{id}` without `invalidate_api_key_cache` | Deleted key accepted for up to 60s | Call `invalidate_api_key_cache(account_id=...)`. |
| Duplicating full endpoint/env tables outside `DOCS.md` | Documentation drift | Keep canonical table in `DOCS.md` and link to it. |
| Modified code/docs without updating `graphify-out/` | Stale knowledge graph | Run `./scripts/graphify-update` and `./scripts/graphify-check`. |

---

## Quick Ownership Decision

```text
Pipeline step, provider, validation plugin, confidence, trace  -> packages/core-engine
HTTP route, auth middleware, rate limit, RunRepository         -> packages/api
Local CLI command or batch dataset runner                      -> packages/cli
MCP tool, resource, prompt, or bearer verifier                 -> packages/mcp
Web route, auth gate, React component, Airtable proxy          -> packages/web
Table, constraint, RLS policy, trigger, or Postgres RPC        -> supabase/migrations
Accuracy benchmark script                                      -> evaluation
Deploy, local daemon, provisioning, smoke, or Graphify script  -> scripts
```

---

[← Previous: Adapters & Web](adapters-and-web.md) | [Next: Reference Map →](reference-map.md)
