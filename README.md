# FIBA OCR Engine

Monorepo for extracting structured, validated basketball game data from FIBA scoresheet images. A pure-Python domain engine (`ocr-engine-core`) powers an async FastAPI HTTP service (`ocr-engine-api`), local CLI commands (`ocr-engine-cli`), an MCP server (`ocr-engine-mcp`), and a Next.js 15 web application (`packages/web`).

> **AI agents:** start with [`AGENTS.md`](./AGENTS.md) for non-negotiable guardrails and skill triggers, and [`docs/CODEBASE-GUIDE.md`](./docs/CODEBASE-GUIDE.md) for package ownership.

---

## How it fits together

```text
  Web App (packages/web)     MCP Server (packages/mcp)     CLI (packages/cli)
    Next.js 15 + Supabase      FastMCP (pure HTTP client)    ocr-run / ocr-dataset
           │                              │                          │
           └──────────── HTTPS ───────────┘                          │
                           │                                         │
                           ▼                                         │
                   HTTP API (packages/api)                           │
                     FastAPI · Auth · Rate limit                     │
                     Sanitization · RunRepository                    │
                           │                                         │
                           └──────────────────┬──────────────────────┘
                                              ▼
                               Core Engine (packages/core-engine)
                                 7-phase pipeline · ModelProviders
                                 13 validation plugins · Confidence
                                              │
                                              ▼
                               runs/<run_id>/ (canonical run layout)
```

> **Core stays pure:** `ocr_engine_core` never imports `ocr_engine_api`, `ocr_engine_cli`, or `ocr_engine_mcp`, and `ocr_engine_mcp` talks strictly to the API over HTTP.

---

## Packages

| Package / Area | Purpose | Docs |
|---|---|---|
| `packages/core-engine` | 7-phase OCR pipeline, `OcrToolbox`, 6 model providers, 13 validation plugins, `confidence`, `RunTracer`, `ArtifactStore` | [Core Pipeline](docs/codebase/core-pipeline.md) |
| `packages/api` | FastAPI service (`/v1/runs/*`, `/v1/me/*`, `/v1/admin/*`), layered auth, rate limiting, `RunRepository` | [API & Auth](docs/codebase/api-and-auth.md) |
| `packages/cli` | Local console scripts (`ocr-run`, `ocr-dataset`, `ocr-binarize`, `ocr-progressive-score`) | [Adapters & Web](docs/codebase/adapters-and-web.md#1-cli-packagescli-ocr_engine_cli) |
| `packages/mcp` | `FastMCP` server (stdio / Streamable HTTP) wrapping `ocr-engine-api` with 10 tools, 4 resources, and 3 prompts | [MCP Server](packages/mcp/docs/mcp-server.md) |
| `packages/web` | Next.js 15 App Router UI: Supabase login/invites, admin API key panel, `/test/{player,referee,club}` demos | [Web README](packages/web/README.md) |
| `supabase/` | 9 Postgres SQL migrations (`accounts`, `api_keys`, `admin_invitations`, RLS, `consume_rate_limit` RPC) | [DOCS.md § Supabase](DOCS.md#supabase-schema) |
| `evaluation/` | Full-sheet and focused ground-truth accuracy evaluators | [Evaluation Guide](docs/EVALUATION.md) |

---

## Get started (local development)

### Prerequisites

- Python `>= 3.12`
- [`uv`](https://docs.astral.sh/uv/)
- Node.js `>= 20` (for `packages/web`)

### 1. Install and configure

```bash
uv sync
cp .env.example .env
```

Set at least one provider key (e.g. `OPENROUTER_API_KEY`) and local API defaults in `.env`:

```bash
OPENROUTER_API_KEY=...
OCR_ENGINE_API_KEY=dev-local-token
OCR_ENV=development
OCR_RUNS_DIR=runs
OCR_MAX_UPLOAD_MB=20
```

For Supabase-backed endpoints (`/v1/me/*`, `/v1/admin/*`, `ocr_live_` keys) and `packages/web`, also configure `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_PUBLISHABLE_KEY`, and `SUPABASE_JWT_SECRET` (see [DOCS.md § Environment Variables](DOCS.md#environment-variables)).

### 2. Run services and tools

```bash
# HTTP API -> http://127.0.0.1:8000
ocr-api

# Single scoresheet via CLI (positional image argument)
ocr-run path/to/scoresheet.jpg --run-layout

# MCP server (stdio)
python mcp_server.py

# MCP server (Streamable HTTP -> http://127.0.0.1:8001/mcp)
MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=8001 uv run ocr-mcp

# Web app -> http://localhost:3000
cd packages/web && cp .env.local.example .env.local && npm install && npm run dev
```

### 3. Run verification suites

```bash
# Python workspace (core-engine, api, cli, mcp)
uv run pytest -q

# Web app (lint, unit tests, production build)
npm --prefix packages/web run lint
npm --prefix packages/web test
npm --prefix packages/web run build

# End-to-end smoke checks (requires running services + provider key)
python scripts/smoke_async_api.py --image path/to/scoresheet.jpg
python scripts/smoke_async_mcp.py --image path/to/scoresheet.jpg
```

---

## For AI agents

1. Read [`AGENTS.md`](./AGENTS.md) for cross-cutting guardrails, Graphify/Engram rules, and skill triggers.
2. Read the target package's `AGENTS.md` (`packages/<pkg>/AGENTS.md`) and load matching [`skills/`](skills/catalog.md) before writing code.
3. Consult [`docs/CODEBASE-GUIDE.md`](docs/CODEBASE-GUIDE.md) to confirm package ownership and [`DOCS.md`](DOCS.md) for canonical contracts.

---

## Documentation

| Where to go | What you'll find |
|---|---|
| **[Technical Reference (`DOCS.md`)](DOCS.md)** | Canonical contracts: env vars, HTTP API, MCP surface, CLI flags, plugins, run layout, Supabase schema, and Documentation Authority Matrix |
| **[Architecture](docs/ARCHITECTURE.md)** | End-to-end async flow, 7-phase pipeline, run lifecycle, stale-run recovery, auth layers, and validation model |
| **[Codebase Guide](docs/CODEBASE-GUIDE.md)** | 90-second mental model, reading path, [Repository Map](docs/codebase/repository-map.md), [Maintainer Playbook](docs/codebase/maintainer-playbook.md), and [Reference Map](docs/codebase/reference-map.md) |
| **[Deployment & Ops](docs/DEPLOYMENT.md)** | `scripts/serve.sh`, Cloud Run + GCS + Cloud Build (`cloudbuild.yaml`), Vercel + CORS, and Supabase ops scripts |
| **[Dataset Evaluation](docs/EVALUATION.md)** | Ground-truth comparison scripts and section evaluators (`evaluation/`) |
| **[Graphify Guide](docs/graphify.md)** | Pinned Graphify `0.9.26` setup, update, and verification workflow |
| **[Contributing](CONTRIBUTING.md)** | Trunk-based Git workflow (`development`, `--ff-only`, conventional commits), testing, and skill authoring standard |

---

## Contributing

Branches start from `development` and merge back with `--ff-only` (direct commits to `main` and `development` are prohibited). See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full Git, testing, and Graphify workflow.

## License

TBD.
