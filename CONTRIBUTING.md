[← Back to README](README.md)

# Contributing to FIBA OCR Engine

**This repository uses a trunk-based Git workflow, strict package boundaries, versioned Graphify knowledge graphs, and modular agent skills.**

---

## 1. Git Workflow

### Protected Branches

| Branch | Purpose | Direct commits? |
|---|---|---|
| `main` | Stable production snapshots (triggers Cloud Build CD on push). | Prohibited |
| `development` | Active integration branch (default merge target). | Prohibited |
| `<prefix>/<area>-<short-slug>` | Short-lived working branches created from `development`. | Allowed |

### Lifecycle of a Change

```text
development ──switch -c──► <prefix>/<area>-<slug>
                                  │
                                  ▼
                           atomic commits
                                  │
                                  ▼
                 tests + lint + Graphify update/check
                                  │
                                  ▼
             merge into development with --ff-only
                                  │
                                  ▼
                 git branch -d <prefix>/<area>-<slug>
```

Example:

```bash
git switch -c feat/web-single-player-demo development
# ... make atomic commits ...
git switch development
git merge --ff-only feat/web-single-player-demo
git branch -d feat/web-single-player-demo
```

If `development` moved ahead while you worked, rebase your branch onto `development` instead of creating a merge commit:

```bash
git rebase development
```

Never rewrite published history (`main` or `development`).

### Branch Naming

```text
<prefix>/<area>-<short-slug>
```

- **Prefixes:** `feat`, `fix`, `chore`, `docs`, `refactor`, `test`
- **Areas:** `core`, `api`, `cli`, `mcp`, `web`, `supabase`, `repo`

### Commit Format

```text
<type>(<scope>[,<scope>...]): <imperative description>
```

- **Types:** `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `style`, `ci`
- **Scopes:** `core`, `api`, `cli`, `mcp`, `web`, `supabase`, `repo` (comma-separated when spanning multiple packages)
- **Atomicity:** One commit = one logical change. Never mix a refactor with a feature. Stage explicitly by file path (`git add <paths>`) or `git add -p`, and inspect `git diff --staged` before committing.

Examples:

```text
feat(api,supabase): add Supabase auth, API keys, and /v1/me/* endpoints
fix(web): guard referee league route with demo access check
docs(repo): align DOCS.md and codebase guides with current routes
```

---

## 2. Out-of-Scope / Never Commit Artifacts

Never commit runtime outputs, credentials, caches, or local agent state:

- `runs/`, `outputs/`, `dataset/results*`
- `.env`, `.env.local`, `.server/`, `.server-token`, `.cloud-token`, `.cloud-image`
- `.venv/`, `.graphify-venv/`, `__pycache__/`, `.pytest_cache/`, `node_modules/`, `.next/`
- `.codex/`, `.devin/`, `.agents/`
- `~/.engram/engram.db` (for Engram Git sync, version only `.engram/` sync artifacts, never the local SQLite file)

---

## 3. Coding Conventions

### Python (`core-engine`, `api`, `cli`, `mcp`)
- Start public modules with `from __future__ import annotations`.
- Type public functions and schemas (`@dataclass` in `ocr_engine_core`; Pydantic models in `ocr_engine_api.schemas`).
- Raise `OcrEngineError` subclasses inside `ocr_engine_core`; translate in `ocr_engine_api` via `error_response` / `engine_error_response`.
- Preserve hard dependency direction: `core-engine` never imports `api`/`cli`/`mcp`; `mcp` never imports `core-engine`/`api`/`cli`.

### Next.js (`packages/web`)
- App Router (`src/app/`) only; Server Components by default (`'use client'` only for state/effects/browser APIs).
- Supabase access strictly via `src/lib/supabase/{server,client,admin,middleware}.ts`.
- Auth gates live in layouts (`requireAdminAccount()`, `requireDemoAccess()`, `requireCurrentUserAccount()`) and `authorizeDemoApiAccess()`.

---

## 4. Verification Before Merge

Run the suites relevant to the packages you touched (and the full suite before merging to `development`):

| Scope | Command |
|---|---|
| Full Python workspace (`core`, `api`, `cli`, `mcp`) | `uv run pytest -q` |
| Web lint, unit tests, production build | `npm --prefix packages/web run lint && npm --prefix packages/web test && npm --prefix packages/web run build` |
| End-to-end API smoke (requires running `ocr-api` + provider key) | `python scripts/smoke_async_api.py --image <path>` |
| End-to-end MCP smoke (requires running `ocr-api` + `ocr-mcp`) | `python scripts/smoke_async_mcp.py --image <path>` |

Report only commands actually executed after your final edit.

---

## 5. Graphify Workflow (Required)

Graphify `0.9.26` is pinned in this repository (see [docs/graphify.md](docs/graphify.md)).

1. Start architecture, dependency, or impact analysis with `graphify query`, `graphify path`, or `graphify explain`, then verify against source files.
2. After any logical change to code, tests, scripts, or architecture docs:
   ```bash
   ./scripts/graphify-update
   ./scripts/graphify-check
   git diff -- graphify-out/ .graphifyignore
   ```
3. Run `$graphify . --update` for semantic documentation changes.
4. Never edit `graphify-out/` manually and never install Graphify git hooks.

---

## 6. Skill Authoring Standard

Repository agent skills live under [`skills/`](skills/catalog.md). Every skill follows a **hybrid format**:

1. **Structured base:** YAML frontmatter (`name`, `description` with explicit `Trigger:`), *When to Use*, *Critical Rules*, and *Verification Checklist*.
2. **Cookbook section:** Concrete `If / Then / Example` snippets for repetitive flows.

Keep `AGENTS.md` (root and package stubs) lightweight — put reusable workflows and checklists into `skills/` and architecture explanations into `docs/codebase/`.

---

[← Back to README](README.md) · [Codebase Guide →](docs/CODEBASE-GUIDE.md)
