---
name: ocr-run-lifecycle
description: >
  How a FIBA OCR run moves from a raw scoresheet image to a validated result with traces
  and artifacts. Trigger: Adding or changing a pipeline phase, modifying RunContext/ArtifactStore
  run layout, updating PipelineConfig, or wiring a caller into OcrToolbox.
version: 2.0.0
---

# OCR Run Lifecycle

Guide for modifying the FIBA OCR pipeline, artifact layout, or configuration plumbing without breaking downstream callers (`packages/api`, `packages/cli`, `packages/mcp`).

## When to Use

- Adding or reordering a pipeline phase in `OcrToolbox` / `FibaOcrPipeline`
- Changing the canonical run layout (`runs/<run_id>/...`)
- Adding a configuration option to `PipelineConfig` or `SectionOverride`
- Debugging missing trace steps, crops, artifacts, or `result.json` output

---

## Canonical Phases

`OcrToolbox.run_full_pipeline` (`packages/core-engine/src/ocr_engine_core/toolbox.py`) runs seven phases in order, mirrored in `pipeline.py` (`_PIPELINE_STEPS`):

```text
1. preprocess_sheet   -> preprocessor.preprocess_sheet (sets meta.preprocess_fallback on fallback)
2. detect_sections    -> Cropper.detect_and_crop_sections (boxes.json + 5 section PNGs)
3. crop_team_fouls    -> Cropper.detect_and_crop_team_fouls (fouls_boxes.json + 2 foul PNGs)
4. enhance_sections   -> enhancer.enhance_sections (gamma + CLAHE + optional grid removal)
5. extract_sections   -> Extractor.extract_all_sections (7 TARGETS via ModelProviders)
6. build_final_output -> output_builder.build_final_output (normalization + meta)
7. validate_result    -> ValidationEngine.validate (plugins + match_status + confidence)
```

---

## Canonical Run Layout

When `use_run_layout=True` (`RunContext.create_run` in `types.py`), artifacts live under `<runs_dir>/<run_id>/`:

```text
runs/<run_id>/
├── input/         # Source image copied by ArtifactStore.copy_input()
├── artifacts/     # context.output_dir & context.artifacts_dir (cropped/enhanced images, boxes*.json)
├── raw/           # context.raw_dir (created by ensure_dirs)
├── status.json    # API RunRepository status (queued | running | completed | failed | cancelled)
├── trace.json     # RunTracer output written by RunTracer.write()
└── result.json    # Final validated JSON written by ArtifactStore.write_result()
```

---

## Critical Rules

1. **Wrap every step in `RunTracer.step`:** Use `with tracer.step("step_name", ...) as trace:` (via `OcrToolbox._step`) and record outputs, artifacts, warnings, usage, or errors cleanly. `RunTracer` writes `trace.json` immediately if an exception occurs.
2. **Route model creation through `PipelineConfig` + `create_provider`:** Never instantiate providers ad hoc or bypass `PROVIDER_API_KEY_ENV_NAMES`.
3. **Preserve `runs/<run_id>/` subdirectory names:** `RunRepository` in `packages/api` and MCP resources (`run://`, `result://`, `trace://`, `artifact://`) depend on `input/`, `artifacts/`, `status.json`, `trace.json`, and `result.json`.
4. **Never import downstream adapters in `core-engine`:** Keep `ocr_engine_core` strictly free of `ocr_engine_api`, `ocr_engine_cli`, and `ocr_engine_mcp`.

---

## Cookbook: Adding a Pipeline Option or Phase

### If adding a `PipelineConfig` option
- **Then:** Add a typed field in `packages/core-engine/src/ocr_engine_core/config/pipeline_config.py`, document any env var in its comment, update env resolvers if env-driven, wire `packages/api/src/ocr_engine_api/pipeline_options.py` if exposed via HTTP, and reflect new env vars in `.env.example` and `DOCS.md`.

### If adding a pipeline phase
- **Then:** Implement the domain function/class in `ocr_engine_core`, wrap it in an `OcrToolbox` method using `self._step(...)` returning `ToolResult`, wire it into `OcrToolbox.run_full_pipeline` and `pipeline.py` (`_PIPELINE_STEPS`), and emit `_emit(progress_callback, "step_start" / "step_complete", ...)` so API `RunExecutor` status progress stays accurate.

### Caller wiring reference

| Caller | Entry point | How it executes the pipeline |
|---|---|---|
| FastAPI API | `RunExecutor.run_full_pipeline` (`packages/api/src/ocr_engine_api/services/run_executor.py`) | Calls `OcrToolbox(config).run_full_pipeline(..., use_run_layout=True)` inside a `ThreadPoolExecutor(max_workers=2)` worker and updates `RunRepository` status. |
| CLI | `FibaOcrPipeline.process` (`packages/cli/src/ocr_engine_cli/run_pipeline.py`) | Calls `OcrToolbox.run_full_pipeline` with stderr progress printing and optional `--use-run-layout`. |
| MCP | `packages/mcp/src/ocr_engine_mcp/tools.py` | Calls `ocr-engine-api` over HTTP (`OcrApiClient`); never invokes core directly. |

---

## Verification Checklist

- [ ] No imports from `ocr_engine_api`, `ocr_engine_cli`, or `ocr_engine_mcp` added to `packages/core-engine`.
- [ ] `RunContext.create_run` directory structure (`input/`, `artifacts/`, `raw/`, `trace.json`, `result.json`) preserved.
- [ ] Step appears in `RunTracer` output (`trace.json`) and `_PIPELINE_STEPS` if part of the full run.
- [ ] Core tests pass: `uv run pytest tests/test_core_contracts.py tests/test_toolbox.py tests/test_validation_confidence.py`.
