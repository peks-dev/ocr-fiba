# core-engine — AGENTS.md

> Local guardrails for `packages/core-engine/` (`ocr_engine_core`).
> Read [`/AGENTS.md`](../../AGENTS.md) and [`/docs/codebase/core-pipeline.md`](../../docs/codebase/core-pipeline.md) before modifying code here.

## Context & Stack

Pure-Python OCR domain library (`>= 3.12`, `opencv-python-headless`, `numpy`, `Pillow`, `requests`, dataclasses — Pydantic-free). Owns the 7-phase FIBA scoresheet pipeline, `OcrToolbox`, `ModelProvider` implementations, `PipelineConfig`, `ValidationEngine` (13 plugins + `confidence`), `ArtifactStore`, `RunTracer`, and `OcrEngineError`.

## Local Verification

```bash
uv run pytest tests/test_core_contracts.py tests/test_toolbox.py tests/test_validation_confidence.py tests/test_provider_http_base.py tests/test_grid_removal.py
```

## Non-Negotiable Rules (`NEVER`)

- **NEVER** import `ocr_engine_api`, `ocr_engine_cli`, `ocr_engine_mcp`, FastAPI, or Supabase in this package.
- **NEVER** instantiate providers ad hoc; always go through `providers.create_provider` and `PipelineConfig` / `PROVIDER_API_KEY_ENV_NAMES`.
- **NEVER** change `RunContext.create_run` layout (`input/`, `artifacts/`, `raw/`, `trace.json`, `result.json`) without coordinating with `packages/api` (`RunRepository`).
- **NEVER** write to `outputs/` or `dataset/results/` from library defaults when `use_run_layout=True`.
- **NEVER** expose untyped `dict[str, Any]` config/results on new public surfaces when `types.py` or `PipelineConfig` dataclasses apply.

## Pointers

- Architecture & invariants: [`docs/codebase/core-pipeline.md`](../../docs/codebase/core-pipeline.md)
- Run lifecycle skill: [`skills/ocr-run-lifecycle/SKILL.md`](../../skills/ocr-run-lifecycle/SKILL.md)
- Dataset evaluation: [`docs/EVALUATION.md`](../../docs/EVALUATION.md)
