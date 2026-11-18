[← Codebase Guide](../CODEBASE-GUIDE.md) | [← Previous: API, Auth & Supabase](api-and-auth.md) | [Next: Maintainer Playbook →](maintainer-playbook.md)

# Adapters and Web (`cli`, `mcp`, `web`)

**`packages/cli`, `packages/mcp`, and `packages/web` are thin delivery interfaces around the OCR domain.** The CLI calls `ocr_engine_core` locally; MCP and Web are strict HTTP clients of `ocr_engine_api` and never import the core.

## 1. CLI (`packages/cli`, `ocr_engine_cli`)

Four console scripts declared in `packages/cli/pyproject.toml` using stdlib `argparse`:

| Command | Entry point | Purpose |
|---|---|---|
| `ocr-run` | `ocr_engine_cli.run_pipeline:main` | Run the full 7-phase pipeline on one scoresheet image (`image` positional arg). |
| `ocr-dataset` | `ocr_engine_cli.run_dataset:main` | Batch-run the pipeline across `ALL_SHEETS` (`sheet-001`..`sheet-010`) under `dataset/`. |
| `ocr-binarize` | `ocr_engine_cli.binarize_image:main` | Standalone adaptive/Otsu binarization helper (`--method`, `--block-size`, `--c`). |
| `ocr-progressive-score` | `ocr_engine_cli.cv_progressive_score:main` | Experimental CV-only progressive score extractor with optional `--gt` check. |

### Key `ocr-run` & `ocr-dataset` flags and conventions

- **Positional `image` argument (not `--image`):** `ocr-run path/to/sheet.jpg`.
- **Canonical layout (`--run-layout`):** Writes to `<runs_dir>/<run_id>/` (`--runs-dir`, default `runs` in `ocr-run` or `dataset/runs` in `ocr-dataset`; `--run-id` supported in `ocr-run`). Cannot be combined with `--output-dir`.
- **Provider & reasoning overrides:** `--cropper`, `--cropper-model`, `--extractor`, `--extractor-model`, `--extractor-reasoning-effort`, `--extractor-max-workers` (`ocr-run`), plus per-section `--override-section SECTION:PROVIDER:MODEL` and `--override-reasoning-effort` (`ocr-run`).
- **Preprocessing & validation:** `--grid-removal {inpaint,handwriting}`, `--gamma` (`ocr-dataset`), `--validation ...` (`ocr-run`, pass `all` or specific plugin names), `--json` (`ocr-run`, emits structured JSON and exits non-zero on `OcrEngineError`).
- **Lazy heavy imports & `sys.exit`:** Heavy pipeline imports happen inside `main()` so `--help` stays fast; errors print to `stderr` and exit with status `1`.

---

## 2. MCP Server (`packages/mcp`, `ocr_engine_mcp`)

Wraps `ocr-engine-api` via `FastMCP` (`fastmcp==3.2.4`) and `OcrApiClient` (`requests.Session`).

### Architecture & transport

```text
Agent Client ──(stdio or Streamable HTTP /mcp)──► FastMCP (server.py)
                                                       ├─ auth.py (McpTokenVerifier when MCP_AUTH_TOKEN set)
                                                       ├─ tools.py (response shaping + handle_api_error)
                                                       └─ client.py (OcrApiClient -> HTTP GET/POST to OCR API)
```

- **Local stdio:** `python mcp_server.py` (root wrapper) or `ocr-mcp` (`MCP_TRANSPORT=stdio`). Ignores `MCP_AUTH_TOKEN` and authenticates to the API with `OCR_API_KEY`.
- **Streamable HTTP:** `MCP_TRANSPORT=http MCP_HOST=127.0.0.1 MCP_PORT=8001 uv run ocr-mcp` (endpoint `/mcp`; `FASTMCP_STATELESS_HTTP=true` on Cloud Run).
- **HTTP bearer verification (`auth.py`):** Enabled when `MCP_AUTH_TOKEN` is set. Accepts:
  1. Static `MCP_AUTH_TOKEN` (constant-time comparison; server forwards `OCR_API_KEY` upstream).
  2. Per-client `ocr_live_<64 hex>` keys (probed via `GET /v1/runs?limit=1`; `2xx`/`429` accepted, `401`/`403`/network failure rejected fail-closed; cached in-memory 60s / 1024 entries and forwarded directly as the upstream API bearer token so per-account quotas apply).

### Tools, resources, and prompts (`server.py`)

- **Tools (10):**
  - `submit_scoresheet_from_path(image_path, run_id?, options?)` — registered **only** when `path_input_allowed()` is true (`MCP_ALLOW_PATH_INPUT` override, else `OCR_ENV != "production"`).
  - `submit_scoresheet_base64(image_base64, filename?, run_id?, options?)` — validates base64 & non-empty bytes client-side, uploads via `POST /v1/runs/upload`.
  - `poll_run(run_id)`, `wait_for_run(run_id, timeout_seconds=300, poll_interval_seconds=2)`, `list_runs(limit=20)`, `inspect_run(run_id)`, `get_run_result(run_id)`, `get_run_trace(run_id)`, `list_run_artifacts(run_id, limit=200)`, `get_artifact(run_id, artifact_name)` (returns base64 payload + content-type).
- **Resources (4, JSON):** `run://{run_id}`, `result://{run_id}`, `trace://{run_id}`, `artifact://{run_id}/{artifact_name}`.
- **Prompts (3):** `review_extraction(run_id)`, `suggest_retry_strategy(run_id)`, `explain_validation_warnings(run_id)`.
- **Error mapping:** Every tool/resource wraps calls in `tools.handle_api_error(OcrApiError)` (parsing both top-level `error` and FastAPI `detail.error` responses in `OcrApiClient._raise_for_error`). `wait_for_run` shapes `RUN_TIMEOUT` and terminal `failed` statuses with `resources` and `next_actions`.

---

## 3. Web App (`packages/web`, Next.js 15 App Router)

Standalone Next.js 15 + React 19 + Tailwind CSS v4 + `@supabase/ssr` app communicating with `ocr-engine-api` over HTTPS (`NEXT_PUBLIC_OCR_API_URL`) and Supabase Auth/DB.

### Route surfaces and server-side auth gates

| Route group | Auth & role enforcement | Purpose |
|---|---|---|
| `/` (`app/page.tsx`), `/login` (`app/login/page.tsx`) | Public (active users on `/login` redirect via `middleware.ts`) | Landing page and email/password login (`AuthCard`, `auth/login/route.ts`). |
| `/auth/callback`, `/auth/invite`, `/auth/accept-invite` | Session / invite token exchange | `InviteSetupCard` + `POST /auth/accept-invite` calls `markCurrentAccountAccepted(user.id)` to activate account & update `admin_invitations`. |
| `/admin`, `/admin/api-keys` | `middleware.ts` + `requireAdminAccount()` in `app/admin/layout.tsx` & pages | Invite testers (`admin_invitations`), inspect accounts, bootstrap/list/delete own keys (`ApiKeysPanel`), issue/revoke keys for other accounts (`AccountKeysPanel`). |
| `/test/player`, `/test/referee`, `/test/club` | `middleware.ts` + `requireDemoAccess(demo)` in each demo's `layout.tsx` | Invite-only demos (`player` progress/history, `referee` capture/reconcile/submit/league, `club` roster/overview/players). Admins may access all three demos. |
| `/api/league/submissions` | `authorizeDemoApiAccess("referee")` | Server-side Airtable proxy (`AIRTABLE_TOKEN`, `AIRTABLE_BASE_ID`, `AIRTABLE_LEAGUE_TABLE`) keeping Airtable credentials off the browser. |
| `/docs/quickstart` | `middleware.ts` + `requireCurrentUserAccount()` in `page.tsx` | Authenticated API/MCP quickstart snippets for signed-in users. |

### Browser-side conventions

- **Supabase clients:** Use `lib/supabase/server.ts` in RSC/route handlers, `lib/supabase/client.ts` in Client Components, `lib/supabase/admin.ts` (`SUPABASE_SERVICE_KEY`) strictly server-side, and `lib/supabase/middleware.ts` in `src/middleware.ts`. Never instantiate `createClient` inline in components.
- **API calls (`lib/api.ts`):** `apiFetch` and `uploadRun` attach the signed-in Supabase session JWT (`Authorization: Bearer <access_token>`) — never store or paste `ocr_live_` keys in browser storage.
- **Client effect hygiene:** Fetch session/key panels once per mount and refresh explicitly after mutations (`api-keys-panel.tsx`), avoiding `session`-dependency re-fetch loops.
- **UI feedback & loading:** Use `sonner` toasts (`AppToaster` in root layout) and `<Suspense>` boundaries for non-blocking server/search-param reads.

---

## Adapters & Web invariants and checklists

### Invariants
- **NEVER** import `ocr_engine_core` in `packages/mcp` or expose internal paths/core imports to `packages/web`.
- **NEVER** import `ocr_engine_api` or `ocr_engine_mcp` in `packages/cli`.
- **NEVER** leak `OcrApiError` raw out of MCP tools or expose `SUPABASE_SERVICE_KEY` / `AIRTABLE_TOKEN` with `NEXT_PUBLIC_`.
- **NEVER** introduce `pages/` routes or store `ocr_live_` secrets in browser storage.

### Change checklists
- **CLI change:** Registered in `packages/cli/pyproject.toml` `[project.scripts]`, heavy imports inside `main()`, non-zero exit on errors, compatible with `--run-layout`.
- **MCP change:** Typed method in `client.py`, wrapper in `tools.py` using `handle_api_error`, registered in `server.py` with actionable docstring, tests pass (`uv run pytest tests/test_mcp_client.py tests/test_mcp_auth.py tests/test_phase3_api_mcp_hardening.py`).
- **Web change:** Gate enforced in server layout / `authorizeDemoApiAccess`, typed `NEXT_PUBLIC_*` in `lib/env.ts`, passes `npm --prefix packages/web run lint && npm --prefix packages/web test && npm --prefix packages/web run build`.

---

[← Previous: API, Auth & Supabase](api-and-auth.md) | [Next: Maintainer Playbook →](maintainer-playbook.md)
