# cli — AGENTS.md

> Domain-specific guidance for AI agents working on `packages/cli/`.
> Cross-cutting rules live in [`/AGENTS.md`](../../../AGENTS.md). Read both before editing.

## Context

Command-line entry points for the FIBA OCR engine. Each script is exposed as a console script (see `pyproject.toml` `[project.scripts]`) and can also be invoked with `python -m`. The CLI talks to `ocr_engine_core` directly — it does not go through the API.

## Stack

- Python ≥ 3.12
- `argparse` (stdlib) for all CLIs
- `ocr_engine_core` for the pipeline and supporting modules
- No third-party CLI framework

## Structure

```text
packages/cli/
├── pyproject.toml
└── src/ocr_engine_cli/
    ├── __init__.py
    ├── run_pipeline.py        # ocr-run        — process a single scoresheet image
    ├── run_dataset.py         # ocr-dataset    — batch run over a directory
    ├── binarize_image.py      # ocr-binarize   — image preprocessing utility
    └── cv_progressive_score.py # ocr-progressive-score — scoreboard detection utility
```

Console scripts (declared in `pyproject.toml`):

| Script | Entry | Purpose |
|---|---|---|
| `ocr-run` | `ocr_engine_cli.run_pipeline:main` | Run the full pipeline on one image |
| `ocr-dataset` | `ocr_engine_cli.run_dataset:main` | Run the pipeline over a folder of images |
| `ocr-binarize` | `ocr_engine_cli.binarize_image:main` | Binarize a single image (preprocessing helper) |
| `ocr-progressive-score` | `ocr_engine_cli.cv_progressive_score:main` | Progressive scoreboard detection helper |
| `ocr-mcp` | (registered via the MCP package, not CLI) | MCP server entry — see `packages/mcp/` |

## Patterns

### 1. Each script is a `main()` callable

Every entry-point module exposes a `main()` function and a small `argparse` block. Convention:

- `main()` returns an `int` exit code (`0` on success).
- Errors are printed to `stderr` with a one-line message and a non-zero exit.
- Heavy imports (the pipeline) happen inside `main()`, not at module top, to keep `--help` fast.

### 2. Reuse core utilities, never reimplement

When adding a new CLI:

- If the task is "run pipeline on N images", call `FibaOcrPipeline.process` (or `OcrToolbox` for atomic ops) — don't reimplement cropping, extraction, or validation.
- If the task is a preprocessing helper (binarize, score detection), put the implementation in `ocr_engine_core` first, then add a thin CLI wrapper.

### 3. Use the canonical run layout

When a CLI runs the full pipeline, prefer the canonical run layout (`runs/<run_id>/...`) with `--use-run-layout` so artifacts are usable by the API/MCP without re-processing. Pass through `--runs-dir` and `--run-id` to `FibaOcrPipeline.process`.

## Rules specific to cli

- **NEVER** import from `ocr_engine_api` or `ocr_engine_mcp` (downstream of the core).
- **NEVER** add a network dependency. The CLI is local-only.
- **NEVER** write to `outputs/` inside the package. Use a caller-provided directory or `runs/`.
- Keep CLIs idempotent and scriptable: prefer flags over interactive prompts.
- New console scripts must be declared in `pyproject.toml` under `[project.scripts]`.

## Auto-invoke skills (per task)

| Task | Skill |
|---|---|
| Optimizing slow Python code | `python-codebase-optimization` |
| Git operations | `git-commit-creation` |

## References

- `pyproject.toml` — console script registration
- `FibaOcrPipeline.process` — see `packages/core-engine/src/ocr_engine_core/pipeline.py`
- `OcrToolbox` — see `packages/core-engine/src/ocr_engine_core/toolbox.py`
