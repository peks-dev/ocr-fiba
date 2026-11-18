[← Codebase Guide](../CODEBASE-GUIDE.md) | [← Previous: Repository Map](repository-map.md) | [Next: API, Auth & Supabase →](api-and-auth.md)

# Core Pipeline

**`packages/core-engine` (`ocr_engine_core`) is the pure OCR domain library.** It owns sheet preprocessing, section cropping, enhancement, provider extraction, output normalization, deterministic validation, confidence scoring, run tracing, and filesystem artifact layout.

## Orchestrator split: `OcrToolbox` vs `FibaOcrPipeline`

`OcrToolbox` (`toolbox.py`) and `FibaOcrPipeline` (`pipeline.py`) share the same underlying steps, with distinct responsibilities:

| Entry point | Primary caller | Behavior |
|---|---|---|
| `OcrToolbox(config)` | `packages/api` (`RunExecutor`) and atomic/agent callers | Exposes each phase as an independent method returning `ToolResult`, plus `run_full_pipeline(...)` with optional `progress_callback` and `RunTracer`. |
| `FibaOcrPipeline(config)` | `packages/cli` (`ocr-run`, `ocr-dataset`) | Wraps `OcrToolbox.run_full_pipeline`, prints `_PIPELINE_STEPS` progress (`[i/7]`) to `stderr`, exposes `last_context` and `total_usage`, and provides `save_result`. |

**Placement rule:** Do not invoke `Cropper`, `Extractor`, or `ValidationEngine` ad hoc from downstream callers. Route through `OcrToolbox` (or `FibaOcrPipeline` for CLI progress) so tracing, artifact layout, and `ToolResult` contracts stay consistent.

---

## Seven-phase execution flow

`OcrToolbox.run_full_pipeline` executes seven ordered steps:

```text
1. preprocess_sheet    -> preprocessor.preprocess_sheet()
                          Isolates sheet & perspective-corrects to <stem>-recortada.jpg.
                          On ValueError, falls back to original image and sets meta.preprocess_fallback = True.

2. detect_sections     -> Cropper.detect_and_crop_sections()
                          Detects 5 regions (header, team_a, team_b, progressive_score, footer)
                          with CROPPING_PROMPT + "cropping" schema; enforces MIN_CROP_DIM_PX = 16;
                          writes boxes.json + <section>.png.

3. crop_team_fouls     -> Cropper.detect_and_crop_team_fouls()
                          Sub-crops team_a_fouls.png and team_b_fouls.png using
                          TEAM_FOULS_CROPPING_PROMPT + "team_fouls_cropping" schema;
                          writes fouls_boxes.json.

4. enhance_sections    -> enhancer.enhance_sections()
                          Applies gamma correction (default 0.7) + CLAHE, optional progressive_score
                          grid removal (False/"off", "inpaint", "handwriting"), and dense upscaling.

5. extract_sections    -> Extractor.extract_all_sections()
                          Extracts 7 TARGETS in parallel (extractor_max_workers=7) using default
                          or per-section SectionOverride providers; tracks TokenUsage.

6. build_final_output  -> output_builder.build_final_output()
                          Normalizes strings/diacritics, judge names, foul/entry flags, points from
                          running score, and attaches meta (cropper, extractor, total_tokens, fallback).

7. validate_result     -> ValidationEngine.validate()
                          Runs selected plugins, attaches plugin-tagged validation_warnings,
                          computes match_status and weighted confidence.
```

---

## Extraction targets and section schemas

`Extractor` (`extractor.py`) runs over seven `TARGETS` defined in `TARGETS`:

| Target | Image file | Schema (`resources/schemas/`) | Default `max_tokens` | Notes |
|---|---|---|---|---|
| `header` | `header.png` | `header.json` | `1200` | Competition, teams, date, game info. |
| `team_a` | `team_a.png` | `team.json` | `4000` | Markdown parsed via `team_markdown_parser` (JSON for `docstrange`). |
| `team_b` | `team_b.png` | `team.json` | `4000` | Markdown parsed via `team_markdown_parser` (JSON for `docstrange`). |
| `team_a_fouls` | `team_a_fouls.png` | `team_fouls.json` | `1200` | Team A per-quarter fouls. |
| `team_b_fouls` | `team_b_fouls.png` | `team_fouls.json` | `1200` | Team B per-quarter fouls. |
| `progressive_score` | `progressive_score.png` | `progressive_score.json` | `6000` | Running score timeline and shooter numbers. |
| `footer` | `footer.png` | `footer.json` | `1500` | Referees, scorer, final score, signatures. |

Special `Extractor` rules:
- **Reasoning token headroom:** If the resolved provider has a truthy `reasoning` setting, `_extract_section` enforces `max_tokens >= 16000` so reasoning tokens do not truncate output.
- **Agentic mode:** `AGENTIC_MODE_SECTIONS` enables `agentic_mode` on `docstrange` for `team_a`, `team_b`, and `progressive_score` when the provider supports it.
- **Schema adaptation:** `resources/schemas/__init__.py` (`load_schema(name, provider=...)`) adapts canonical schemas when provider-specific formatting is required (for example, `interfaze` or `gemini`).

---

## Configuration (`PipelineConfig` and `SectionOverride`)

`config/pipeline_config.py` is the dataclass source of truth for model selection, enhancement, validation, and API key resolution:

| Field / Concept | Default / Resolution | Relevant env vars |
|---|---|---|
| `cropper_provider` / `cropper_model` | `"openrouter"` / `"google/gemini-3-flash-preview"` | Provider API key env vars below |
| `extractor_provider` / `extractor_model` | `resolve_default_extractor()` → `"openrouter"` / `"google/gemini-4-carbon"` (or `"nanonets-ocr-3"` when `docstrange`) | `OCR_DEFAULT_EXTRACTOR_PROVIDER`, `OCR_DEFAULT_EXTRACTOR_MODEL` |
| `extractor_reasoning` | `resolve_default_extractor_reasoning()` → `{"effort": "low", "exclude": True}` when `openrouter` + `google/gemini-4-carbon`, else `None` | `OCR_DEFAULT_EXTRACTOR_REASONING` (JSON object, effort level `max`..`none`, or `off`/`false`/`disabled`) |
| `extractor_max_workers` | `7` | Configured via `PipelineConfig` |
| `section_overrides` | `{}` (`dict[str, SectionOverride]`) | Per-section `provider`, `model`, `reasoning`, `max_tokens` |
| `grid_removal` | `False` (`False`/`"off"`, `"inpaint"`, `"handwriting"`) | Configured via `PipelineConfig` |
| `gamma` | `0.7` (`None` or `1.0` disables) | Configured via `PipelineConfig` |
| `validation_plugins` | `None` (core category default) or `"all"` or `list[str]` | Configured via `PipelineConfig` |

**To add a new pipeline option:**
1. Add a typed field (with default and env-var comment) to `PipelineConfig` or `SectionOverride`.
2. Update env resolution helpers in `config/pipeline_config.py` if configurable via environment.
3. Wire API option parsing (`packages/api/src/ocr_engine_api/pipeline_options.py`) and `.env.example` if exposed externally.

---

## Providers (`providers/`)

All providers inherit from `ModelProvider` (`providers/base.py`) and are instantiated solely through `create_provider` (`providers/__init__.py`):

| `ProviderType` | Class | Transport base | Candidate key env vars (in priority order) |
|---|---|---|---|
| `"openrouter"` | `OpenrouterProvider` | `HttpJsonProvider` | `OPENROUTER_API_KEY` |
| `"gemini"` | `GeminiProvider` | `HttpJsonProvider` | `GOOGLE_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_GENAI_API_KEY` |
| `"glm"` | `GlmProvider` | `HttpJsonProvider` | `GLM_API_KEY`, `ZAI_API_KEY` |
| `"interfaze"` | `InterfazeProvider` | `HttpJsonProvider` | `INTERFAZE_API_KEY`, `INTERFAZE_KEY` |
| `"qubrid"` | `QubridProvider` | `HttpJsonProvider` | `QUBRID_API_KEY` |
| `"docstrange"` | `DocstrangeProvider` | `ModelProvider` (direct, `MAX_RETRIES = 3`) | `DOCSTRANGE_API_KEY` |

`HttpJsonProvider` (`providers/http_base.py`) standardizes `TIMEOUT = 180s`, `MAX_ATTEMPTS = 4` (1 initial attempt + up to 3 retries), and exponential backoff (`1.0s` base, `20.0s` cap, `0.25` jitter) for retryable `ProviderError`s.

**To add a new provider:**
1. Subclass `HttpJsonProvider` (or `ModelProvider` if non-standard HTTP) in `providers/<name>.py`.
2. Register the `ProviderType` literal and branch in `providers/__init__.py` (`create_provider`) and `DetectorName` in `providers/base.py`.
3. Add its canonical env var tuple to `PROVIDER_API_KEY_ENV_NAMES` in `utils/image_utils.py` and key resolution in `PipelineConfig`.
4. Add contract tests in `tests/test_core_contracts.py` (and `tests/test_provider_http_base.py` if using `HttpJsonProvider`).

---

## Validation plugins and confidence (`validation/`)

Built-in plugins auto-register on import of `validation/plugins/__init__.py`. There are **13 registered plugins** across two `ValidationPlugin.category` values:

| Category | Constant | Included when `validation_plugins=None`? | Registered plugins |
|---|---|---|---|
| Core consistency & cross-checks | `CATEGORY_CORE` (`"core"`) | **Yes (11 plugins run by default)** | `core_quarter_sums`, `core_duplicate_numbers`, `core_ghost_players`, `core_progressive_vs_final`, `core_player_vs_progressive`, `core_progressive_sequence`, `core_entry_and_fouls_consistency`, `core_illegible_marks`, `core_preprocess_fallback` (`plugins/core.py`), plus `referee_player_points_sum`, `referee_winner_consistency` (`plugins/referee.py`). |
| FIBA sport rules | `CATEGORY_SPORT_RULES` (`"sport_rules"`) | No (opt-in by name or `"all"`) | `fiba_player_fouls`, `fiba_team_fouls` (`plugins/fiba_rules.py`). |

### Status and confidence computation (`validation/base.py`)

- **`determine_match_status(warnings)`:**
  - Any `"critical"` warning → `"error"`
  - Else any `"high"` or `"medium"` warning → `"needs_review"`
  - Else (no warnings or only `"low"`) → `"success"`
- **`compute_confidence(data, warnings, match_status)`:**
  - Starts each section at `1.0` with section weights: `header` (`0.10`), `team_a` (`0.25`), `team_b` (`0.25`), `progressive_score` (`0.25`), `footer` (`0.15`).
  - Subtracts per-warning severity penalties (`critical`: `0.40`, `high`: `0.20`, `medium`: `0.10`, `low`: `0.03`) from the targeted section (or `0.25 * penalty` across all sections when `field` has no section prefix), plus `0.5 * penalty` to coupled sections for `player_progressive_mismatch`, `player_shot_breakdown_mismatch`, `ghost_player`, and `progressive_quarter_mismatch`.
  - Clamps section scores to `[0.0, 1.0]`, computes weighted sum, caps global `score` at `0.49` when `match_status == "error"` and `0.89` when `match_status == "needs_review"`.
  - Assigns `level`: `"low"` (`error` or `score < 0.70`), `"medium"` (`needs_review` or `score < 0.90`), or `"high"`.
- **Exception resilience:** `ValidationEngine.validate` catches unexpected plugin exceptions and records a `"medium"` `"plugin_error"` warning rather than crashing the pipeline.

---

## Run layout, artifacts, and tracing (`types.py`, `artifacts.py`, `tracing.py`)

- **`RunContext.create_run`** (`use_run_layout=True`) creates:
  - `runs/<run_id>/input/` — copy of input image (`ArtifactStore.copy_input()`)
  - `runs/<run_id>/artifacts/` — `output_dir` and `artifacts_dir` (preprocessed sheet, `boxes.json`, `fouls_boxes.json`, section PNGs, enhanced PNGs)
  - `runs/<run_id>/raw/` — directory created for optional raw payload debugging
  - `runs/<run_id>/trace.json` — `RunTracer.write()` output (`steps`, `run_artifacts`, `total_usage`, `result_summary`, ISO timestamps, `duration_ms`)
  - `runs/<run_id>/result.json` — `ArtifactStore.write_result()` final JSON
- **`RunTracer.step`:** Context manager (`with tracer.step(name, section=..., input=...) as trace:`) that records start/finish timestamps, catches exceptions via `trace.fail(...)`, and writes `trace.json` immediately on failure.

---

## Typed error hierarchy (`exceptions.py`)

Every domain failure extends `OcrEngineError` and serializes cleanly via `.to_dict()` (`code`, `message`, `retryable`, optional `phase`, `provider`, `details`) so `packages/api` can translate it to HTTP `422` via `engine_error_response`:

- `ConfigurationError` (`phase="configuration"`, `retryable=False`)
- `InputError` (`phase="input"`, `retryable=False`)
- `PipelineError` → `CroppingError` (`phase="cropping"`), `ExtractionError` (`phase="extraction"`)
- `ProviderError` (`phase="provider"`):
  - Non-retryable: `ProviderAuthError`, `ProviderInvalidResponseError`
  - Retryable (`retryable=True`): `ProviderRateLimitError`, `ProviderTimeoutError`, `ProviderServerError`, `ProviderConnectionError`
- `ValidationEngineError` (`phase="validation"`, `retryable=False`)

---

## Core invariants and change checklist

### Invariants
- **NEVER** import `ocr_engine_api`, `ocr_engine_cli`, `ocr_engine_mcp`, or web/DB SDKs inside `ocr_engine_core`.
- **NEVER** write runtime artifacts inside `packages/` or `outputs/` when `use_run_layout=True`.
- **NEVER** bypass `create_provider` or `PROVIDER_API_KEY_ENV_NAMES` for ad hoc model calls or key lookups.
- **ALWAYS** keep public contracts typed using dataclasses in `types.py` and `config/pipeline_config.py` (no Pydantic in core).

### Core-engine change checklist
- [ ] Pure-Python boundary preserved (`ocr_engine_core` imports zero adapter packages).
- [ ] New pipeline phases exposed on `OcrToolbox` and wrapped in `RunTracer.step(...)`.
- [ ] New `PipelineConfig` options documented in field comments and `.env.example`.
- [ ] Relevant core tests pass: `uv run pytest tests/test_core_contracts.py tests/test_toolbox.py tests/test_validation_confidence.py tests/test_provider_http_base.py`.

---

[← Previous: Repository Map](repository-map.md) | [Next: API, Auth & Supabase →](api-and-auth.md)
