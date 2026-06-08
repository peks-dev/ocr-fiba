# FIBA OCR Engine — AGENTS.md

> **Human contributors** should read [`README.md`](./README.md) instead. This file is the equivalent for AI agents: machine-actionable conventions, scopes, and auto-invoke skills.

## How to use this file

1. Read this root `AGENTS.md` first — it establishes cross-cutting rules.
2. Read the target package's `AGENTS.md` (e.g. `packages/api/AGENTS.md`) before modifying code there.
3. Skills in `.agents/skills/` (and the bundled `agent-skill-creation` skill) override the generic patterns below when they conflict.
4. The human source of truth is `README.md`. If you find a contradiction, the `README.md` wins for product-level decisions; this file wins for operational conventions.

## Project summary

Monorepo that extracts structured basketball game data from FIBA score sheet images. The pipeline is exposed through a FastAPI HTTP API, a CLI, an MCP server adapter, and a Next.js dashboard. Authentication is Supabase-backed (with a static-bearer fallback for local dev).

## Stack

- **Language (engine + adapters):** Python ≥ 3.12
- **Workspace manager:** `uv` (Astral)
- **HTTP server:** FastAPI ≥ 0.115, uvicorn
- **OCR providers:** openrouter, docstrange, glm, gemini, interfaze, qubrid (all via `ocr_engine_core.providers`)
- **Validation:** `validation` engine with pluggable plugins
- **CLI entry points:** `ocr-api`, `ocr-run`, `ocr-dataset`, `ocr-binarize`, `ocr-progressive-score`, `ocr-mcp`
- **Web:** Next.js 15 (App Router) + React 19 + Tailwind CSS v4 + Supabase SSR
- **DB:** Supabase (Postgres) with versioned SQL migrations in `supabase/migrations/`
- **Tests:** `pytest` against the workspace's PYTHONPATH

## Environment setup

```bash
# one-time
uv sync

# required env (see .env.example for the full list)
export OCR_ENGINE_API_KEY=dev-local-token
export OCR_ENV=development
export OCR_RUNS_DIR=runs
export OCR_MAX_UPLOAD_MB=20
# at least one provider key
export OPENROUTER_API_KEY=...
```

When working in `packages/web`, also set:

```bash
export NEXT_PUBLIC_SUPABASE_URL=...
export NEXT_PUBLIC_SUPABASE_ANON_KEY=...
```

## Commands (verified to work)

| Action | Command |
|---|---|
| Install workspace | `uv sync` |
| Run API (dev) | `ocr-api` → `http://127.0.0.1:8000` |
| Run MCP server (stdio) | `python mcp_server.py` |
| Run MCP server (HTTP) | `MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=8001 python -m adapters.mcp.server` |
| Run web dev server | `cd packages/web && npm install && npm run dev` |
| Web lint | `cd packages/web && npm run lint` |
| Web build | `cd packages/web && npm run build` |
| Run all tests | `uv run pytest -q` (or the `python -m unittest` form documented in `README.md`) |
| Smoke API end-to-end | `python scripts/smoke_async_api.py --image <path>` |
| Smoke MCP end-to-end | `python scripts/smoke_async_mcp.py --image <path>` |

## Repository layout

```text
.
├── packages/
│   ├── core-engine/   # OCR domain library: pipeline, providers, schemas, validation, toolbox
│   ├── api/           # FastAPI HTTP adapter (depends on core-engine)
│   ├── cli/           # Command-line tools (depends on core-engine)
│   ├── mcp/           # MCP server adapter (talks to the API over HTTP)
│   └── web/           # Next.js 15 dashboard (Supabase auth + API key mgmt)
├── supabase/
│   └── migrations/    # Versioned SQL migrations (5 applied)
├── scripts/           # smoke_async_api.py, smoke_async_mcp.py
├── tests/             # unittest-style tests (run via pytest)
├── runs/, outputs/    # Runtime artifacts (gitignored, never inside packages/)
└── dataset/           # Test datasets
```

### Hard dependency rule

```text
ocr-engine-core  ←  ocr-engine-api  ←  ocr-engine-mcp
ocr-engine-core  ←  ocr-engine-cli
ocr-engine-web   (independent; talks to API over HTTP)
```

`ocr_engine_core` **must not** import `ocr_engine_api`, `ocr_engine_cli`, or `ocr_engine_mcp`. The core stays pure. This rule is enforced by the import direction in code reviews; there is no automated linter for it yet.

## Git workflow

This repo uses **trunk-based** with short-lived branches and fast-forward merges into `development`. Detailed policy is in `README.md` § Git workflow. The agent-facing summary is:

### Branching

- `main` and `development` are protected: **no direct commits**.
- Working branches: `feat/<area>-<slug>`, `fix/<area>-<slug>`, `chore/<area>-<slug>`, `docs/<area>-<slug>`, `refactor/<area>-<slug>`, `test/<area>-<slug>`.
- Always create from `development` and merge back with `--ff-only`:

```bash
git switch -c feat/web-single-player-demo development
# work, atomic commits
git switch development && git merge --ff-only feat/web-single-player-demo
git branch -d feat/web-single-player-demo
```

### Commit format

```text
<type>(<scope>[,<scope>...]): <imperative description>
```

- **Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `style`, `ci`
- **Scopes (valid areas):** `core`, `api`, `cli`, `mcp`, `web`, `supabase`, `repo`
- Multiple scopes allowed for cross-package changes.
- `repo` is for changes that don't belong to a single package (e.g. `pyproject.toml`, `uv.lock`, root scripts).

Examples seen in real history:

```text
feat(api,supabase): add Supabase auth, API keys, and /v1/me/* endpoints
feat(mcp): add async run tools
refactor(api,mcp): remove-legacy-sync
chore(repo): restructure docs into per-package layout and add root README
```

### Atomicity

- One commit = one logical change. Never mix a refactor with a feature.
- Stage with `git add -p` or by explicit file path. Avoid `git add .` without reviewing.

## Project conventions (must follow)

### Python

- All public modules use `from __future__ import annotations`.
- Type hints everywhere on public surfaces. Pydantic models for input/output schemas in `ocr_engine_api.schemas` and `ocr_engine_core.types`.
- Errors raised by the core engine extend `OcrEngineError` (see `ocr_engine_core.exceptions`). Convert them in the API layer via `errors.engine_error_response` to HTTP 422.
- Configuration objects use `@dataclass` (see `PipelineConfig` in `core-engine`).
- Provider implementations live in `ocr_engine_core/providers/` and must inherit from `providers.base.Provider`.

### FastAPI (api package)

- `create_app()` is the composition root in `ocr_engine_api/main.py`. Routes are mounted from `routes/` and registered conditionally based on `settings.has_supabase`.
- Auth is layered: `api_key_auth` middleware → optional Supabase JWT for `/v1/me/*` (handled inside `routes/me.py`).
- Standard error envelope: `error_response(status_code, code, message, retryable=False, details=None)`. Never return raw `HTTPException` to clients.
- Public responses are sanitized via `responses.sanitize_for_public_response` before leaving the API.

### Next.js (web package)

- App Router only (no `pages/`). RSC by default; mark `'use client'` only for components that need state/effects.
- All Supabase I/O goes through `lib/supabase/server.ts` (RSC) or `lib/supabase/client.ts` (browser). Never instantiate `createClient` directly in a component.
- Auth-gated routes live under `app/dashboard/*` and rely on the `dashboard/layout.tsx` redirect. The layout is the source of truth — don't re-check auth inside individual pages.
- UI feedback uses `sonner` toasts. Existing helpers: see `components/nav.tsx` for the `signOut` pattern.

### MCP

- The MCP server is an **HTTP client** of the API; it does not import the core. All OCR work happens server-side.
- Tools, resources, and prompts are defined in `ocr_engine_mcp/server.py`. Business logic for each tool is in `tools.py` and uses `OcrApiClient` from `client.py`.
- Error mapping uses `tools.handle_api_error` — never re-raise `OcrApiError` to MCP callers without translating it.

## Auto-invoke skills

When the request matches the action in the left column, load the skill in the right column **before** writing code.

| Action | Skill |
|---|---|
| Creating or editing FastAPI routes in `packages/api` | `next-best-practices` for web side; no first-party skill yet for FastAPI, follow conventions in this file |
| Creating/editing React/Next.js components in `packages/web` | `next-best-practices` + `vercel-react-best-practices` |
| Refactoring for performance in `packages/web` | `react-performance-optimization` |
| Working with Tailwind design tokens / system | `design-tailwind-system` |
| Adding motion to web UI | `design-motion-animation` + the appropriate `library-gsap-*` skill |
| Doing git operations (commit, branch, merge) | `git-commit-creation` |
| Before declaring a feature "done" (security check) | `audit-security-implementation` |
| Editing system configs / installing CLI tools | `sys-config-context` |
| Creating/updating skills | `agent-skill-creation` (the bundled one) |
| Obsidian note management | `obsidian-core` (load first per its rules) |
| Researching APIs/libraries | `research-core` (load first per its rules) |

## Available first-party skills (located in each package)

After Phase B, the following skills live inside this repo (see `packages/<x>/skills/SKILL.md`):

- `packages/core-engine/skills/ocr-run-lifecycle/SKILL.md` — how the canonical run layout, RunContext, and RunTracer work
- `packages/api/skills/api-error-envelope/SKILL.md` — how to emit a structured error from any route
- `packages/api/skills/api-key-auth/SKILL.md` — bearer API key flow including caching and Supabase fallback

These are the **only** SKILL.md files justified by repeated patterns (each appears in 3+ call sites in their domain). New SKILL.md files should not be created speculatively.

## Domains / packages

| Domain | Path | Owns |
|---|---|---|
| Core OCR engine | `packages/core-engine/` | Pipeline, providers, validation, schemas, tracing |
| HTTP API | `packages/api/` | FastAPI app, auth, runs, /v1/me/*, sanitization |
| CLI | `packages/cli/` | Local CLI entry points |
| MCP server | `packages/mcp/` | Tools, resources, prompts that wrap the API |
| Web dashboard | `packages/web/` | Next.js 15 app, Supabase auth, API key management |
| Database | `supabase/` | Versioned SQL migrations |

## Out of scope (do not touch)

- `runs/`, `outputs/`, `dataset/results/` — runtime artifacts, gitignored.
- `.venv/`, `__pycache__/`, `.pytest_cache/`, `node_modules/`, `.next/` — build/cache artifacts.
- `.engram/`, `.codex/`, `.devin/`, `.agents/` — local agent state, not part of the product.
