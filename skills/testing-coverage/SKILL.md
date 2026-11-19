---
name: testing-coverage
description: >
  Test execution, verification scope, and honest reporting standards across Python
  packages and Next.js web app.
  Trigger: Implementing bugfixes, features, or refactors in any package, or verifying changes before merge.
version: 1.0.0
---

# Testing & Verification

Defines the verification commands per package and evidence reporting rules.

## When to Use

- Implementing or fixing behavior in `core-engine`, `api`, `cli`, `mcp`, or `web`
- Running pre-merge validation
- Writing regression tests for fixed bugs or new contracts

---

## Critical Rules

1. **Test every behavior change at the affected boundary:** Core contract/validation changes require tests under `tests/`; API/auth/repo changes require HTTP/unit tests; web logic changes require `packages/web/tests/web-logic.test.ts` + lint + build.
2. **Never report unrun or stale tests as passing:** Only report checks executed **after** your final edit, stating the exact command and observed scope (mocked/filtered vs full).
3. **Never rely on live paid VLM/OCR APIs in unit tests:** Mock `ModelProvider` / HTTP transports in `tests/`. Reserve live runs for explicit `scripts/smoke_async_*.py` or `evaluation/`.
4. **Never relax or skip assertions just to make a test green.**

---

## Cookbook: Verification Commands by Scope

| Scope changed | Command |
|---|---|
| `packages/core-engine` | `uv run pytest tests/test_core_contracts.py tests/test_toolbox.py tests/test_validation_confidence.py tests/test_provider_http_base.py tests/test_grid_removal.py` |
| `packages/api` | `uv run pytest tests/test_api.py tests/test_auth.py tests/test_admin_api.py tests/test_run_repository.py tests/test_hardening.py tests/test_phase3_api_mcp_hardening.py` |
| `packages/mcp` | `uv run pytest tests/test_mcp_client.py tests/test_mcp_auth.py tests/test_phase3_api_mcp_hardening.py` |
| Full Python workspace | `uv run pytest -q` |
| `packages/web` | `npm --prefix packages/web run lint && npm --prefix packages/web test && npm --prefix packages/web run build` |
| End-to-end API / MCP smoke | `python scripts/smoke_async_api.py --image <path>` · `python scripts/smoke_async_mcp.py --image <path>` |

---

## Verification Checklist

- [ ] Focused tests for the modified package pass after the final edit.
- [ ] Full workspace suite (`uv run pytest -q` and/or `packages/web` checks) passes when cross-package or before merge.
- [ ] Regression test added for any bugfix or new contract.
