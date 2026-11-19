---
name: docs-alignment
description: >
  Documentation consistency and Graphify knowledge graph alignment rules.
  Trigger: Any change modifying endpoints, MCP tools, CLI flags, env vars,
  validation plugins, Supabase migrations, deployment scripts, or Markdown docs.
version: 1.0.0
---

# Docs Alignment

Keeps `DOCS.md`, `docs/`, `AGENTS.md`, `skills/`, and `graphify-out/` truthful against shipped code.

## When to Use

- Adding or changing HTTP routes, MCP tools/resources/prompts, CLI flags, or env vars
- Changing `PipelineConfig` defaults, providers, validation plugins, or Supabase migrations
- Updating deployment scripts (`scripts/deploy_cloudrun.sh`, `cloudbuild.yaml`, Vercel)
- Editing any Markdown file in the repository

---

## Critical Rules

1. **Document verified current behavior, never aspirations:** Verify flag names, status codes, paths, and defaults directly in code before writing docs.
2. **Respect `DOCS.md` as the single technical reference:** Do not duplicate full endpoint, env var, CLI flag, or schema tables in `README.md`, `AGENTS.md`, or package docs — update `DOCS.md` and link to it.
3. **Update sibling surfaces together:** Check [DOCS.md § Documentation Authority](../../DOCS.md#documentation-authority) and update every row affected in the same change.
4. **Update Graphify after logical or semantic doc changes:** Follow [docs/graphify.md](../../docs/graphify.md). Never hand-edit `graphify-out/`.
5. **Keep all repository documentation in concise technical English.**

---

## Cookbook: Closing a Code or Docs Change

```bash
# 1. Verify code/tests pass first
uv run pytest -q

# 2. Update Graphify and validate
./scripts/graphify-update
./scripts/graphify-check
git diff -- graphify-out/ .graphifyignore
```

For semantic documentation changes, also run `$graphify . --update` per `docs/graphify.md`.

---

## Verification Checklist

- [ ] Every documented path, env var, CLI flag, and status code exists in current code.
- [ ] All relative Markdown links resolve to existing files.
- [ ] `DOCS.md` and sibling docs listed in *Documentation Authority* are updated together.
- [ ] `./scripts/graphify-update` and `./scripts/graphify-check` pass after final edits.
