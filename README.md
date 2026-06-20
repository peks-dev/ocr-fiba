# FIBA OCR Engine

Monorepo for the FIBA scoresheet OCR engine. Extracts structured basketball game data from score sheet images and exposes the pipeline through an HTTP API, a CLI, an MCP server, and a Next.js web app.

> **AI agents**: read [`AGENTS.md`](./AGENTS.md) instead — it contains the same project knowledge plus machine-actionable conventions, scopes, and auto-invoke skills.

## Repository layout

```text
.
├── packages/
│   ├── core-engine/   # OCR domain library: pipeline, providers, schemas, validation
│   ├── api/           # FastAPI HTTP adapter (depends on core-engine)
│   ├── cli/           # Command-line tools (depends on core-engine)
│   ├── mcp/           # MCP server adapter (talks to the API over HTTP)
│   └── web/           # Next.js 15 web app (Supabase auth, admin, tester demos)
├── supabase/          # Versioned SQL migrations
├── scripts/           # Smoke tests and ops utilities
├── runs/              # Runtime output (gitignored, not in packages)
├── outputs/           # Local OCR outputs (gitignored)
└── dataset/           # Test datasets
```

### Dependency direction

```text
ocr-engine-core  ←  ocr-engine-api  ←  ocr-engine-mcp
ocr-engine-core  ←  ocr-engine-cli
ocr-engine-web   (independent; talks to the API over HTTP)
```

Hard rule: `ocr_engine_core` must **never** import `ocr_engine_api`, `ocr_engine_cli`, or `ocr_engine_mcp`. The core stays pure.

## Per-package documentation

- MCP server: [`packages/mcp/docs/mcp-server.md`](./packages/mcp/docs/mcp-server.md)
- Other packages: each has its own `AGENTS.md` for AI-agent context.

## Quickstart (local development)

### Prerequisites

- Python ≥ 3.12
- [`uv`](https://docs.astral.sh/uv/) (workspace manager)
- Node.js ≥ 20 (only for `packages/web`)

### Environment

Copy `.env.example` to `.env` and fill in what you need:

```bash
cp .env.example .env
```

At minimum for OCR runs:

```bash
# At least one provider key
OPENROUTER_API_KEY=...
# Local API auth fallback (development)
OCR_ENGINE_API_KEY=dev-local-token
OCR_ENV=development
OCR_RUNS_DIR=runs
OCR_MAX_UPLOAD_MB=20
```

For the Supabase-backed web app, also set:

```bash
SUPABASE_URL=...
SUPABASE_SERVICE_KEY=...
SUPABASE_PUBLISHABLE_KEY=...
SUPABASE_JWT_SECRET=...
```

### Install

```bash
uv sync
```

### Run the API

```bash
ocr-api
# → http://127.0.0.1:8000
```

### Run a CLI OCR job

```bash
ocr-run --image path/to/score-sheet.jpg
```

### Run the MCP server (stdio)

```bash
python mcp_server.py
```

Or as HTTP:

```bash
MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=8001 \
  python -m adapters.mcp.server
```

### Run the web app

```bash
cd packages/web
npm install
npm run dev
# → http://localhost:3000
```

### Run the test suite

```bash
PYTHONPATH=packages/core-engine/src:packages/api/src:packages/cli/src:packages/mcp/src \
  python -m unittest discover -s tests -p 'test_*.py'
```

## Git workflow

This repository uses a **trunk-based** model with short-lived feature branches and fast-forward merges.

### Branches

| Branch | Purpose | Direct commits? |
|---|---|---|
| `main` | Stable, production-ready snapshots. | ❌ Prohibited |
| `development` | Active integration branch. The default target for merges. | ❌ Prohibited |
| `feat/*`, `fix/*`, `chore/*`, `docs/*`, `refactor/*`, `test/*` | Short-lived working branches. | ✅ |

### Lifecycle of a change

```text
development ──switch -c─→ feat/<area>-<slug>
                              │
                              ▼
                       commits atómicos
                              │
                              ▼
                    lint + tests + smoke
                              │
                              ▼
            merge a development con --ff-only
                              │
                              ▼
                    git branch -d feat/<area>-<slug>
```

Example:

```bash
git switch -c feat/web-single-player-demo development
# … work, atomic commits …
git switch development
git merge --ff-only feat/web-single-player-demo
git branch -d feat/web-single-player-demo
```

### Branch naming

```text
<prefix>/<area>-<short-slug>
```

Prefixes: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`.
Areas: `core`, `api`, `cli`, `mcp`, `web`, `supabase`, `repo`.

Examples:

- `feat/web-single-player-demo`
- `fix/mcp-timeout-on-large-image`
- `docs/api-runs-endpoint`
- `chore/repo-bump-deps`

### Commit messages

Format: `<type>(<scope>): <imperative description>`

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `style`, `ci`.
Scopes: `core`, `api`, `cli`, `mcp`, `web`, `supabase`, `repo`.

Multiple scopes are allowed when a change spans packages:

```text
feat(api,supabase): add account creation trigger
refactor(core,api): extract pipeline options
```

### Releases and tags

Not used yet. We will adopt semantic versioning (`vMAJOR.MINOR.PATCH`) and git tags only when the engine ships to real production users. Until then, `main` is just the most recent stable snapshot.

### Rules of thumb

- One commit = one logical change. Never mix a refactor with a new feature.
- Run `git diff` and `git diff --staged` before every commit. Avoid `git add .` without reviewing.
- Never rewrite published history (no force-push to `main` or `development`).
- If a branch is no longer fast-forwardable, rebase it onto `development` instead of merging `development` into it.

## Contributing

- Read the relevant `packages/<x>/AGENTS.md` before modifying a package.
- AI agents should load `AGENTS.md` (root) and the target package's `AGENTS.md` before writing code.
- Run the test suite and any package-specific smoke scripts (`scripts/smoke_async_api.py`, `scripts/smoke_async_mcp.py`) before opening a merge.

## License

TBD.
