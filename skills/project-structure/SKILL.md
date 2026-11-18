---
name: project-structure
description: >
  Where files, modules, schemas, migrations, scripts, tests, and documentation belong
  in the ocr-engine monorepo.
  Trigger: Creating new files, packages, endpoints, CLI scripts, Next.js pages, migrations, or docs.
version: 1.0.0
---

# Project Structure

Placement rules to prevent responsibility drift across `ocr-engine`.

## When to Use

- Deciding which package or directory should own a new file
- Creating new FastAPI routes, `OcrToolbox` methods, CLI scripts, Next.js pages, SQL migrations, or docs

---

## Placement Rules

| What you are creating | Where it goes |
|---|---|
| Pipeline step, provider, prompt, schema, validator | `packages/core-engine/src/ocr_engine_core/` |
| FastAPI route, Pydantic schema, auth/rate-limit, `RunRepository` | `packages/api/src/ocr_engine_api/` |
| Console script entrypoint (`[project.scripts]`) | `packages/cli/src/ocr_engine_cli/` + `packages/cli/pyproject.toml` |
| MCP tool, resource, prompt, `OcrApiClient` method | `packages/mcp/src/ocr_engine_mcp/` |
| Next.js App Router page/layout/API route or component | `packages/web/src/app/` or `packages/web/src/components/` |
| Browser/server Supabase or API helper | `packages/web/src/lib/` |
| Postgres table, RLS policy, trigger, or RPC | `supabase/migrations/<timestamp>_<slug>.sql` |
| Dataset accuracy script | `evaluation/evaluate_<domain>.py` |
| Ops, deploy, provisioning, or smoke script | `scripts/` |
| Python unit/contract tests | `tests/test_<area>.py` |
| Web unit tests | `packages/web/tests/` |
| Repository agent skills | `skills/<name>/SKILL.md` + `skills/catalog.md` |
| Technical reference / guides | `DOCS.md` or `docs/` |

---

## Critical Rules

1. **Put behavior near its domain, not its caller:** Shared CV/OCR helpers belong in `ocr_engine_core`, not inside `packages/cli` or `packages/api`.
2. **Never create `pages/` in `packages/web`:** App Router (`src/app/`) only.
3. **Never write runtime outputs inside `packages/`:** Runs belong in `runs/` (or caller-supplied output dirs), never inside package source trees.
4. **Keep package `AGENTS.md` files as lightweight stubs:** Detailed patterns live in `docs/codebase/*.md`; reusable instructions live in `skills/`.

---

## Verification Checklist

- [ ] New file placed in its owning package per [docs/codebase/repository-map.md](../../docs/codebase/repository-map.md).
- [ ] Corresponding package `pyproject.toml`, `DOCS.md`, or `skills/catalog.md` updated if a public surface was added.
- [ ] No utility dumping grounds or cross-layer duplicates introduced.
