# cli — AGENTS.md

> Local guardrails for `packages/cli/` (`ocr_engine_cli`).
> Read [`/AGENTS.md`](../../AGENTS.md) and [`/docs/codebase/adapters-and-web.md`](../../docs/codebase/adapters-and-web.md) before modifying code here.

## Context & Stack

Stdlib `argparse` console scripts declared in `packages/cli/pyproject.toml` (`ocr-run`, `ocr-dataset`, `ocr-binarize`, `ocr-progressive-score`). Calls `ocr_engine_core` directly (`FibaOcrPipeline` / `OcrToolbox`); does not talk to `ocr-api` or `ocr-mcp`.

## Local Verification

```bash
uv run ocr-run --help
uv run ocr-dataset --help
```

## Non-Negotiable Rules (`NEVER`)

- **NEVER** import `ocr_engine_api` or `ocr_engine_mcp`.
- **NEVER** add network calls to the OCR API from CLI tools (CLI is local-only).
- **NEVER** import heavy pipeline modules at module top level inside entrypoints (keep `--help` fast by importing inside `main()`).
- **NEVER** write runtime artifacts inside `packages/`; respect `--run-layout` (`--runs-dir`) or caller-provided `--output-dir`.
- **ALWAYS** register new console scripts under `[project.scripts]` in `packages/cli/pyproject.toml` and prefer flags over interactive prompts.

## Pointers

- CLI architecture & flags: [`docs/codebase/adapters-and-web.md`](../../docs/codebase/adapters-and-web.md)
- Dataset evaluation: [`docs/EVALUATION.md`](../../docs/EVALUATION.md)
