## Summary

- What changed and why:

## Verification

- [ ] Relevant tests pass (`uv run pytest -q` and/or `npm --prefix packages/web run lint && npm --prefix packages/web test && npm --prefix packages/web run build`)
- [ ] Package boundaries preserved (`core-engine` pure; `ocr_engine_mcp` HTTP-only)
- [ ] Docs & sibling surfaces updated per `DOCS.md` (`Documentation Authority`) when contracts, endpoints, CLI, MCP, env vars, or migrations change
- [ ] Graphify updated and validated (`./scripts/graphify-update && ./scripts/graphify-check`)
