# Graph Report - ocr-engine  (2026-11-17)

## Corpus Check
- 222 files · ~91,185 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2033 nodes · 4218 edges · 125 communities (114 shown, 11 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 184 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `58f7516c`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- club-demo/capture-client.tsx
- OcrApiClient
- single-player-demo/capture-client.tsx
- .detect_and_crop_team_fouls
- create_provider
- devDependencies
- HttpJsonProvider
- ProviderInvalidResponseError
- team_markdown_parser.py
- output_builder.py
- runs.py
- ApiTest
- PipelineConfig
- reconcile-sections.tsx
- compilerOptions
- FIBA OCR Engine — AGENTS.md
- api_keys.py
- plugins/__init__.py
- league-store.ts
- extractor.py
- OpenrouterProvider
- Quickstart (local development)
- _StubProvider
- validation/__init__.py
- get_api_settings
- Artifact
- OcrEngineError
- FakeSession
- exceptions.py
- TokenUsage
- MatchStatusTest
- enhance_sections
- StepTrace
- account.ts
- McpTokenVerifier
- reconcile-client.tsx
- preprocessor.py
- OcrToolbox
- api.ts
- smoke_async_api.py
- sanitize_for_public_response
- submit-client.tsx
- auth_api_key.py
- main.py
- ValidationPlugin
- server.py
- api — AGENTS.md
- create_app
- me.py
- generate_api_key
- cv_progressive_score.py
- core-engine — AGENTS.md
- evaluate_dataset.py
- web — AGENTS.md
- ProviderUsage
- ValidationEngine
- validation.ts
- cli — AGENTS.md
- create_warning
- OcrApiError
- deploy_cloudrun.sh
- RunRepository
- smoke_async_mcp.py
- FIBA OCR Engine
- API Key Auth
- OCR Run Lifecycle
- is_api_key_request
- referee.py
- binarize_image.py
- MCP Server
- referee-demo/types.ts
- Cropper
- toolbox.py
- evaluate_header.py
- evaluate_player_fouls.py
- evaluate_progressive_score.py
- evaluate_team_identity.py
- test_grid_removal.py
- API Error Envelope
- evaluate_entry_marks.py
- evaluate_player_points.py
- admin.py
- mcp — AGENTS.md
- resolve_provider_api_key
- evaluation/__init__.py
- evaluation/README.md
- main
- serve.sh
- app/layout.tsx
- Git workflow
- Patterns
- login/page.tsx
- Project conventions (must follow)
- eslint.config.mjs
- ocr-engine-workspace
- McpPathToolTest
- Git workflow
- README.md
- graphify.md
- ocr_engine_api/__init__.py
- services/__init__.py
- next.config.ts
- postcss.config.mjs
- cropper.py
- graphify-check script
- submissions/route.ts
- graphify-update
- create_admin_user.py
- setup-graphify
- FibaOcrPipeline
- tools.py
- ModelProvider
- load_schema
- api_key_for_request
- issue_api_key.py
- QubridProvider

## God Nodes (most connected - your core abstractions)
1. `TokenUsage` - 65 edges
2. `OcrApiClient` - 43 edges
3. `HttpJsonProvider` - 42 edges
4. `RunRepository` - 36 edges
5. `OcrToolbox` - 34 edges
6. `ApiTest` - 34 edges
7. `ValidationPlugin` - 33 edges
8. `create_app()` - 32 edges
9. `RunContext` - 31 edges
10. `get_api_settings()` - 30 edges

## Surprising Connections (you probably didn't know these)
- `PathInputTest` --uses--> `RateLimitBackendError`  [INFERRED]
  tests/test_hardening.py → packages/api/src/ocr_engine_api/rate_limit.py
- `RateLimiterTest` --uses--> `RateLimitBackendError`  [INFERRED]
  tests/test_hardening.py → packages/api/src/ocr_engine_api/rate_limit.py
- `ServerDefaultsTest` --uses--> `RateLimitBackendError`  [INFERRED]
  tests/test_hardening.py → packages/api/src/ocr_engine_api/rate_limit.py
- `PathInputTest` --uses--> `MemoryRateLimitStore`  [INFERRED]
  tests/test_hardening.py → packages/api/src/ocr_engine_api/rate_limit.py
- `RateLimiterTest` --uses--> `MemoryRateLimitStore`  [INFERRED]
  tests/test_hardening.py → packages/api/src/ocr_engine_api/rate_limit.py

## Import Cycles
- None detected.

## Communities (125 total, 11 thin omitted)

### Community 0 - "club-demo/capture-client.tsx"
Cohesion: 0.05
Nodes (60): ACCEPTED_IMAGE_TYPES, CaptureClient(), formatFileSize(), INITIAL_STORE, findBestRosterNameMatch(), hasRosterNameMatch(), initials(), levenshtein() (+52 more)

### Community 1 - "OcrApiClient"
Cohesion: 0.26
Nodes (5): OcrApiClient, Any, Response, Session, HTTP client used by the remote MCP adapter.

### Community 2 - "single-player-demo/capture-client.tsx"
Cohesion: 0.06
Nodes (42): ACCEPTED_IMAGE_TYPES, CaptureClient(), formatFileSize(), StepState, HistoryClient(), ProgressClient(), createSavedGame(), extractPlayers() (+34 more)

### Community 3 - ".detect_and_crop_team_fouls"
Cohesion: 0.09
Nodes (26): Cropper, Path, ProviderType, Sub-crop team fouls from already-cropped team sections.          For each team (, Detect the team-fouls bounding box for one team (network-bound)., Validate and normalize a list of detected bounding boxes., Validate a single team fouls bounding box., Normalize section names, handling common aliases. (+18 more)

### Community 4 - "create_provider"
Cohesion: 0.11
Nodes (14): Any, Path, Detect bounding boxes in an image (used for section cropping).          Args:, Represents token usage from a model call., Perform a completion on an image.          If schema is provided, uses structure, TokenUsage, Extract usage from an OpenAI-compatible ``usage`` object., InterfazeProvider (+6 more)

### Community 5 - "devDependencies"
Cohesion: 0.05
Nodes (38): eslint, eslint-config-next, next, dependencies, next, react, react-dom, sonner (+30 more)

### Community 6 - "HttpJsonProvider"
Cohesion: 0.10
Nodes (19): BoundingBox, Normalized bounding box (0-1000 scale)., HttpJsonProvider, Any, Path, Sleep ``BACKOFF_BASE * 2**(attempt-1)`` (capped) plus jitter., Encode an image as a base64 ``data:`` URI., Encode an image as raw base64 (no data URI prefix). (+11 more)

### Community 7 - "ProviderInvalidResponseError"
Cohesion: 0.07
Nodes (27): ProviderInvalidResponseError, El provider devolvió una respuesta que no se puede interpretar., Core Extractor — Model-agnostic structured extraction from FIBA sections.  This, Prompts detallados para extracción de secciones de hojas FIBA. Migrados desde ex, ModelProvider, ABC, Base abstraction for AI model providers.  This module defines the common interfa, Abstract base class for all model providers.      Each provider (Interfaze, Gemi (+19 more)

### Community 8 - "team_markdown_parser.py"
Cohesion: 0.13
Nodes (27): FooterMarkdownParseError, _is_separator(), _is_table_header(), _map_period(), parse_footer_markdown(), _parse_int_or_null(), _parse_text_or_null(), ValueError (+19 more)

### Community 9 - "output_builder.py"
Cohesion: 0.05
Nodes (58): build_final_output(), _coerce_bool(), _coerce_int(), _compute_points_from_running_score(), _derive_entry_flags(), _derive_fouls_from_cells(), _foul_token(), _is_illegible_entry_mark() (+50 more)

### Community 10 - "runs.py"
Cohesion: 0.14
Nodes (19): BaseModel, File, Form, apply_server_defaults(), build_config(), parse_options_json(), HTTPException, Fill extractor provider/model from server env when the client did not set them. (+11 more)

### Community 11 - "ApiTest"
Cohesion: 0.17
Nodes (5): is_authorized(), ApiTest, FakeUploadFile, run_async(), wait_for_status()

### Community 12 - "PipelineConfig"
Cohesion: 0.09
Nodes (18): find_image(), main(), Path, Batch runner: process the entire FIBA scoresheet dataset through the pipeline., Find the .jpg image inside a sheet directory., PipelineConfig, Pipeline configuration for model selection per phase., Resolve the API key for a given provider. (+10 more)

### Community 13 - "reconcile-sections.tsx"
Cohesion: 0.14
Nodes (30): FooterScoreSection(), HeaderSection(), matchWinner(), ProgressiveScoreSection(), QUARTERS, SectionProps, TeamFoulsSection(), TeamPlayersSection() (+22 more)

### Community 14 - "compilerOptions"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 15 - "FIBA OCR Engine — AGENTS.md"
Cohesion: 0.14
Nodes (14): Auto-invoke skills, Available first-party skills (located in each package), Commands (verified to work), Domains / packages, Engram — memoria técnica compartida, Environment setup, FIBA OCR Engine — AGENTS.md, Graphify — required repository knowledge (+6 more)

### Community 16 - "api_keys.py"
Cohesion: 0.18
Nodes (4): ParsingHelpersTest, Tests for the shared HttpJsonProvider base: retry/backoff and parsing., Minimal concrete provider that records request attempts., _StubProvider

### Community 17 - "plugins/__init__.py"
Cohesion: 0.11
Nodes (21): DuplicateNumbersPlugin, EntryAndFoulsConsistencyPlugin, GhostPlayersPlugin, IllegibleMarksPlugin, _player_shot_counts(), _player_table_points(), PlayerVsProgressivePlugin, ProgressiveSequencePlugin (+13 more)

### Community 18 - "league-store.ts"
Cohesion: 0.16
Nodes (16): AirtableConfig, AirtableRecord, airtableUrl(), GET(), notConfigured(), POST(), readConfig(), SUBMISSION_FIELDS (+8 more)

### Community 19 - "extractor.py"
Cohesion: 0.13
Nodes (18): ErrorCode, ExtractionError, Error durante la fase de extracción de datos., Catálogo de códigos de error machine-readable., _convert_interfaze_team_json(), ExtractionTarget, Extractor, _parse_mark_flag() (+10 more)

### Community 20 - "OpenrouterProvider"
Cohesion: 0.21
Nodes (8): Whether a provider's structured_completion accepts agentic_mode.      Cached per, _supports_agentic_mode(), OpenrouterProvider, Any, Path, Provider for OpenRouter-hosted models such as google/gemini-3-flash-preview., AgenticCapabilityTest, P3 — capability detection is cached per provider class.

### Community 21 - "Quickstart (local development)"
Cohesion: 0.22
Nodes (9): Environment, Install, Prerequisites, Quickstart (local development), Run a CLI OCR job, Run the API, Run the MCP server (stdio), Run the test suite (+1 more)

### Community 22 - "_StubProvider"
Cohesion: 0.25
Nodes (6): Future, Any, Path, Execute OCR runs and update filesystem-backed status., Submit a local/preview run without holding the HTTP response open., RunExecutor

### Community 23 - "validation/__init__.py"
Cohesion: 0.12
Nodes (24): compute_confidence(), determine_match_status(), Base types for the validation plugin system.  Defines the ValidationPlugin proto, Determine the overall match status based on warning severities., Compute a deterministic, explainable confidence summary per section and globally, _section_for_field(), Validation Engine — orchestrates plugin execution and determines match status., Args:             plugins: List of plugin names, "all" for every registered plug (+16 more)

### Community 24 - "get_api_settings"
Cohesion: 0.12
Nodes (7): ApiSettings, _env_bool(), get_api_settings(), Path, resolve_runs_dir(), validate_api_settings(), PathInputTest

### Community 25 - "Artifact"
Cohesion: 0.11
Nodes (14): ArtifactStore, _guess_image_mime_type(), Any, Path, Small filesystem-backed artifact registry for one run., Copy the source image into the run input directory., Write the final engine result to the run result path., Artifact (+6 more)

### Community 26 - "OcrEngineError"
Cohesion: 0.10
Nodes (17): main(), _output_error(), _output_success(), Entry point for running the FIBA OCR pipeline with model selection., Output a successful pipeline result., Output a pipeline error in standardized format., ConfigurationError, InputError (+9 more)

### Community 27 - "FakeSession"
Cohesion: 0.20
Nodes (4): FakeResponse, FakeSession, OcrApiClientTest, Any

### Community 28 - "exceptions.py"
Cohesion: 0.11
Nodes (27): ProviderAuthError, ProviderConnectionError, ProviderError, ProviderRateLimitError, ProviderServerError, ProviderTimeoutError, Excepción base y jerarquía para el OCR Engine.  Toda excepción del engine hereda, Error originado en un provider de IA externo. (+19 more)

### Community 29 - "TokenUsage"
Cohesion: 0.19
Nodes (6): GeminiProvider, Any, Path, Attempt to repair truncated JSON by removing incomplete values and closing struc, Provider for Google Gemini models (via Google AI Studio)., Extract text content from a Gemini response.

### Community 31 - "enhance_sections"
Cohesion: 0.17
Nodes (19): _apply_clahe(), _apply_gamma(), _enhance_image(), enhance_sections(), _normalize_grid_mode(), ndarray, Path, Enhancer — Image preprocessing phase for FIBA section crops.  Applies three enha (+11 more)

### Community 32 - "StepTrace"
Cohesion: 0.13
Nodes (15): Helpers for recording OCR run artifacts., Agent-ready tool layer for the FIBA OCR engine.  The toolbox exposes atomic oper, _to_token_usage(), Trace recording for OCR engine runs., _sum_usage(), _timestamp_iso(), _duration_ms(), ProviderUsage (+7 more)

### Community 33 - "account.ts"
Cohesion: 0.11
Nodes (26): AdminLayout(), AdminPage(), demoLabels, inviteTester(), redirectWithMessage(), POST(), Home(), TestLayout() (+18 more)

### Community 34 - "McpTokenVerifier"
Cohesion: 0.18
Nodes (5): AccessToken, McpTokenVerifier, Accept the static MCP_AUTH_TOKEN or a validated ``ocr_live_`` API key.      ``oc, McpTokenVerifierTest, TokenVerifier

### Community 35 - "reconcile-client.tsx"
Cohesion: 0.13
Nodes (21): DEFAULT_REFEREE_PLUGIN_IDS, pluginLabel(), REFEREE_PLUGINS, RefereePlugin, pluginsFromWarnings(), ReconcileClient(), ReconcileSectionEditor(), buildSheetSections() (+13 more)

### Community 36 - "preprocessor.py"
Cohesion: 0.27
Nodes (18): _apply_inverse_rotation(), _contour_metrics(), _estimate_rotation_angle(), _expand_quad(), _find_best_sheet_contour(), _find_canny_sheet_candidates(), _find_paper_mask_candidates(), _find_sheet_contour() (+10 more)

### Community 37 - "OcrToolbox"
Cohesion: 0.27
Nodes (11): _emit(), OcrToolbox, Any, Path, Composable OCR operations with structured results and tracing., Execution context shared by tool-layer operations., Structured response returned by each engine tool operation., Build usage from TokenUsage or a usage dict. (+3 more)

### Community 38 - "api.ts"
Cohesion: 0.11
Nodes (29): AccountKeysPanel(), ApiKeysPanel(), AccountRecord, ApiEnvelope, apiFetch(), ApiKeyRecord, bootstrapApiKey(), buildHeaders() (+21 more)

### Community 39 - "smoke_async_api.py"
Cohesion: 0.24
Nodes (19): Exception, cleanup_run(), get_json(), guess_mime_type(), main(), make_run_id(), parse_args(), parse_json_response() (+11 more)

### Community 40 - "sanitize_for_public_response"
Cohesion: 0.17
Nodes (17): FileResponse, ge, le, Any, Remove local filesystem paths from API responses in production., _sanitize(), sanitize_for_public_response(), delete_run() (+9 more)

### Community 41 - "submit-client.tsx"
Cohesion: 0.23
Nodes (8): readDraft(), formatFinalScore(), buildPreview(), SubmitClient(), EmptyState(), Panel(), StatusBanner(), TextField()

### Community 42 - "auth_api_key.py"
Cohesion: 0.15
Nodes (12): Fire-and-forget update of last_used_at for an API key., update_last_used_at(), _cache_get(), _cache_set(), JSONResponse, Return (account_id, status) from cache if present and not expired., Store a validated key in the cache., Validate an OCR API key from the request.      Returns None on success (request (+4 more)

### Community 43 - "main.py"
Cohesion: 0.11
Nodes (22): FastAPI, forbidden_response(), is_auth_exempt(), JSONResponse, extract_bearer_token(), is_jwt_request(), JSONResponse, Request (+14 more)

### Community 44 - "ValidationPlugin"
Cohesion: 0.14
Nodes (11): ABC, Base class for validation plugins.      Every plugin must define:     - name: un, ValidationPlugin, Internal singleton-style registry for validation plugins., Register a validation plugin. Overwrites if name already exists., Get a plugin by name, or None if not found., Get all registered plugins., Get all plugins in a given category. (+3 more)

### Community 45 - "server.py"
Cohesion: 0.15
Nodes (10): FastMCP, auth_from_env(), Build the HTTP token verifier from the environment.      When MCP_AUTH_TOKEN is, Remote MCP adapter for the OCR Engine API., create_mcp(), _json_resource(), path_input_allowed(), Any (+2 more)

### Community 46 - "api — AGENTS.md"
Cohesion: 0.12
Nodes (15): 1. Composition root: `create_app()`, 2. Auth is layered, 3. Standard error envelope, 4. Response sanitization, 5. Run repository is filesystem-backed, 6. `/v1/me/*` is Supabase-only, 7. `/v1/admin/*` is admin-only, api — AGENTS.md (+7 more)

### Community 47 - "create_app"
Cohesion: 0.08
Nodes (17): create_app(), _load_project_env(), Load .env from cwd or the repository root without overriding env vars., client_key(), JSONResponse, rate_limit_unavailable_response(), rate_limited_response(), Sliding-window limiter for run creation, keyed per token. A limit of 0 disables (+9 more)

### Community 48 - "me.py"
Cohesion: 0.38
Nodes (4): _exception_to_dict(), Any, Collects step traces and persists them as JSON., RunTracer

### Community 49 - "generate_api_key"
Cohesion: 0.17
Nodes (7): Any, Runs selected validation plugins against extracted data.      Usage:         # D, Run all selected plugins against the data.          Adds 'validation_warnings' a, Names of currently active plugins., ValidationEngine, Unit tests for Phase 1 validation plugins, illegible mark propagation, and confi, ValidationAndConfidenceTest

### Community 50 - "cv_progressive_score.py"
Cohesion: 0.21
Nodes (14): cell_has_ink(), create_ink_masks(), detect_row_positions(), evaluate(), extract_progressive_score(), main(), ndarray, Path (+6 more)

### Community 51 - "core-engine — AGENTS.md"
Cohesion: 0.13
Nodes (14): 1. Pipeline orchestration is split into "pipeline" and "toolbox", 2. Configuration via `PipelineConfig`, 3. Provider implementations, 4. Validation plugins, 5. Canonical run layout (artifacts), 6. Tracing, Auto-invoke skills (per task), Context (+6 more)

### Community 52 - "evaluate_dataset.py"
Cohesion: 0.22
Nodes (13): compare_values(), count_fields(), count_matches(), evaluate_sheet(), main(), print_mismatches(), Any, Evaluate OCR pipeline results against ground truth for all sheets.  Compares eve (+5 more)

### Community 53 - "web — AGENTS.md"
Cohesion: 0.13
Nodes (14): 1. App Router only, RSC by default, 2. Auth and role gates live in shared layouts/helpers, 3. API calls go through `lib/api.ts`, 4. Toasts via `sonner`, 5. Public docs live under `app/docs/*`, 6. Avoid infinite re-fetch loops in client effects, Auto-invoke skills (per task), Context (+6 more)

### Community 54 - "ProviderUsage"
Cohesion: 0.19
Nodes (15): get_account_by_id(), list_api_keys(), List API keys for an account. Returns prefix, name, status, timestamps only., Look up an account by its internal ID., engine_error_response(), error_response(), Any, HTTPException (+7 more)

### Community 55 - "ValidationEngine"
Cohesion: 0.17
Nodes (10): ClubDemoLayout(), metadata, metadata, PlayerDemoLayout(), metadata, RefereeDemoLayout(), DemoTabs(), DemoTabs() (+2 more)

### Community 56 - "validation.ts"
Cohesion: 0.31
Nodes (13): computeReconciliation(), engineTitle(), finalScore(), normalize(), normalizeSeverity(), playerPointsSum(), quarterLabel(), quarterScore() (+5 more)

### Community 57 - "cli — AGENTS.md"
Cohesion: 0.17
Nodes (11): 1. Each script is a `main()` callable, 2. Reuse core utilities, never reimplement, 3. Use the canonical run layout, Auto-invoke skills (per task), cli — AGENTS.md, Context, Patterns, References (+3 more)

### Community 58 - "create_warning"
Cohesion: 0.18
Nodes (10): create_warning(), Any, Run validations on extracted data. Returns a list of warnings., Create a standardized validation warning., PlayerFoulsPlugin, Any, FIBA rules validation plugins — rules of the sport of basketball.  These check t, Validate that no player has more than 5 personal fouls (FIBA rule). (+2 more)

### Community 59 - "OcrApiError"
Cohesion: 0.21
Nodes (6): probe_ocr_api_key(), Session, Return True when the OCR API accepts ``token`` as a bearer key.      Uses GET /v, OcrApiError, Exception, ProbeOcrApiKeyTest

### Community 60 - "deploy_cloudrun.sh"
Cohesion: 0.31
Nodes (11): build(), deploy_api(), deploy_mcp(), ensure_secret(), g(), grant_secret_access(), infra(), secret_exists() (+3 more)

### Community 61 - "RunRepository"
Cohesion: 0.13
Nodes (10): run_links(), _is_relative_to(), _list_input_files(), Exception, Path, Filesystem-backed access to OCR run records., _read_optional_json(), RunRepository (+2 more)

### Community 62 - "smoke_async_mcp.py"
Cohesion: 0.33
Nodes (10): _assert_success(), _call_tool_data(), main(), parse_args(), Any, Client, Namespace, Path (+2 more)

### Community 63 - "FIBA OCR Engine"
Cohesion: 0.33
Nodes (6): Contributing, Dependency direction, FIBA OCR Engine, License, Per-package documentation, Repository layout

### Community 64 - "API Key Auth"
Cohesion: 0.20
Nodes (9): Adding a new caller, API Key Auth, Constraints (do not violate), Debugging a 401, How validation works, Key format, References, What "active" means (+1 more)

### Community 65 - "OCR Run Lifecycle"
Cohesion: 0.20
Nodes (9): Canonical phases, Canonical run layout, Configuration plumbing, Constraints (do not violate), How callers wire in, OCR Run Lifecycle, References, Tracing rule (+1 more)

### Community 66 - "is_api_key_request"
Cohesion: 0.33
Nodes (4): is_api_key_request(), Request, Return True when the Bearer token is a per-client ``ocr_live_`` API key.      Th, IsApiKeyRequestTest

### Community 67 - "referee.py"
Cohesion: 0.25
Nodes (6): PlayerPointsSumPlugin, Any, Referee use-case validation plugins — checks useful for officials verifying the, Validate that sum of individual player points equals team final score., Validate that the declared winner has the higher final score., WinnerConsistencyPlugin

### Community 68 - "binarize_image.py"
Cohesion: 0.36
Nodes (7): binarize_adaptive(), binarize_otsu(), main(), Path, Binarize a FIBA scoresheet section image for OCR testing.  Standalone utility —, Binarize using adaptive Gaussian thresholding.      Good for images with uneven, Binarize using Otsu's global threshold.      Good for images with even lighting

### Community 69 - "MCP Server"
Cohesion: 0.20
Nodes (10): Bearer auth on HTTP transport, Configuration, Continuous deployment (push to `main`), MCP Server, Production notes, Public deployment (Google Cloud Run), Run API + MCP as background services, Run as HTTP server (+2 more)

### Community 70 - "referee-demo/types.ts"
Cohesion: 0.14
Nodes (13): IssueSeverity, OcrFooter, OcrPlayer, OcrResult, OcrTeam, PlayerPoints, ProgressiveEvent, QuarterKey (+5 more)

### Community 71 - "Cropper"
Cohesion: 0.18
Nodes (13): delete_api_key(), find_active_key_by_hash(), list_accounts(), List all accounts (admin use). Emails are included for the admin picker., Find an active API key by its hash. Returns the key row or None., Insert a new API key record in Supabase and return the stored row., Delete an API key row. Returns the deleted row when available., store_api_key() (+5 more)

### Community 72 - "toolbox.py"
Cohesion: 0.25
Nodes (8): getSafeNextPath(), LoginPayload, POST(), QuickstartPage(), assertBrowserEnv(), siteConfig, createClient(), createClient()

### Community 73 - "evaluate_header.py"
Cohesion: 0.53
Nodes (5): evaluate_sheet(), main(), _norm(), Any, Evaluate header extraction against ground truth.  Usage:     python evaluation/e

### Community 74 - "evaluate_player_fouls.py"
Cohesion: 0.53
Nodes (5): evaluate_sheet(), _foul_family(), main(), Any, Evaluate individual player foul extraction against ground truth.  This focuses o

### Community 75 - "evaluate_progressive_score.py"
Cohesion: 0.53
Nodes (5): evaluate_sheet(), _events_by_running_score(), main(), Any, Evaluate progressive_score extraction against ground truth.  Reports running_sco

### Community 76 - "evaluate_team_identity.py"
Cohesion: 0.53
Nodes (5): evaluate_sheet(), main(), _norm(), Any, Evaluate team/player identity extraction against ground truth.  Focuses on team.

### Community 77 - "test_grid_removal.py"
Cohesion: 0.21
Nodes (16): compare_with_gt(), extract_progressive_score(), isolate_colored_ink(), main(), ndarray, Path, Test: Preprocessing variants for progressive_score section.  Compares multiple p, Extract only colored ink (red/blue handwriting) onto a clean background. (+8 more)

### Community 78 - "API Error Envelope"
Cohesion: 0.25
Nodes (7): Adding a new error code, API Error Envelope, Constraints (do not violate), Envelope shape, How to emit, References, When to use

### Community 79 - "evaluate_entry_marks.py"
Cohesion: 0.50
Nodes (4): evaluate_sheet(), main(), Any, Evaluate player entered/started extraction against ground truth.  Usage:     pyt

### Community 80 - "evaluate_player_points.py"
Cohesion: 0.50
Nodes (4): evaluate_sheet(), main(), Any, Evaluate player points extraction against ground truth.  Usage:     python evalu

### Community 81 - "admin.py"
Cohesion: 0.18
Nodes (8): AccountPayload, AccountRole, AssignedDemo, demoHomePaths, demoLabels, destinationForAccount(), InviteSetupCard(), InviteStatus

### Community 82 - "mcp — AGENTS.md"
Cohesion: 0.25
Nodes (8): Auto-invoke skills (per task), Context, mcp — AGENTS.md, References, Rules specific to mcp, Stack, Structure, Tools and resources (current)

### Community 83 - "resolve_provider_api_key"
Cohesion: 0.22
Nodes (12): get_account_by_supabase_user_id(), Look up an account by its Supabase user ID., bootstrap_api_key(), create_api_key(), delete_api_key(), _get_account_id(), get_api_keys(), Resolve the internal account ID from a Supabase JWT payload. (+4 more)

### Community 86 - "main"
Cohesion: 0.43
Nodes (7): fail(), is_sensitive(), main(), md5_file(), Any, Path, source_locations()

### Community 87 - "serve.sh"
Cohesion: 0.50
Nodes (6): ensure_token(), is_running(), print_urls(), serve.sh script, start_service(), stop_service()

### Community 88 - "app/layout.tsx"
Cohesion: 0.33
Nodes (4): bodyFont, headingFont, metadata, AppToaster()

### Community 89 - "Git workflow"
Cohesion: 0.29
Nodes (7): Branch naming, Branches, Commit messages, Git workflow, Lifecycle of a change, Releases and tags, Rules of thumb

### Community 90 - "Patterns"
Cohesion: 0.33
Nodes (6): 1. Tools wrap `OcrApiClient`, not the core engine, 2. Error mapping via `handle_api_error`, 3. Resources expose run state, 4. Auth: static MCP token or per-client `ocr_live_` keys, 5. Transport selection, Patterns

### Community 91 - "login/page.tsx"
Cohesion: 0.47
Nodes (3): flowSteps, AuthCard(), getSafeNextPath()

### Community 92 - "Project conventions (must follow)"
Cohesion: 0.40
Nodes (5): FastAPI (api package), MCP, Next.js (web package), Project conventions (must follow), Python

### Community 93 - "eslint.config.mjs"
Cohesion: 0.40
Nodes (4): compat, __dirname, eslintConfig, __filename

### Community 94 - "ocr-engine-workspace"
Cohesion: 0.60
Nodes (5): ocr-engine-api, ocr-engine-cli, ocr-engine-core, ocr-engine-mcp, ocr-engine-workspace

### Community 95 - "McpPathToolTest"
Cohesion: 0.06
Nodes (25): create_rate_limit_store(), is_run_creation(), MemoryRateLimitStore, parse_consume_rate_limit_payload(), Any, Exception, Path, RateLimitBackendError (+17 more)

### Community 96 - "Git workflow"
Cohesion: 0.50
Nodes (4): Atomicity, Branching, Commit format, Git workflow

### Community 97 - "README.md"
Cohesion: 0.20
Nodes (5): Deploy on Vercel, Local development, Optional environment variables, packages/web, Required environment variables

### Community 105 - "cropper.py"
Cohesion: 0.15
Nodes (14): Core Cropper — Model-agnostic section detection, validation, and cropping.  This, Prompts for the Cropping phase (bounding box detection for main sections)., Prompts for the Team Fouls sub-cropping phase (bounding box detection within tea, guess_mime_type(), load_dotenv(), ndarray, Path, Shared image and environment utilities. (+6 more)

### Community 109 - "submissions/route.ts"
Cohesion: 0.23
Nodes (6): ACCEPTED_IMAGE_TYPES, buttonLabel(), CaptureClient(), formatFileSize(), writeDraft(), RunRecord

### Community 111 - "create_admin_user.py"
Cohesion: 0.43
Nodes (6): find_user_by_email(), main(), parse_args(), Any, Namespace, require_env()

### Community 118 - "FibaOcrPipeline"
Cohesion: 0.23
Nodes (7): FibaOcrPipeline, Any, Path, Save the result JSON to a file., Pipeline completo para procesar hojas de anotación FIBA.     Usa la arquitectura, Run the full pipeline on a FIBA scoresheet image.          Args:             ima, _to_token_usage()

### Community 119 - "tools.py"
Cohesion: 0.44
Nodes (12): OcrApiError, _async_next_actions(), handle_api_error(), inspect_run(), poll_run(), process_submit_response(), Any, _resources() (+4 more)

### Community 120 - "ModelProvider"
Cohesion: 0.33
Nodes (5): generate_api_key(), hash_api_key(), Generate an OCR API key and return (raw_key, key_hash, key_prefix).      The raw, Return the SHA-256 hash of an API key., GenerateApiKeyTest

### Community 121 - "load_schema"
Cohesion: 0.33
Nodes (10): _convert_dict(), _convert_node(), _convert_type(), load_schema(), Any, Centralized schemas for the FIBA OCR pipeline.  Schemas are stored in canonical, Convert type field from canonical to Gemini format.      Returns:         Tuple, Load a JSON schema by name, optionally converting for a specific provider. (+2 more)

### Community 122 - "api_key_for_request"
Cohesion: 0.32
Nodes (5): api_key_for_request(), API key to send upstream: the caller's ``ocr_live_`` token, else OCR_API_KEY., _client(), Build an API client that forwards the caller's ocr_live_ key when present., ApiKeyForRequestTest

### Community 123 - "issue_api_key.py"
Cohesion: 0.43
Nodes (7): find_user_by_email(), main(), parse_args(), Any, Namespace, require_env(), resolve_user_id()

### Community 124 - "QubridProvider"
Cohesion: 0.39
Nodes (6): config, middleware(), destinationForMiddlewareAccount(), getAccountForUser(), MiddlewareAccount, updateSession()

## Knowledge Gaps
- **238 isolated node(s):** `ocr-engine-mcp`, `__filename`, `__dirname`, `compat`, `eslintConfig` (+233 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TokenUsage` connect `create_provider` to `StepTrace`, `.detect_and_crop_team_fouls`, `OcrToolbox`, `HttpJsonProvider`, `ProviderInvalidResponseError`, `cropper.py`, `output_builder.py`, `PipelineConfig`, `api_keys.py`, `extractor.py`, `OpenrouterProvider`, `FibaOcrPipeline`, `exceptions.py`, `TokenUsage`, `MatchStatusTest`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Why does `generate_api_key()` connect `ModelProvider` to `Cropper`, `auth_api_key.py`, `resolve_provider_api_key`, `ProviderUsage`, `issue_api_key.py`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Why does `ValidationPlugin` connect `ValidationPlugin` to `referee.py`, `generate_api_key`, `plugins/__init__.py`, `validation/__init__.py`, `create_warning`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **Are the 19 inferred relationships involving `TokenUsage` (e.g. with `Cropper` and `ExtractionTarget`) actually correct?**
  _`TokenUsage` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `OcrApiClient` (e.g. with `McpTokenVerifier` and `FakeResponse`) actually correct?**
  _`OcrApiClient` has 4 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `HttpJsonProvider` (e.g. with `GeminiProvider` and `GlmProvider`) actually correct?**
  _`HttpJsonProvider` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `RunRepository` (e.g. with `RunExecutor` and `RunRepositoryTest`) actually correct?**
  _`RunRepository` has 2 INFERRED edges - model-reasoned connections that need verification._