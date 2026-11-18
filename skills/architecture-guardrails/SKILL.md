---
name: architecture-guardrails
description: >
  Cross-package architectural boundaries and ownership rules for ocr-engine.
  Trigger: Any change affecting package dependencies, cross-package contracts,
  security/auth boundaries, or where new domain logic lives.
version: 1.0.0
---

# Architecture Guardrails

Protects the monorepo's core invariant: **`ocr_engine_core` is pure domain logic; `api`, `cli`, `mcp`, and `web` are thin adapters around the canonical run.**

## When to Use

- Adding or refactoring features spanning multiple packages
- Creating new imports between `packages/*`
- Modifying authentication, authorization, or API/MCP/Web trust boundaries
- Adding pipeline orchestration or run persistence logic

---

## Critical Rules

1. **Enforce strict inward dependencies:**
   - `ocr_engine_core` **NEVER** imports `ocr_engine_api`, `ocr_engine_cli`, `ocr_engine_mcp`, FastAPI, or Supabase.
   - `ocr_engine_mcp` **NEVER** imports `ocr_engine_core`, `ocr_engine_api`, or `ocr_engine_cli` (HTTP client only via `OcrApiClient`).
   - `ocr_engine_api` **NEVER** imports `ocr_engine_cli` or `ocr_engine_mcp`.
2. **Never simulate policy only in UI/client code:** Admin roles (`public.accounts.role == 'admin'`), active account status, demo assignment (`assigned_demo`), and rate limits MUST be enforced on the server (`packages/api`, Next.js server layouts/routes, and Supabase RLS/`raw_app_meta_data`).
3. **Preserve canonical run ownership:** Run files live on disk under `OCR_RUNS_DIR` (`runs/<run_id>/`) managed by `RunContext` (`core-engine`) and `RunRepository` (`api`). Never read `runs/` directly from `mcp` or `web`.
4. **Sanitize external boundaries:** Production API responses pass through `sanitize_for_public_response`; API errors use `error_response`/`engine_error_response`; MCP errors pass through `handle_api_error`.

---

## Cookbook: Decision Routing

- **Need image isolation, cropping, extraction, prompts, or validation?** -> Put it in `packages/core-engine`, expose through `OcrToolbox`, and wrap in `RunTracer.step(...)`.
- **Need an HTTP route, upload validation, rate limit, or run lookup?** -> Put it in `packages/api` using `settings.py` and `RunRepository`.
- **Need an agent tool or resource?** -> Add a typed method to `OcrApiClient` and wrap it in `packages/mcp` `tools.py` + `server.py`.
- **Need an admin or tester flow?** -> Gate the layout/API route in `packages/web` with `requireAdminAccount()` / `requireDemoAccess()` / `authorizeDemoApiAccess()`.

---

## Verification Checklist

- [ ] No forbidden cross-package imports added (`rg "ocr_engine_(api|cli|mcp)" packages/core-engine/` and `rg "ocr_engine_(core|api|cli)" packages/mcp/` return empty).
- [ ] Security/permission checks enforced server-side, not only client-side.
- [ ] Boundaries documented in [docs/codebase/repository-map.md](../../docs/codebase/repository-map.md) remain intact.
