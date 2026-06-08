---
name: ocr-run-lifecycle
description: How a FIBA OCR run moves from a raw scoresheet image to a structured result with traces and artifacts. Use when adding a new pipeline phase, debugging run artifacts, or wiring a new caller (API route, CLI subcommand, MCP tool) into the pipeline.
version: 1.0.0
---

# OCR Run Lifecycle

Guide for understanding and extending how a single FIBA OCR run flows through the engine. Trigger this skill when you are about to add a new pipeline phase, change the canonical artifact layout, or wire a new caller into `FibaOcrPipeline.process` / `OcrToolbox`.

## When to use

- Adding a new pipeline phase (e.g. a new detector, a new enhancer).
- Changing the canonical run layout (`runs/<run_id>/...`).
- Reading or writing artifacts from a new caller (API route, CLI, MCP tool).
- Debugging why a run is missing a trace span, a crop, or a result.

## Canonical phases

The pipeline runs these phases in order. The MCP server exposes `get_run_trace` so agents and humans can see the actual order and durations of any run.

```text
0. Sheet isolation         → Preprocessor.preprocess_sheet
1. Section detection       → Cropper (per section)
2. Team-fouls sub-crop     → Cropper
3. Image enhancement       → Enhancer.enhance_sections
4. Data extraction         → Extractor (per section)
5. Output normalization    → OutputBuilder.build_final_output
6. Validation              → ValidationEngine + plugins
```

## Canonical run layout

Every run that uses `use_run_layout=True` writes under `runs/<run_id>/`:

```text
runs/<run_id>/
├── input/         # original image
├── preprocessed/  # isolated sheet
├── crops/         # section crops
├── enhanced/      # enhanced section images
├── trace.json     # RunTracer output
└── result.json    # final structured output
```

When adding a new artifact type, place it under an existing subdirectory when it belongs to that phase. Create a new subdirectory only if a new phase is introduced, and update `ArtifactStore` accordingly.

## Tracing rule

Every new pipeline phase MUST be wrapped in a `RunTracer` span. The trace is what the MCP `get_run_trace` tool surfaces, and it's the easiest way to debug a slow or failing run.

```python
with tracer.span("phase_name", **metadata) as span:
    result = do_work(...)
    span.set_metadata("count", len(result))
```

Do not skip this even for "trivial" phases — over-instrumentation is fine, gaps in the trace are not.

## Configuration plumbing

All per-phase model selection goes through `PipelineConfig` (and `SectionOverride` for per-section overrides). When you add a new phase that uses a model:

1. Add a typed field to `PipelineConfig` (e.g. `phase_name_provider: ProviderType`).
2. If sections can override it, add a corresponding `SectionOverride` field.
3. Build the model via the `providers.create_provider` factory in the phase's tool method.
4. Document the env var that loads the field in the field's comment.
5. Reflect the new env var in `.env.example`.

## How callers wire in

| Caller | Entry point | What it does |
|---|---|---|
| FastAPI route (`POST /v1/runs`) | `RunExecutor` in `services/run_executor.py` | Creates `RunContext`, invokes `FibaOcrPipeline.process(..., use_run_layout=True)`, sanitizes the response |
| CLI (`ocr-run`) | `run_pipeline.main` | Calls `FibaOcrPipeline.process` directly with caller-provided args |
| MCP (`submit_scoresheet_from_path`, `submit_scoresheet_base64`) | `tools.py` → `OcrApiClient` | Always goes through the API, never calls the pipeline directly |

All three rely on the same canonical run layout. Do not change the layout without updating all three callers.

## Constraints (do not violate)

- Do not import from `ocr_engine_api`, `ocr_engine_cli`, or `ocr_engine_mcp` inside `core-engine`.
- Do not change `runs/<run_id>/<subdir>` names — the API, CLI, and MCP tools read them by name.
- Do not skip `tracer.span(...)` for a phase, even if it seems trivial.
- Do not bypass `PipelineConfig` to instantiate a provider ad hoc. Always go through the factory.

## References

- `FibaOcrPipeline.process` — `packages/core-engine/src/ocr_engine_core/pipeline.py`
- `OcrToolbox` — `packages/core-engine/src/ocr_engine_core/toolbox.py`
- `RunTracer` and `RunContext` — `packages/core-engine/src/ocr_engine_core/tracing.py` and `types.py`
- `ArtifactStore` (canonical layout) — `packages/core-engine/src/ocr_engine_core/artifacts.py`
- `PipelineConfig` — `packages/core-engine/src/ocr_engine_core/config/pipeline_config.py`
- API call site — `packages/api/src/ocr_engine_api/services/run_executor.py`
