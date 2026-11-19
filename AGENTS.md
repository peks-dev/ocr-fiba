# FIBA OCR Engine — AGENTS.md

Cross-cutting instructions for AI agents working in `ocr-engine`. Before editing inside a package, also read `packages/<pkg>/AGENTS.md` and [`docs/CODEBASE-GUIDE.md`](docs/CODEBASE-GUIDE.md).

## Non-Negotiable Guardrails

1. **Hard dependency direction:**
   - `ocr_engine_core` **NEVER** imports `ocr_engine_api`, `ocr_engine_cli`, `ocr_engine_mcp`, FastAPI, or Supabase.
   - `ocr_engine_mcp` **NEVER** imports `ocr_engine_core`, `ocr_engine_api`, or `ocr_engine_cli` (HTTP client only via `OcrApiClient`).
   - `ocr_engine_api` **NEVER** imports `ocr_engine_cli` or `ocr_engine_mcp`.
2. **Trunk-based Git workflow:** Never commit directly to `main` or `development`. Branch from `development` (`<prefix>/<area>-<slug>`), keep atomic conventional commits (`<type>(<scope>): <description>`), and merge back with `--ff-only` (see [`CONTRIBUTING.md`](CONTRIBUTING.md)). Commit only with explicit user authorization.
3. **Never commit runtime or local state:** Exclude `runs/`, `outputs/`, `dataset/results*`, `.env*` (except `.env*.example`), `.server/`, `.server-token`, `.cloud-token`, `.cloud-image`, `.venv/`, `.graphify-venv/`, `node_modules/`, `.next/`, `.codex/`, `.devin/`, `.agents/`.
4. **Canonical contracts live in [`DOCS.md`](DOCS.md):** Document verified current behavior, never duplicate full API/env/schema tables elsewhere, and keep sibling surfaces in [Documentation Authority](DOCS.md#documentation-authority) aligned.

## Autonomous Pre-Completion Gate

Before reporting **any** task that changes code, config, migrations, scripts, or contracts as done — **without waiting for the user to ask**:

1. **Sync contracts & docs:** Check [Documentation Authority](DOCS.md#documentation-authority) and follow [`skills/docs-alignment/SKILL.md`](skills/docs-alignment/SKILL.md) whenever routes, MCP tools, CLI flags, env vars, `PipelineConfig`, providers, plugins, migrations, or deploy scripts changed; update `DOCS.md` and affected sibling surfaces in the same change.
2. **Run verification:** Run applicable tests (`uv run pytest -q`, which enforces relative Markdown links via `tests/test_docs_links.py`) and `packages/web` lint/test/build when frontend files changed.
3. **Update Graphify:** Run `./scripts/graphify-update` and `./scripts/graphify-check` (`$graphify . --update` when documentation semantics changed) and inspect `git diff -- graphify-out/`.

## Graphify (Required Repository Knowledge)

Graphify `0.9.26` is required (see [`docs/graphify.md`](docs/graphify.md)); canonical outputs live in `graphify-out/`.

- Start architecture, dependency, or impact work with `graphify query`, `graphify path`, or `graphify explain`, then verify against source files.
- Never edit `graphify-out/` manually, never install Graphify Git hooks, and never auto-stage/commit.

## Engram (Shared Technical Memory)

- Engram is available only when opened through its local MCP server. Before saving, run `mem_current_project` and confirm `ocr-engine`.
- Save architectural decisions, bugs, configurations, and discoveries; never store secrets or personal notes.
- `.engram/` is an explicit exception for Git Sync: version only sync artifacts under `.engram/`, never `~/.engram/engram.db`.

## Repository Skills (`skills/`)

Load matching skills **before** writing code or docs (full list: [`skills/catalog.md`](skills/catalog.md)):

| Skill | Trigger | Path |
|---|---|---|
| `architecture-guardrails` | Package boundaries, imports, auth/trust boundaries | [`skills/architecture-guardrails/SKILL.md`](skills/architecture-guardrails/SKILL.md) |
| `docs-alignment` | Changes affecting endpoints, tools, CLI flags, env vars, or docs | [`skills/docs-alignment/SKILL.md`](skills/docs-alignment/SKILL.md) |
| `commit-hygiene` | Branch creation, staging, commits, or merging into `development` | [`skills/commit-hygiene/SKILL.md`](skills/commit-hygiene/SKILL.md) |
| `testing-coverage` | Implementing behavior changes or verifying before merge | [`skills/testing-coverage/SKILL.md`](skills/testing-coverage/SKILL.md) |
| `project-structure` | Creating new modules, routes, pages, migrations, or scripts | [`skills/project-structure/SKILL.md`](skills/project-structure/SKILL.md) |
| `ocr-run-lifecycle` | Pipeline phases, `RunContext`/`ArtifactStore`, `PipelineConfig` | [`skills/ocr-run-lifecycle/SKILL.md`](skills/ocr-run-lifecycle/SKILL.md) |
| `api-error-envelope` | FastAPI error responses or `OcrEngineError` HTTP translation | [`skills/api-error-envelope/SKILL.md`](skills/api-error-envelope/SKILL.md) |
| `api-key-auth` | `ocr_live_` keys, `api_key_auth` middleware, `/v1/me`, `/v1/admin`, JWT auth | [`skills/api-key-auth/SKILL.md`](skills/api-key-auth/SKILL.md) |

## Stack & External Skills

When installed in your agent environment, also load stack skills on matching work:
- **Next.js / React (`packages/web`):** `next-best-practices` + `vercel-react-best-practices`; `react-performance-optimization` for performance; `design-tailwind-system` for Tailwind tokens; `design-motion-animation` + `library-gsap-*` for motion.
- **Python optimization:** `python-codebase-optimization`.
- **Pre-completion security check:** `audit-security-implementation`.
- **Tooling & research:** `git-commit-creation`, `sys-config-context`, `agent-skill-creation`, `obsidian-core`, `research-core`.

## Quick Pointers

- Technical reference & authority: [`DOCS.md`](DOCS.md)
- Codebase ownership & flows: [`docs/CODEBASE-GUIDE.md`](docs/CODEBASE-GUIDE.md) · [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- Git, verification & conventions: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Per-package stubs: `packages/core-engine/AGENTS.md`, `packages/api/AGENTS.md`, `packages/cli/AGENTS.md`, `packages/mcp/AGENTS.md`, `packages/web/AGENTS.md`
