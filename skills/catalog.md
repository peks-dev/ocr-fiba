# AI Agent Skills Catalog (`ocr-engine`)

All repository-owned agent skills live under `skills/`. Load matching skills before modifying code or documentation.

- [`architecture-guardrails`](architecture-guardrails/SKILL.md): System boundaries, inward dependency direction, and server-side enforcement.
- [`docs-alignment`](docs-alignment/SKILL.md): Living doc accuracy, `DOCS.md` authority, link hygiene, and Graphify alignment.
- [`commit-hygiene`](commit-hygiene/SKILL.md): Trunk-based `development` branching, `--ff-only`, conventional commits, and excluded runtime artifacts.
- [`testing-coverage`](testing-coverage/SKILL.md): Package-focused vs workspace test suites, web lint/test/build, and honest evidence reporting.
- [`project-structure`](project-structure/SKILL.md): Placement rules across `core-engine`, `api`, `cli`, `mcp`, `web`, `supabase`, `evaluation`, and `scripts`.
- [`ocr-run-lifecycle`](ocr-run-lifecycle/SKILL.md): 7-phase OCR pipeline, `RunContext.create_run` layout, `RunTracer.step`, and `PipelineConfig` plumbing.
- [`api-error-envelope`](api-error-envelope/SKILL.md): `error_response`, `engine_error_response`, and middleware `JSONResponse` error contracts.
- [`api-key-auth`](api-key-auth/SKILL.md): `ocr_live_<64 hex>` API key lifecycle, caches, invalidation, and layered Supabase JWT verification.
