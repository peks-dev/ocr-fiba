# Graph Report - .  (2026-06-16)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1689 nodes · 3781 edges · 102 communities (91 shown, 11 thin omitted)
- Extraction: 81% EXTRACTED · 19% INFERRED · 0% AMBIGUOUS · INFERRED: 732 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `32eb7875`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 94|Community 94]]
- [[_COMMUNITY_Community 95|Community 95]]

## God Nodes (most connected - your core abstractions)
1. `TokenUsage` - 76 edges
2. `RunContext` - 52 edges
3. `ProviderInvalidResponseError` - 48 edges
4. `BoundingBox` - 46 edges
5. `ModelProvider` - 46 edges
6. `PipelineConfig` - 41 edges
7. `OcrToolbox` - 41 edges
8. `ProviderAuthError` - 40 edges
9. `ProviderRateLimitError` - 40 edges
10. `ProviderServerError` - 40 edges

## Surprising Connections (you probably didn't know these)
- `ApiTest` --uses--> `CreateRunRequest`  [INFERRED]
  tests/test_api.py → packages/api/src/ocr_engine_api/schemas.py
- `FakeToolbox` --uses--> `CreateRunRequest`  [INFERRED]
  tests/test_api.py → packages/api/src/ocr_engine_api/schemas.py
- `FakeUploadFile` --uses--> `CreateRunRequest`  [INFERRED]
  tests/test_api.py → packages/api/src/ocr_engine_api/schemas.py
- `RunRepositoryTest` --uses--> `RunRepositoryError`  [INFERRED]
  tests/test_run_repository.py → packages/api/src/ocr_engine_api/services/run_repository.py
- `RunRepositoryTest` --uses--> `RunRepository`  [INFERRED]
  tests/test_run_repository.py → packages/api/src/ocr_engine_api/services/run_repository.py

## Import Cycles
- 1-file cycle: `packages/mcp/src/ocr_engine_mcp/server.py -> packages/mcp/src/ocr_engine_mcp/server.py`
- 1-file cycle: `packages/api/src/ocr_engine_api/main.py -> packages/api/src/ocr_engine_api/main.py`
- 1-file cycle: `packages/core-engine/src/ocr_engine_core/validation/__init__.py -> packages/core-engine/src/ocr_engine_core/validation/__init__.py`
- 2-file cycle: `packages/api/src/ocr_engine_api/auth_api_key.py -> packages/api/src/ocr_engine_api/main.py -> packages/api/src/ocr_engine_api/auth_api_key.py`

## Communities (102 total, 11 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (57): ACCEPTED_IMAGE_TYPES, CaptureClient(), formatFileSize(), INITIAL_STORE, findBestRosterNameMatch(), hasRosterNameMatch(), initials(), levenshtein() (+49 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (29): FastMCP, OcrApiClient, OcrApiError, HTTP client used by the remote MCP adapter., _client(), create_mcp(), _json_resource(), _async_next_actions() (+21 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (44): metadata, metadata, metadata, ACCEPTED_IMAGE_TYPES, CaptureClient(), formatFileSize(), StepState, HistoryClient() (+36 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (48): DetectionMeta, Cropper, Core Cropper — Model-agnostic section detection, validation, and cropping.  This, Sub-crop team fouls from already-cropped team sections.          For each team (, Validate and normalize a list of detected bounding boxes., Validate a single team fouls bounding box., Normalize section names, handling common aliases., Normalize team fouls section name. (+40 more)

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (38): ErrorCode, ExtractionError, PipelineError, Error genérico durante una fase del pipeline., Error durante la fase de extracción de datos., Catálogo de códigos de error machine-readable., _convert_interfaze_team_json(), ExtractionTarget (+30 more)

### Community 5 - "Community 5"
Cohesion: 0.40
Nodes (3): DemoTabs(), tabs, metadata

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (39): Home(), GET(), getSafeNextPath(), ApiKeysPanel(), AuthCard(), links, Nav(), DashboardLayout() (+31 more)

### Community 8 - "Community 8"
Cohesion: 0.10
Nodes (28): ModelProvider, Excepción base y jerarquía para el OCR Engine.  Toda excepción del engine hereda, Any, Path, ModelProvider, ProviderType, BoundingBox, ModelProvider (+20 more)

### Community 9 - "Community 9"
Cohesion: 0.10
Nodes (38): build_final_output(), _coerce_bool(), _compute_points_from_running_score(), _derive_entry_flags(), _derive_fouls_from_cells(), _normalize_foul_cell(), _normalize_foul_code(), _normalize_foul_kind() (+30 more)

### Community 10 - "Community 10"
Cohesion: 0.13
Nodes (28): BaseModel, CreateRunRequest, File, FileResponse, Form, ge, le, CreateRunRequest (+20 more)

### Community 11 - "Community 11"
Cohesion: 0.12
Nodes (8): is_auth_exempt(), is_authorized(), unauthorized_response(), JSONResponse, ApiTest, FakeUploadFile, run_async(), wait_for_status()

### Community 12 - "Community 12"
Cohesion: 0.11
Nodes (23): find_image(), main(), Batch runner: process the entire FIBA scoresheet dataset through the pipeline., Find the .jpg image inside a sheet directory., main(), _output_error(), _output_success(), Entry point for running the FIBA OCR pipeline with model selection. (+15 more)

### Community 13 - "Community 13"
Cohesion: 0.12
Nodes (25): FooterScoreSection(), HeaderSection(), matchWinner(), QUARTERS, SectionProps, TeamPlayersSection(), addProgressiveEvent(), applySuggestion() (+17 more)

### Community 14 - "Community 14"
Cohesion: 0.14
Nodes (26): FooterMarkdownParseError, _is_separator(), _is_table_header(), _map_period(), parse_footer_markdown(), _parse_int_or_null(), _parse_text_or_null(), Footer Markdown parser — converts free-form Markdown from the LLM into the struc (+18 more)

### Community 15 - "Community 15"
Cohesion: 0.08
Nodes (25): Atomicity, Auto-invoke skills, Available first-party skills (located in each package), Branching, Commands (verified to work), Commit format, Domains / packages, Environment setup (+17 more)

### Community 16 - "Community 16"
Cohesion: 0.22
Nodes (8): run_links(), Path, _is_relative_to(), _list_input_files(), Filesystem-backed access to OCR run records., _read_optional_json(), RunRepository, RunRepositoryError

### Community 17 - "Community 17"
Cohesion: 0.12
Nodes (19): Any, DuplicateNumbersPlugin, GhostPlayersPlugin, ProgressiveVsFinalPlugin, QuarterSumsPlugin, Core validation plugins — extraction consistency checks.  These detect errors in, Validate that sum of quarters equals final score for both teams., Validate that the last running_score matches the final score.      Provides diag (+11 more)

### Community 18 - "Community 18"
Cohesion: 0.08
Nodes (24): dependencies, next, react, react-dom, sonner, @supabase/ssr, @supabase/supabase-js, devDependencies (+16 more)

### Community 19 - "Community 19"
Cohesion: 0.17
Nodes (15): ProviderInvalidResponseError, El provider devolvió una respuesta que no se puede interpretar., Any, BoundingBox, Path, TokenUsage, Extract text content from a Gemini response., GlmProvider (+7 more)

### Community 20 - "Community 20"
Cohesion: 0.17
Nodes (13): Any, Path, TokenUsage, OpenrouterProvider, Send a request to OpenRouter and return the parsed response body., Strip markdown code fences commonly wrapped around JSON., Make a call to OpenRouter Chat Completion API., Provider for OpenRouter-hosted models such as google/gemini-3-flash-preview. (+5 more)

### Community 21 - "Community 21"
Cohesion: 0.09
Nodes (22): Branch naming, Branches, Commit messages, Contributing, Dependency direction, Environment, FIBA OCR Engine, Git workflow (+14 more)

### Community 22 - "Community 22"
Cohesion: 0.13
Nodes (14): readDraft(), writeDraft(), ReconcileClient(), ReconcileSectionEditor(), buildSheetSections(), firstActionableSection(), nextSectionId(), SECTION_ORDER (+6 more)

### Community 23 - "Community 23"
Cohesion: 0.14
Nodes (14): Extractor, _emit(), ProviderUsage, Structured response returned by each engine tool operation., Usage reported by a model/provider call., Build usage from TokenUsage or a usage dict., ToolResult, PipelineConfig (+6 more)

### Community 24 - "Community 24"
Cohesion: 0.13
Nodes (12): FastAPI, create_app(), _load_project_env(), Run the API app with uvicorn for the ocr-api console script., Load .env from cwd or the repository root without overriding env vars., run(), ApiSettings, get_api_settings() (+4 more)

### Community 25 - "Community 25"
Cohesion: 0.15
Nodes (10): ArtifactStore, _guess_image_mime_type(), Small filesystem-backed artifact registry for one run., Copy the source image into the run input directory., Write the final engine result to the run result path., Any, Artifact, Path (+2 more)

### Community 26 - "Community 26"
Cohesion: 0.14
Nodes (8): ConfigurationError, InputError, Serializar al formato de respuesta de error estandarizado., Error en la configuración del pipeline (.env, providers, API keys)., Error con la imagen de entrada (no existe, corrupta, formato inválido)., Error interno del motor de validación., ValidationEngineError, Any

### Community 27 - "Community 27"
Cohesion: 0.18
Nodes (12): Any, Path, TokenUsage, QubridProvider, Send a request to the Qubrid API and return the parsed JSON body., Strip markdown code fences commonly wrapped around JSON., Make a call to the Qubrid Chat Completion API., Provider for Qubrid-hosted multimodal models such as Qwen/Qwen3-VL-Flash. (+4 more)

### Community 28 - "Community 28"
Cohesion: 0.18
Nodes (16): ProviderAuthError, ProviderError, ProviderTimeoutError, Error originado en un provider de IA externo., Error de autenticación (401/403) — API key inválida o sin permisos., Timeout en la llamada al provider — reintentable., Any, BoundingBox (+8 more)

### Community 29 - "Community 29"
Cohesion: 0.18
Nodes (15): ProviderRateLimitError, ProviderServerError, Rate limit excedido (429) — reintentable con backoff., Error del lado del servidor (5xx) — reintentable., Any, BoundingBox, Path, TokenUsage (+7 more)

### Community 30 - "Community 30"
Cohesion: 0.16
Nodes (14): ABC, Any, FIBA rules validation plugins — rules of the sport of basketball.  These check t, determine_match_status(), Base types for the validation plugin system.  Defines the ValidationPlugin proto, Determine the overall match status based on warning severities., Base class for validation plugins.      Every plugin must define:     - name: un, ValidationPlugin (+6 more)

### Community 31 - "Community 31"
Cohesion: 0.17
Nodes (19): _apply_clahe(), _apply_gamma(), _enhance_image(), enhance_sections(), _normalize_grid_mode(), Enhancer — Image preprocessing phase for FIBA section crops.  Applies three enha, Remove printed grid lines from a document image using morphological operations., Remove grid lines via inpainting, protect only handwritten marks.      FIBA scor (+11 more)

### Community 32 - "Community 32"
Cohesion: 0.18
Nodes (12): _exception_to_dict(), Collects step traces and persists them as JSON., RunTracer, _sum_usage(), Artifact, A file or structured payload produced by an engine step., Any, Artifact (+4 more)

### Community 33 - "Community 33"
Cohesion: 0.10
Nodes (19): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+11 more)

### Community 34 - "Community 34"
Cohesion: 0.17
Nodes (15): Override the default extractor for a specific section., SectionOverride, build_config(), parse_options_json(), unsupported_upload_type_error(), resolve_runs_dir(), HTTPException, PipelineConfig (+7 more)

### Community 35 - "Community 35"
Cohesion: 0.21
Nodes (13): ProviderConnectionError, Error de conexión (DNS, network unreachable) — reintentable., Any, BoundingBox, Path, TokenUsage, InterfazeProvider, Perform a completion on an image.          If schema is provided, uses structure (+5 more)

### Community 36 - "Community 36"
Cohesion: 0.27
Nodes (18): _apply_inverse_rotation(), _contour_metrics(), _estimate_rotation_angle(), _expand_quad(), _find_best_sheet_contour(), _find_canny_sheet_candidates(), _find_paper_mask_candidates(), _find_sheet_contour() (+10 more)

### Community 37 - "Community 37"
Cohesion: 0.44
Nodes (8): OcrToolbox, Composable OCR operations with structured results and tracing., Any, Artifact, Path, RunContext, RunTracer, ToolResult

### Community 38 - "Community 38"
Cohesion: 0.16
Nodes (13): buildSubmissionPayload(), formatFinalScore(), gameTitle(), sectionMeta(), buildPreview(), SubmitClient(), IssueSeverity, EmptyState() (+5 more)

### Community 39 - "Community 39"
Cohesion: 0.28
Nodes (17): cleanup_run(), get_json(), guess_mime_type(), main(), make_run_id(), parse_args(), parse_json_response(), Any (+9 more)

### Community 40 - "Community 40"
Cohesion: 0.14
Nodes (11): PipelineConfig, Pipeline configuration for model selection per phase., Get the API key for the extractor provider., Resolve the API key for a given provider., Get the override for a section, if any., Get the API key for a section override provider., Configuration object that defines which model/provider to use     for each phase, Get the API key for the cropper provider. (+3 more)

### Community 41 - "Community 41"
Cohesion: 0.11
Nodes (15): ValidationPlugin, get(), get_by_category(), Internal singleton-style registry for validation plugins., Register a validation plugin. Overwrites if name already exists., Get a plugin by name, or None if not found., Get all registered plugins., Get all plugins in a given category. (+7 more)

### Community 42 - "Community 42"
Cohesion: 0.21
Nodes (9): _cache_get(), _cache_set(), Return (account_id, status) from cache if present and not expired., Store a validated key in the cache., Validate an OCR API key from the request.      Returns None on success (request, _unauthorized_response(), validate_api_key(), JSONResponse (+1 more)

### Community 43 - "Community 43"
Cohesion: 0.23
Nodes (10): extract_bearer_token(), FastAPI dependency that verifies a Supabase JWT and returns the payload.      Us, Verify a Supabase session JWT and return normalized user claims.      Supabase p, Extract the Bearer token from the Authorization header., require_supabase_user(), _verify_hs256_token(), verify_supabase_jwt(), _verify_with_supabase_auth_server() (+2 more)

### Community 44 - "Community 44"
Cohesion: 0.21
Nodes (10): Args:             plugins: List of plugin names, "all" for every registered plug, get_all(), get_core_names(), get_names(), Validation Plugin Registry.  Central registry where plugins register themselves., Get all registered plugins., Get all registered plugin names., Get names of all core plugins. (+2 more)

### Community 45 - "Community 45"
Cohesion: 0.13
Nodes (14): 1. Composition root: `create_app()`, 2. Auth is layered, 3. Standard error envelope, 4. Response sanitization, 5. Run repository is filesystem-backed, 6. `/v1/me/*` is Supabase-only, api — AGENTS.md, Auto-invoke skills (per task) (+6 more)

### Community 46 - "Community 46"
Cohesion: 0.13
Nodes (14): 1. Pipeline orchestration is split into "pipeline" and "toolbox", 2. Configuration via `PipelineConfig`, 3. Provider implementations, 4. Validation plugins, 5. Canonical run layout (artifacts), 6. Tracing, Auto-invoke skills (per task), Context (+6 more)

### Community 47 - "Community 47"
Cohesion: 0.13
Nodes (14): 1. Tools wrap `OcrApiClient`, not the core engine, 2. Error mapping via `handle_api_error`, 3. Resources expose run state, 4. Auth via `OCR_API_KEY`, 5. Transport selection, Auto-invoke skills (per task), Context, mcp — AGENTS.md (+6 more)

### Community 48 - "Community 48"
Cohesion: 0.18
Nodes (13): delete_api_key(), find_active_key_by_hash(), get_account_by_supabase_user_id(), list_api_keys(), Delete an API key row. Returns the deleted row when available., List API keys for an account. Returns prefix, name, status, timestamps only., Look up an account by its Supabase user ID., Find an active API key by its hash. Returns the key row or None. (+5 more)

### Community 49 - "Community 49"
Cohesion: 0.18
Nodes (11): generate_api_key(), hash_api_key(), Generate an OCR API key and return (raw_key, key_hash, key_prefix).      The raw, Return the SHA-256 hash of an API key., Insert a new API key record in Supabase and return the stored row., store_api_key(), bootstrap_api_key(), create_api_key() (+3 more)

### Community 50 - "Community 50"
Cohesion: 0.21
Nodes (14): cell_has_ink(), create_ink_masks(), detect_row_positions(), evaluate(), extract_progressive_score(), main(), CV-based Progressive Score Extraction — Isolated test script (v2).  Uses Compute, Create masks for red ink (team_a) and black ink (team_b + dorsals). (+6 more)

### Community 51 - "Community 51"
Cohesion: 0.13
Nodes (14): 1. App Router only, RSC by default, 2. Auth gate lives in `dashboard/layout.tsx`, 3. API calls go through `lib/api.ts`, 4. Toasts via `sonner`, 5. Public docs live under `app/docs/*`, 6. Avoid infinite re-fetch loops in client effects, Auto-invoke skills (per task), Context (+6 more)

### Community 52 - "Community 52"
Cohesion: 0.22
Nodes (13): compare_values(), count_fields(), count_matches(), evaluate_sheet(), main(), print_mismatches(), Any, Evaluate OCR pipeline results against ground truth for all sheets.  Compares eve (+5 more)

### Community 53 - "Community 53"
Cohesion: 0.22
Nodes (9): LeagueClient(), createSubmission(), errorText(), LeagueStoreError, listSubmissions(), safeJson(), LeagueRecord, LeagueSubmissionPayload (+1 more)

### Community 54 - "Community 54"
Cohesion: 0.24
Nodes (6): _duration_ms(), Convert engine values to plain JSON-compatible structures., Audit record for one engine step., StepTrace, to_jsonable(), Any

### Community 55 - "Community 55"
Cohesion: 0.26
Nodes (12): computeReconciliation(), engineTitle(), finalScore(), normalize(), normalizeSeverity(), playerPointsSum(), quarterLabel(), quarterScore() (+4 more)

### Community 56 - "Community 56"
Cohesion: 0.22
Nodes (11): engine_error_response(), error_response(), Any, HTTPException, OcrEngineError, delete_api_key(), _get_account_id(), get_api_keys() (+3 more)

### Community 57 - "Community 57"
Cohesion: 0.23
Nodes (6): Helpers for recording OCR run artifacts., FibaOcrPipeline — Complete pipeline orchestrator (model-agnostic).  This module, Agent-ready tool layer for the FIBA OCR engine.  The toolbox exposes atomic oper, Trace recording for OCR engine runs., _timestamp_iso(), Shared contracts for the OCR engine tool layer.  These types are intentionally l

### Community 58 - "Community 58"
Cohesion: 0.18
Nodes (8): Any, Any, Any, PlayerFoulsPlugin, Validate that no player has more than 5 personal fouls (FIBA rule)., create_warning(), Create a standardized validation warning., Run validations on extracted data. Returns a list of warnings.

### Community 59 - "Community 59"
Cohesion: 0.17
Nodes (11): 1. Each script is a `main()` callable, 2. Reuse core utilities, never reimplement, 3. Use the canonical run layout, Auto-invoke skills (per task), cli — AGENTS.md, Context, Patterns, References (+3 more)

### Community 60 - "Community 60"
Cohesion: 0.17
Nodes (11): OcrFooter, OcrPlayer, OcrTeam, PlayerPoints, QuarterScore, ReconcileIssue, ReconcileSummary, RunStatus (+3 more)

### Community 62 - "Community 62"
Cohesion: 0.33
Nodes (10): _assert_success(), _call_tool_data(), main(), parse_args(), Any, Client, Namespace, Path (+2 more)

### Community 63 - "Community 63"
Cohesion: 0.20
Nodes (9): Adding a new caller, API Key Auth, Constraints (do not violate), Debugging a 401, How validation works, Key format, References, What "active" means (+1 more)

### Community 64 - "Community 64"
Cohesion: 0.20
Nodes (9): Canonical phases, Canonical run layout, Configuration plumbing, Constraints (do not violate), How callers wire in, OCR Run Lifecycle, References, Tracing rule (+1 more)

### Community 65 - "Community 65"
Cohesion: 0.39
Nodes (8): AirtableConfig, AirtableRecord, airtableUrl(), GET(), notConfigured(), POST(), readConfig(), SUBMISSION_FIELDS

### Community 66 - "Community 66"
Cohesion: 0.25
Nodes (7): Adding a new error code, API Error Envelope, Constraints (do not violate), Envelope shape, How to emit, References, When to use

### Community 67 - "Community 67"
Cohesion: 0.36
Nodes (5): Future, Any, Path, PipelineConfig, Submit a local/preview run without holding the HTTP response open.

### Community 68 - "Community 68"
Cohesion: 0.36
Nodes (7): binarize_adaptive(), binarize_otsu(), main(), Binarize a FIBA scoresheet section image for OCR testing.  Standalone utility —, Binarize using adaptive Gaussian thresholding.      Good for images with uneven, Binarize using Otsu's global threshold.      Good for images with even lighting, Path

### Community 69 - "Community 69"
Cohesion: 0.33
Nodes (4): bodyFont, headingFont, metadata, AppToaster()

### Community 70 - "Community 70"
Cohesion: 0.29
Nodes (6): Configuration, MCP Server, Production notes, Run as HTTP server, Run locally (stdio), Tools and resources

### Community 71 - "Community 71"
Cohesion: 0.38
Nodes (4): is_api_key_request(), Check if the request carries a Bearer token that looks like an OCR API key., Request, IsApiKeyRequestTest

### Community 72 - "Community 72"
Cohesion: 0.38
Nodes (4): Remove local filesystem paths from API responses in production., _sanitize(), sanitize_for_public_response(), Any

### Community 73 - "Community 73"
Cohesion: 0.53
Nodes (5): evaluate_sheet(), main(), _norm(), Any, Evaluate header extraction against ground truth.  Usage:     python evaluation/e

### Community 74 - "Community 74"
Cohesion: 0.53
Nodes (5): evaluate_sheet(), _foul_family(), main(), Any, Evaluate individual player foul extraction against ground truth.  This focuses o

### Community 75 - "Community 75"
Cohesion: 0.53
Nodes (5): evaluate_sheet(), _events_by_running_score(), main(), Any, Evaluate progressive_score extraction against ground truth.  Reports running_sco

### Community 76 - "Community 76"
Cohesion: 0.53
Nodes (5): evaluate_sheet(), main(), _norm(), Any, Evaluate team/player identity extraction against ground truth.  Focuses on team.

### Community 77 - "Community 77"
Cohesion: 0.40
Nodes (3): DemoTabs(), steps, metadata

### Community 78 - "Community 78"
Cohesion: 0.40
Nodes (3): DemoTabs(), tabs, metadata

### Community 79 - "Community 79"
Cohesion: 0.50
Nodes (4): evaluate_sheet(), main(), Any, Evaluate player entered/started extraction against ground truth.  Usage:     pyt

### Community 80 - "Community 80"
Cohesion: 0.50
Nodes (4): evaluate_sheet(), main(), Any, Evaluate player points extraction against ground truth.  Usage:     python evalu

### Community 81 - "Community 81"
Cohesion: 0.50
Nodes (3): new_run_id(), Create a compact, sortable-enough run identifier for local executions., Path

### Community 82 - "Community 82"
Cohesion: 0.40
Nodes (4): compat, __dirname, eslintConfig, __filename

### Community 83 - "Community 83"
Cohesion: 0.50
Nodes (3): Deploy on Vercel, Getting Started, Learn More

## Knowledge Gaps
- **227 isolated node(s):** `Any`, `Any`, `JSONResponse`, `Client`, `Path` (+222 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Exception` connect `Community 32` to `Community 1`, `Community 39`, `Community 10`, `Community 16`, `Community 54`, `Community 23`?**
  _High betweenness centrality (0.088) - this node is a cross-community bridge._
- **Why does `OcrToolbox` connect `Community 37` to `Community 32`, `Community 67`, `Community 3`, `Community 4`, `Community 40`, `Community 8`, `Community 10`, `Community 12`, `Community 54`, `Community 23`, `Community 57`, `Community 25`?**
  _High betweenness centrality (0.071) - this node is a cross-community bridge._
- **Why does `OcrApiError` connect `Community 1` to `Community 32`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Are the 65 inferred relationships involving `TokenUsage` (e.g. with `DetectionMeta` and `Extractor`) actually correct?**
  _`TokenUsage` has 65 INFERRED edges - model-reasoned connections that need verification._
- **Are the 45 inferred relationships involving `RunContext` (e.g. with `CreateRunRequest` and `Extractor`) actually correct?**
  _`RunContext` has 45 INFERRED edges - model-reasoned connections that need verification._
- **Are the 30 inferred relationships involving `ProviderInvalidResponseError` (e.g. with `Any` and `BoundingBox`) actually correct?**
  _`ProviderInvalidResponseError` has 30 INFERRED edges - model-reasoned connections that need verification._
- **Are the 37 inferred relationships involving `BoundingBox` (e.g. with `DetectionMeta` and `Cropper`) actually correct?**
  _`BoundingBox` has 37 INFERRED edges - model-reasoned connections that need verification._