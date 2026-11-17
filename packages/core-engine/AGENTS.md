# core-engine — AGENTS.md

> Domain-specific guidance for AI agents working on `packages/core-engine/`.
> Cross-cutting rules live in [`/AGENTS.md`](../../../AGENTS.md). Read both before editing.

## Context

Pure-Python OCR domain library. Owns the FIBA scoresheet pipeline, the provider abstractions, validation plugins, the toolbox (agent-friendly atomic operations), and the canonical run layout. The API, CLI, and MCP packages are all adapters that depend on this package.

**This is the only package with no outward dependencies on the rest of the monorepo.** Keep it that way.

## Stack

- Python ≥ 3.12
- `opencv-python-headless`, `numpy`, `Pillow`, `requests` (declared in `pyproject.toml`)
- `dataclass` for configuration, Pydantic-free (the core stays light)
- `pytest` (run from repo root with `uv run pytest tests/`)

## Structure

```text
packages/core-engine/
├── pyproject.toml
└── src/ocr_engine_core/
    ├── __init__.py            # public re-exports
    ├── pipeline.py            # FibaOcrPipeline — full orchestrator
    ├── toolbox.py             # OcrToolbox — agent-friendly atomic operations
    ├── preprocessor.py        # Sheet isolation (preprocess_sheet)
    ├── cropper.py             # Section detection and cropping
    ├── enhancer.py            # Image enhancement (enhance_sections)
    ├── extractor.py           # Per-section data extraction
    ├── output_builder.py      # Output normalization (build_final_output)
    ├── validation/
    │   ├── engine.py          # ValidationEngine
    │   ├── base.py            # Base plugin class
    │   ├── registry.py
    │   └── plugins/           # Concrete validators
    ├── providers/             # Model providers (openrouter, docstrange, glm, gemini, interfaze, qubrid)
    │   ├── base.py            # Provider base + TokenUsage
    │   └── <provider>.py
    ├── config/pipeline_config.py   # PipelineConfig + SectionOverride
    ├── prompts/               # Prompt templates per section
    ├── resources/schemas/     # Bundled JSON schemas for output
    ├── artifacts.py           # ArtifactStore (canonical run layout)
    ├── tracing.py             # RunTracer (StepTrace, RunContext)
    ├── types.py               # RunContext, StepTrace, Artifact, ToolResult
    ├── exceptions.py          # OcrEngineError hierarchy
    └── utils/                 # Misc helpers
```

## Patterns

### 1. Pipeline orchestration is split into "pipeline" and "toolbox"

`FibaOcrPipeline` is the full orchestrator used by the API. `OcrToolbox` exposes the same operations as composable atomic calls with structured `ToolResult`s — designed for agent callers (and what the MCP server could build on in the future).

**Convention:** do not call `Cropper`, `Extractor`, or `ValidationEngine` directly from new code. Wire them through `OcrToolbox` so the structured contract stays consistent.

### 2. Configuration via `PipelineConfig`

All model selection (per phase and per section override) flows through `PipelineConfig` in `config/pipeline_config.py`. Default extraction uses `resolve_default_extractor()` and `resolve_default_extractor_reasoning()` (`OCR_DEFAULT_EXTRACTOR_PROVIDER`, default `openrouter`; `OCR_DEFAULT_EXTRACTOR_MODEL`, default `google/gemini-4-carbon` or `nanonets-ocr-3` when `docstrange` is selected; `OCR_DEFAULT_EXTRACTOR_REASONING`, default `{"effort": "low", "exclude": True}` when `openrouter` + `google/gemini-4-carbon` is active). Sections can override the default extractor with `SectionOverride`. To add a new pipeline option:

1. Add a typed field to `PipelineConfig` (or `SectionOverride` if it's per-section).
2. Document the env var it reads in the field's comment.
3. Update `resolve_default_extractor` / env helpers if it should be loadable from env.

### 3. Provider implementations

Every provider in `providers/<name>.py` must:

- Inherit from `providers.base.Provider`.
- Implement `complete(...)` returning a `ProviderResponse` (or raise a typed exception from `exceptions`).
- Update `TokenUsage` on every call.

Adding a new provider:

1. Create `providers/<name>.py` with a class extending `Provider`.
2. Register it in `providers/__init__.py` (`create_provider` factory + `ProviderType` literal).
3. Add a unit test under `tests/test_core_contracts.py` exercising the contract.

### 4. Validation plugins and confidence

Plugins live in `validation/plugins/` (`core.py`, `fiba_rules.py`, `referee.py` — 13 registered plugins: 9 core, 2 FIBA, 2 referee) and extend `validation.base.ValidationPlugin`. `ValidationEngine` in `validation/engine.py` runs the selected plugins (`None` = core defaults; `"all"` = every registered plugin), emits `validation_warnings`, sets `match_status`, and computes weighted per-section + global `confidence` via `compute_confidence`. Sheet isolation fallbacks are flagged in `meta.preprocess_fallback` and surfaced by `PreprocessFallbackPlugin`.

### 5. Canonical run layout (artifacts)

`ArtifactStore` (in `artifacts.py`) writes runs under `runs/{run_id}/` with a fixed substructure:

```text
runs/<run_id>/
├── input/         # original image
├── preprocessed/  # isolated sheet
├── crops/         # section crops
├── enhanced/      # enhanced section images
├── trace.json     # RunTracer output
└── result.json    # final structured output
```

`pipeline.process(..., use_run_layout=True)` enables this layout. Both the API and CLI rely on it; do not change the layout without coordinating with the API and CLI packages.

### 6. Tracing

Every pipeline step emits a `StepTrace` via `RunTracer`. The trace is included in the run's `result.json` and surfaced through the MCP `get_run_trace` tool. When adding a new pipeline phase, wrap the work in `tracer.span("phase_name", **metadata)` so the trace stays complete.

## Rules specific to core-engine

- **NEVER** import from `ocr_engine_api`, `ocr_engine_cli`, or `ocr_engine_mcp` (enforced by import direction in code review).
- **NEVER** add a network dependency that talks to a runtime service (e.g. Supabase). The core stays pure-Python with only the model providers.
- **NEVER** write to `outputs/`, `dataset/results/`, or any path inside another package. Runtime artifacts go under `runs/` or a caller-provided directory.
- New env vars must be documented in the field comment of `PipelineConfig` and reflected in `.env.example`.
- All public functions take and return typed objects. Avoid `dict[str, Any]` on public surfaces — use the typed `types.py` definitions.

## Auto-invoke skills (per task)

| Task | Skill |
|---|---|
| Optimizing slow Python code | `python-codebase-optimization` |
| Git operations | `git-commit-creation` |
| Pre-completion security check (if exposing a new input surface) | `audit-security-implementation` |

## References

- `FibaOcrPipeline` — see `src/ocr_engine_core/pipeline.py`
- `OcrToolbox` — see `src/ocr_engine_core/toolbox.py`
- `Provider` base — see `src/ocr_engine_core/providers/base.py`
- `RunTracer` and `RunContext` — see `src/ocr_engine_core/tracing.py` and `types.py`
- First-party skill: `packages/core-engine/skills/ocr-run-lifecycle/SKILL.md`
