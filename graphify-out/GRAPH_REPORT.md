# Graph Report - ocr-engine  (2026-11-18)

## Corpus Check
- 257 files · ~105,351 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2045 nodes · 4622 edges · 118 communities (109 shown, 9 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 287 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
-   Init  
- Evaluate Dataset
- Evaluate Entry Marks
- Evaluate Header
- Evaluate Player Fouls
- Evaluate Player Points
- Evaluate Progressive Score
- Evaluate Team Identity
- Server
- Pyproject
-   Init  
- Api Keys
- Test Auth
- Me
- Auth Api Key
- Auth Supabase
- Test Api
- Test Auth
- API Key Cache & Stub
- FastAPI App & Auth Docs
- Test Hardening
- Runs
- Rate Limit
- Async Run Execution & Repo
- Test Api
-   Init  
- Core Pipeline Docs
- Image Utils
- Cv Progressive Score
- Run Dataset
- CLI & Adapters Docs
- Tracing
- Artifact Store
- Pipeline Config
- Cropper
- Cropper
- Cropper
- Cropper
- Test Phase2 Quality
- Enhancer
- Test Provider Http Base
- Exceptions
- Extractor
- Interfaze
- Output Builder
- FibaOcrPipeline Orchestrator
- Preprocessor
- Docstrange
- Base
- Gemini
- Http Base
- Openrouter
- Qubrid
- Toolbox
- Tracing
- Ocr Engine Core Types
- Ocr Engine Core Types
- Image Utils
- Registry
- Base
- Fiba Rules
- Registry
- Validation Engine & Plugins
- Plugins Core
- Test Mcp Auth
- MCP Auth Verifier
- MCP HTTP Client
- Tools
- Eslint.Config
- Next.Config
- Package
- Postcss.Config
- Api
- Nav
- Admin Page
- Submissions Route
- Account
- Invite-Setup-Card
- App Layout
- Login Page
- Result-Utils
- Club Layout
- Stats-Utils
- Plugins
- League-Store
- Sections
- Ui
- Referee Demo Types
- Reconcile-Utils
- Validation
- Origin
- Env
- Middleware
- Tsconfig
- Tsconfig.Test
- Create Admin User
- Deploy Cloudrun
- Graphify-Check
- Graphify-Update
- Graphify Check
- Issue Api Key
- Serve
- Setup-Graphify
- Smoke Async Api
- Smoke Async Mcp
- Test Grid Removal
- Test Mcp Client
- Docs
- Repo Guardrails & Contributing
- Cloud Run & Vercel Deployment

## God Nodes (most connected - your core abstractions)
1. `TokenUsage` - 68 edges
2. `OcrApiClient` - 55 edges
3. `RunRepository` - 45 edges
4. `OcrToolbox` - 45 edges
5. `HttpJsonProvider` - 42 edges
6. `RunContext` - 35 edges
7. `get_api_settings()` - 34 edges
8. `ValidationPlugin` - 34 edges
9. `ApiTest` - 34 edges
10. `create_app()` - 33 edges

## Surprising Connections (you probably didn't know these)
- `Seven-Phase FIBA OCR Pipeline Flow` --references--> `OcrToolbox`  [EXTRACTED]
  docs/ARCHITECTURE.md → packages/core-engine/src/ocr_engine_core/toolbox.py
- `Middleware JSONResponse vs FastAPI HTTPException(detail=...) Split` --conceptually_related_to--> `OcrApiClient`  [INFERRED]
  skills/api-error-envelope/SKILL.md → packages/mcp/src/ocr_engine_mcp/client.py
- `60s Key Cache & Mandatory Eviction on Delete` --rationale_for--> `invalidate_api_key_cache()`  [EXTRACTED]
  skills/api-key-auth/SKILL.md → packages/api/src/ocr_engine_api/auth_api_key.py
- `Skill: api-key-auth` --references--> `validate_api_key()`  [EXTRACTED]
  skills/api-key-auth/SKILL.md → packages/api/src/ocr_engine_api/auth_api_key.py
- `Skill: api-key-auth` --references--> `validate_supabase_session()`  [EXTRACTED]
  skills/api-key-auth/SKILL.md → packages/api/src/ocr_engine_api/auth_supabase.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Engram-Style Layered Documentation Architecture** — readme_md_landing, docs_md_technical_reference, docs_codebase_guide_landing, agents_md_root_index [INFERRED 0.95]
- **Centralized Agent Skills & Package Stub System** — agents_md_root_index, skills_catalog_index, packages_core_engine_agents_stub, packages_api_agents_stub [INFERRED 0.95]

## Communities (118 total, 9 thin omitted)

### Community 50 - "Evaluate Dataset"
Cohesion: 0.19
Nodes (14): compare_values(), Any, count_fields(), count_matches(), evaluate_sheet(), print_mismatches(), main(), Evaluate OCR pipeline results against ground truth for all sheets.  Compares eve (+6 more)

### Community 97 - "Evaluate Entry Marks"
Cohesion: 0.50
Nodes (4): evaluate_sheet(), Any, main(), Evaluate player entered/started extraction against ground truth.  Usage:     pyt

### Community 91 - "Evaluate Header"
Cohesion: 0.53
Nodes (5): _norm(), Any, evaluate_sheet(), main(), Evaluate header extraction against ground truth.  Usage:     python evaluation/e

### Community 92 - "Evaluate Player Fouls"
Cohesion: 0.53
Nodes (5): _foul_family(), Any, evaluate_sheet(), main(), Evaluate individual player foul extraction against ground truth.  This focuses o

### Community 98 - "Evaluate Player Points"
Cohesion: 0.50
Nodes (4): evaluate_sheet(), Any, main(), Evaluate player points extraction against ground truth.  Usage:     python evalu

### Community 93 - "Evaluate Progressive Score"
Cohesion: 0.53
Nodes (5): _events_by_running_score(), Any, evaluate_sheet(), main(), Evaluate progressive_score extraction against ground truth.  Reports running_sco

### Community 94 - "Evaluate Team Identity"
Cohesion: 0.53
Nodes (5): _norm(), Any, evaluate_sheet(), main(), Evaluate team/player identity extraction against ground truth.  Focuses on team.

### Community 33 - "Server"
Cohesion: 0.13
Nodes (13): Remote MCP adapter for the OCR Engine API., auth_from_env(), Build the HTTP token verifier from the environment.      When MCP_AUTH_TOKEN is, create_mcp(), FastMCP, path_input_allowed(), _client(), _call_with_client() (+5 more)

### Community 100 - "Pyproject"
Cohesion: 0.60
Nodes (5): ocr-engine-api, ocr-engine-cli, ocr-engine-core, ocr-engine-mcp, ocr-engine-workspace

### Community 27 - "Api Keys"
Cohesion: 0.15
Nodes (20): store_api_key(), delete_api_key(), get_account_by_supabase_user_id(), get_account_by_id(), list_accounts(), Insert a new API key record in Supabase and return the stored row., Delete an API key row. Returns the deleted row when available., Look up an account by its Supabase user ID. (+12 more)

### Community 66 - "Test Auth"
Cohesion: 0.24
Nodes (6): generate_api_key(), hash_api_key(), Generate an OCR API key and return (raw_key, key_hash, key_prefix).      The raw, Return the SHA-256 hash of an API key., GenerateApiKeyTest, UpdateLastUsedAtTest

### Community 41 - "Me"
Cohesion: 0.18
Nodes (17): list_api_keys(), List API keys for an account. Returns prefix, name, status, timestamps only., error_response(), Any, HTTPException, engine_error_response(), _get_account_id(), bootstrap_api_key() (+9 more)

### Community 34 - "Auth Api Key"
Cohesion: 0.15
Nodes (13): find_active_key_by_hash(), update_last_used_at(), Find an active API key by its hash. Returns the key row or None., Fire-and-forget update of last_used_at for an API key., _cache_get(), _cache_set(), validate_api_key(), JSONResponse (+5 more)

### Community 8 - "Auth Supabase"
Cohesion: 0.10
Nodes (27): is_auth_exempt(), unauthorized_response(), JSONResponse, forbidden_response(), verify_supabase_jwt(), _verify_hs256_token(), _jwt_cache_key(), _jwt_cache_get() (+19 more)

### Community 17 - "Test Api"
Cohesion: 0.10
Nodes (10): is_authorized(), ApiSettings, get_api_settings(), validate_api_settings(), resolve_runs_dir(), Path, _env_bool(), True when the service-role client can be constructed (URL + service key). (+2 more)

### Community 77 - "Test Auth"
Cohesion: 0.33
Nodes (4): is_api_key_request(), Request, Return True when the Bearer token is a per-client ``ocr_live_`` API key.      Th, IsApiKeyRequestTest

### Community 83 - "API Key Cache & Stub"
Cohesion: 0.25
Nodes (8): invalidate_api_key_cache(), Evict cached API keys by key_hash or account_id after revocation/deletion., delete_account_api_key(), Permanently delete an API key belonging to the given account., packages/api/AGENTS.md (API Guardrails Stub), Skill: api-error-envelope, Skill: api-key-auth, 60s Key Cache & Mandatory Eviction on Delete

### Community 9 - "FastAPI App & Auth Docs"
Cohesion: 0.08
Nodes (15): create_app(), _load_project_env(), Load .env from cwd or the repository root without overriding env vars., is_run_creation(), RunRateLimiter, rate_limited_response(), JSONResponse, rate_limit_unavailable_response() (+7 more)

### Community 22 - "Test Hardening"
Cohesion: 0.14
Nodes (14): apply_server_defaults(), build_config(), parse_options_json(), Fill extractor provider/model/reasoning from server env when the client did not, SectionOverrideRequest, BaseModel, PipelineOptions, parse_cors_origins() (+6 more)

### Community 20 - "Runs"
Cohesion: 0.12
Nodes (21): unsupported_upload_type_error(), HTTPException, sanitize_for_public_response(), Any, _sanitize(), Remove local filesystem paths from API responses in production., create_run(), upload_and_create_run() (+13 more)

### Community 5 - "Rate Limit"
Cohesion: 0.07
Nodes (24): client_key(), request_rate_limit_key(), RateLimitBackendError, Exception, RateLimitDecision, RateLimitStore, Protocol, MemoryRateLimitStore (+16 more)

### Community 4 - "Async Run Execution & Repo"
Cohesion: 0.09
Nodes (15): run_links(), RunRepositoryError, Exception, RunRepository, Path, _read_optional_json(), _list_input_files(), _is_relative_to() (+7 more)

### Community 15 - "Test Api"
Cohesion: 0.11
Nodes (16): list_runs(), Query, ge, le, get_run(), delete_run(), get_run_trace(), get_run_result() (+8 more)

### Community 14 - "Core Pipeline Docs"
Cohesion: 0.10
Nodes (17): Path, Future, Any, Submit a local/preview run without holding the HTTP response open., PipelineConfig, Configuration object that defines which model/provider to use     for each phase, Get the API key for the cropper provider., Get the API key for the extractor provider. (+9 more)

### Community 45 - "Image Utils"
Cohesion: 0.18
Nodes (16): binarize_adaptive(), Path, binarize_otsu(), main(), Binarize a FIBA scoresheet section image for OCR testing.  Standalone utility —, Binarize using adaptive Gaussian thresholding.      Good for images with uneven, Binarize using Otsu's global threshold.      Good for images with even lighting, Path (+8 more)

### Community 54 - "Cv Progressive Score"
Cohesion: 0.21
Nodes (14): detect_row_positions(), ndarray, create_ink_masks(), cell_has_ink(), extract_progressive_score(), Path, evaluate(), main() (+6 more)

### Community 78 - "Run Dataset"
Cohesion: 0.28
Nodes (8): find_image(), Path, main(), Batch runner: process the entire FIBA scoresheet dataset through the pipeline., Find the .jpg image inside a sheet directory., resolve_default_extractor(), ProviderType, Resolve the default extractor provider/model from overrides or env vars.      Re

### Community 76 - "CLI & Adapters Docs"
Cohesion: 0.31
Nodes (7): _output_success(), _output_error(), main(), Entry point for running the FIBA OCR pipeline with model selection., Output a successful pipeline result., Output a pipeline error in standardized format., packages/cli/AGENTS.md (CLI Guardrails Stub)

### Community 58 - "Tracing"
Cohesion: 0.21
Nodes (7): Helpers for recording OCR run artifacts., FibaOcrPipeline — Complete pipeline orchestrator (model-agnostic).  This module, Agent-ready tool layer for the FIBA OCR engine.  The toolbox exposes atomic oper, _timestamp_iso(), Trace recording for OCR engine runs., Shared contracts for the OCR engine tool layer.  These types are intentionally l, toolbox_usage()

### Community 35 - "Artifact Store"
Cohesion: 0.16
Nodes (10): ArtifactStore, Path, Any, _guess_image_mime_type(), Small filesystem-backed artifact registry for one run., Copy the source image into the run input directory., Write the final engine result to the run result path., Artifact (+2 more)

### Community 68 - "Pipeline Config"
Cohesion: 0.25
Nodes (9): default_extractor_reasoning(), Any, parse_reasoning_config(), resolve_default_extractor_reasoning(), build_reasoning_config(), Return a fresh copy of the default extractor reasoning config., Parse ``OCR_DEFAULT_EXTRACTOR_REASONING`` into ``(is_set, reasoning_dict)``., Resolve OpenRouter reasoning config for the given extractor provider/model. (+1 more)

### Community 95 - "Cropper"
Cohesion: 0.33
Nodes (3): Core Cropper — Model-agnostic section detection, validation, and cropping.  This, Prompts for the Cropping phase (bounding box detection for main sections)., Prompts for the Team Fouls sub-cropping phase (bounding box detection within tea

### Community 25 - "Cropper"
Cohesion: 0.16
Nodes (15): Cropper, Path, Any, Responsible for detecting and cropping sections from a FIBA scoresheet image., Detect main sections, validate bounding boxes, and crop.          Detection and, Sub-crop team fouls from already-cropped team sections.          For each team (, Detect the team-fouls bounding box for one team (network-bound)., Crop sections from the source image based on validated bounding boxes. (+7 more)

### Community 69 - "Cropper"
Cohesion: 0.18
Nodes (6): SectionName, Validate and normalize a list of detected bounding boxes., Validate a single team fouls bounding box., Normalize section names, handling common aliases., Normalize team fouls section name., Validate that normalized coordinates are in 0..1000 range and box is valid.

### Community 42 - "Test Phase2 Quality"
Cohesion: 0.19
Nodes (13): Convert a normalized (0-1000) bounding box to pixel coordinates., ErrorCode, CroppingError, Catálogo de códigos de error machine-readable., Error durante la fase de detección y recorte de secciones., BoundingBox, Normalized bounding box (0-1000 scale)., PreprocessorSingleWriteTest (+5 more)

### Community 38 - "Enhancer"
Cohesion: 0.17
Nodes (19): _apply_gamma(), ndarray, _apply_clahe(), _remove_grid_lines(), _remove_grid_protect_handwriting(), _enhance_image(), _upscale_dense_progressive_score(), _normalize_grid_mode() (+11 more)

### Community 10 - "Test Provider Http Base"
Cohesion: 0.12
Nodes (21): ProviderError, ProviderAuthError, ProviderRateLimitError, ProviderTimeoutError, ProviderServerError, ProviderConnectionError, Excepción base y jerarquía para el OCR Engine.  Toda excepción del engine hereda, Error originado en un provider de IA externo. (+13 more)

### Community 19 - "Exceptions"
Cohesion: 0.11
Nodes (13): OcrEngineError, Exception, Any, ConfigurationError, InputError, PipelineError, ValidationEngineError, Excepción base de todo el OCR Engine.      Atributos:         message: Descripci (+5 more)

### Community 1 - "Extractor"
Cohesion: 0.05
Nodes (56): ExtractionError, Error durante la fase de extracción de datos., ExtractionTarget, Extractor, Any, ProviderType, Path, _supports_agentic_mode() (+48 more)

### Community 11 - "Interfaze"
Cohesion: 0.09
Nodes (23): ProviderInvalidResponseError, El provider devolvió una respuesta que no se puede interpretar., create_provider(), ProviderType, Provider factory — centralized creation of ModelProvider instances., Create a ModelProvider instance from configuration.      Extra kwargs are passed, ABC, Base abstraction for AI model providers.  This module defines the common interfa (+15 more)

### Community 3 - "Output Builder"
Cohesion: 0.06
Nodes (52): _strip_diacritics(), _normalize_string(), _normalize_judge_name(), _reassign_periods_from_footer(), Any, _compute_points_from_running_score(), _coerce_int(), _normalize_strings_in_obj() (+44 more)

### Community 59 - "FibaOcrPipeline Orchestrator"
Cohesion: 0.21
Nodes (7): FibaOcrPipeline, Path, Any, Pipeline completo para procesar hojas de anotación FIBA.     Usa la arquitectura, Run the full pipeline on a FIBA scoresheet image.          Args:             ima, Save the result JSON to a file., Build TokenUsage from another TokenUsage, ProviderUsage, dict, or None.

### Community 43 - "Preprocessor"
Cohesion: 0.27
Nodes (18): _order_points(), ndarray, _expand_quad(), _contour_metrics(), _score_sheet_candidate(), _find_canny_sheet_candidates(), _find_paper_mask_candidates(), _select_best_sheet_contour() (+10 more)

### Community 23 - "Docstrange"
Cohesion: 0.13
Nodes (15): TokenUsage, Represents token usage from a model call., DocstrangeProvider, Path, Any, _unwrap_docstrange_content(), Provider for Nanonets DocStrange document extraction API.      Supports custom_i, Make a call to DocStrange Extraction API using requests library. (+7 more)

### Community 74 - "Base"
Cohesion: 0.24
Nodes (6): Any, ModelProvider, Path, Abstract base class for all model providers.      Each provider (Interfaze, Gemi, Perform a completion on an image.          If schema is provided, uses structure, Detect bounding boxes in an image (used for section cropping).          Args:

### Community 51 - "Gemini"
Cohesion: 0.15
Nodes (8): GeminiProvider, Path, Any, Provider for Google Gemini models (via Google AI Studio)., Extract text content from a Gemini response., Attempt to repair truncated JSON by removing incomplete values and closing struc, guess_mime_type(), Guess MIME type from filename, defaulting to image/jpeg.

### Community 12 - "Http Base"
Cohesion: 0.10
Nodes (17): HttpJsonProvider, Any, Path, Base for providers that POST JSON and parse a JSON/text response., Default OpenAI-compatible auth headers. Override as needed., URL to POST to. Override for providers that key in the query string., POST ``payload`` and return the parsed JSON body, with retries., POST with exponential backoff + jitter on retryable provider errors. (+9 more)

### Community 70 - "Openrouter"
Cohesion: 0.25
Nodes (6): OpenrouterProvider, Any, Path, Provider for OpenRouter-hosted models such as google/gemini-4-carbon., AgenticCapabilityTest, P3 — capability detection is cached per provider class.

### Community 79 - "Qubrid"
Cohesion: 0.33
Nodes (5): QubridProvider, Path, Any, Provider for Qubrid-hosted multimodal models such as Qwen/Qwen3-VL-Flash., Extract the first choice finish reason, if present.

### Community 29 - "Toolbox"
Cohesion: 0.26
Nodes (9): Path, Any, ProgressCallback, _emit(), RunContext, ToolResult, Build usage from TokenUsage or a usage dict., Execution context shared by tool-layer operations. (+1 more)

### Community 55 - "Tracing"
Cohesion: 0.24
Nodes (7): RunTracer, Any, _exception_to_dict(), Exception, Collects step traces and persists them as JSON., StepTrace, Audit record for one engine step.

### Community 46 - "Ocr Engine Core Types"
Cohesion: 0.16
Nodes (8): _sum_usage(), new_run_id(), ProviderUsage, Path, Create a compact, sortable-enough run identifier for local executions., Usage reported by a model/provider call., FakeToolbox, CoreContractsTest

### Community 71 - "Ocr Engine Core Types"
Cohesion: 0.29
Nodes (4): to_jsonable(), Any, _duration_ms(), Convert engine values to plain JSON-compatible structures.

### Community 72 - "Image Utils"
Cohesion: 0.22
Nodes (8): env_names_for_provider(), resolve_provider_api_key(), get_api_key(), Candidate env var names for a provider (falls back to the default)., Resolve a provider's API key from its candidate env vars., Resolve an API key from environment variables.      If ``api_key_env`` is given, ApiKeyResolutionTest, M7 — single source of truth for provider → env var names.

### Community 28 - "Registry"
Cohesion: 0.15
Nodes (17): Validation plugin system for FIBA scoresheet OCR.  Architecture: - base: Validat, Validation Engine — orchestrates plugin execution and determines match status., Args:             plugins: List of plugin names, "all" for every registered plug, register(), get(), get_all(), get_by_category(), get_names() (+9 more)

### Community 44 - "Base"
Cohesion: 0.14
Nodes (13): Any, determine_match_status(), compute_confidence(), _section_for_field(), ABC, Base types for the validation plugin system.  Defines the ValidationPlugin proto, Determine the overall match status based on warning severities., Compute a deterministic, explainable confidence summary per section and globally (+5 more)

### Community 39 - "Fiba Rules"
Cohesion: 0.13
Nodes (14): create_warning(), Create a standardized validation warning., PlayerFoulsPlugin, Any, TeamFoulsPlugin, FIBA rules validation plugins — rules of the sport of basketball.  These check t, Validate that no player has more than 5 personal fouls (FIBA rule)., Validate that teams do not exceed 4 team fouls per quarter (FIBA rule). (+6 more)

### Community 65 - "Registry"
Cohesion: 0.19
Nodes (8): ValidationPlugin, Base class for validation plugins.      Every plugin must define:     - name: un, _Registry, Internal singleton-style registry for validation plugins., Register a validation plugin. Overwrites if name already exists., Get a plugin by name, or None if not found., Get all plugins in a given category., Get names of all core plugins (useful as default).

### Community 63 - "Validation Engine & Plugins"
Cohesion: 0.21
Nodes (6): ValidationEngine, Runs selected validation plugins against extracted data.      Usage:         # D, Names of currently active plugins., ValidationAndConfidenceTest, Unit tests for Phase 1 validation plugins, illegible mark propagation, and confi, 13 Validation Plugins (11 Default Core, 2 Opt-In) & Confidence

### Community 13 - "Plugins Core"
Cohesion: 0.10
Nodes (23): Built-in validation plugins.  Importing this module registers all built-in plugi, QuarterSumsPlugin, Any, DuplicateNumbersPlugin, GhostPlayersPlugin, ProgressiveVsFinalPlugin, _player_shot_counts(), _player_table_points() (+15 more)

### Community 26 - "Test Mcp Auth"
Cohesion: 0.14
Nodes (11): probe_ocr_api_key(), Session, _probe_with_session(), api_key_for_request(), Return True when the OCR API accepts ``token`` as a bearer key.      Uses GET /v, API key to send upstream: the caller's ``ocr_live_`` token, else OCR_API_KEY., OcrApiError, Exception (+3 more)

### Community 24 - "MCP Auth Verifier"
Cohesion: 0.14
Nodes (6): McpTokenVerifier, TokenVerifier, AccessToken, Accept the static MCP_AUTH_TOKEN or a validated ``ocr_live_`` API key.      ``oc, McpTokenVerifierTest, McpHardeningPhase3Test

### Community 21 - "MCP HTTP Client"
Cohesion: 0.22
Nodes (6): Any, OcrApiClient, Session, Response, _validate_run_id(), HTTP client used by the remote MCP adapter.

### Community 64 - "Tools"
Cohesion: 0.42
Nodes (12): handle_api_error(), OcrApiError, Any, process_submit_response(), submit_scoresheet_from_path(), submit_scoresheet_base64(), poll_run(), wait_for_run() (+4 more)

### Community 99 - "Eslint.Config"
Cohesion: 0.40
Nodes (4): __filename, __dirname, compat, eslintConfig

### Community 7 - "Package"
Cohesion: 0.05
Nodes (39): name, version, private, scripts, dev, build, start, lint (+31 more)

### Community 6 - "Api"
Cohesion: 0.10
Nodes (35): AccountKeysPanel(), KeyStatusChip(), NewApiKeyBanner(), ApiKeysPanel(), ApiKeyRecord, ApiEnvelope, RunStatus, RunRecord (+27 more)

### Community 52 - "Nav"
Cohesion: 0.16
Nodes (10): AdminLayout(), QuickstartPage(), TestLayout(), AccountRole, AssignedDemo, adminLinks, testerLinks, Nav() (+2 more)

### Community 84 - "Admin Page"
Cohesion: 0.46
Nodes (7): demoLabels, AdminPage(), inviteTester(), redirectWithMessage(), DEMOS, requireAdminAccount(), createAdminClient()

### Community 75 - "Submissions Route"
Cohesion: 0.40
Nodes (9): AirtableConfig, readConfig(), airtableUrl(), notConfigured(), GET(), POST(), AirtableRecord, validateLeagueSubmissionPayload() (+1 more)

### Community 36 - "Account"
Cohesion: 0.17
Nodes (17): POST(), LoginPayload, POST(), getSafeNextPath(), Home(), AssignedDemo, AccountRole, Account (+9 more)

### Community 60 - "Invite-Setup-Card"
Cohesion: 0.18
Nodes (8): AssignedDemo, AccountRole, AccountPayload, InviteStatus, demoLabels, demoHomePaths, InviteSetupCard(), destinationForAccount()

### Community 88 - "App Layout"
Cohesion: 0.33
Nodes (4): headingFont, bodyFont, metadata, AppToaster()

### Community 96 - "Login Page"
Cohesion: 0.47
Nodes (3): flowSteps, AuthCard(), getSafeNextPath()

### Community 0 - "Result-Utils"
Cohesion: 0.06
Nodes (58): INITIAL_STORE, CaptureClient(), NameMatch, findBestRosterNameMatch(), hasRosterNameMatch(), normalizePlayerName(), nameSimilarity(), tokenContainmentScore() (+50 more)

### Community 53 - "Club Layout"
Cohesion: 0.17
Nodes (10): metadata, ClubDemoLayout(), metadata, PlayerDemoLayout(), metadata, RefereeDemoLayout(), DemoTabs(), DemoTabs() (+2 more)

### Community 2 - "Stats-Utils"
Cohesion: 0.07
Nodes (45): ACCEPTED_IMAGE_TYPES, RunStatusBadge(), UploadIcon(), CheckIcon(), extractRunError(), CaptureClient(), StepState, HistoryClient() (+37 more)

### Community 56 - "Plugins"
Cohesion: 0.23
Nodes (9): formatFileSize(), CaptureClient(), buttonLabel(), writeDraft(), RefereePlugin, REFEREE_PLUGINS, DEFAULT_REFEREE_PLUGIN_IDS, pluginLabel() (+1 more)

### Community 67 - "League-Store"
Cohesion: 0.29
Nodes (7): LeagueClient(), LeagueStoreError, listSubmissions(), createSubmission(), errorText(), safeJson(), LeagueRecord

### Community 30 - "Sections"
Cohesion: 0.16
Nodes (17): ReconcileClient(), pluginsFromWarnings(), ReconcileSectionEditor(), gameTitle(), SheetSectionId, SheetSection, SECTION_ORDER, buildSheetSections() (+9 more)

### Community 31 - "Ui"
Cohesion: 0.14
Nodes (14): readDraft(), formatFinalScore(), buildSubmissionPayload(), text(), SubmitClient(), buildPreview(), IssueSeverity, OcrResult (+6 more)

### Community 47 - "Referee Demo Types"
Cohesion: 0.12
Nodes (16): LeagueValidationResult, RunStatus, ValidationWarning, PlayerPoints, OcrPlayer, OcrTeam, ProgressiveEvent, QuarterScore (+8 more)

### Community 16 - "Reconcile-Utils"
Cohesion: 0.16
Nodes (28): QUARTERS, FooterScoreSection(), TeamPlayersSection(), TeamFoulsSection(), ProgressiveScoreSection(), HeaderSection(), SectionProps, collectSuspiciousProgressiveIndices() (+20 more)

### Community 57 - "Validation"
Cohesion: 0.28
Nodes (14): REQUIRED_QUARTERS, RECOMPUTED_TYPES, finalScore(), quarterScore(), quartersSum(), playerPointsSum(), computeReconciliation(), quarterLabel() (+6 more)

### Community 80 - "Origin"
Cohesion: 0.39
Nodes (8): HeaderReader, OriginEnv, resolveAppOrigin(), firstHeaderValue(), cleanHost(), isLocalHost(), withHttpsScheme(), parseHttpOrigin()

### Community 89 - "Env"
Cohesion: 0.52
Nodes (3): siteConfig, assertBrowserEnv(), createClient()

### Community 81 - "Middleware"
Cohesion: 0.36
Nodes (7): MiddlewareAccount, matchesPrefix(), updateSession(), getAccountForUser(), destinationForMiddlewareAccount(), middleware(), config

### Community 18 - "Tsconfig"
Cohesion: 0.07
Nodes (28): compilerOptions, target, lib, dom, dom.iterable, esnext, allowJs, skipLibCheck (+20 more)

### Community 32 - "Tsconfig.Test"
Cohesion: 0.09
Nodes (21): extends, ./tsconfig.json, compilerOptions, noEmit, outDir, module, moduleResolution, target (+13 more)

### Community 90 - "Create Admin User"
Cohesion: 0.43
Nodes (6): parse_args(), Namespace, require_env(), find_user_by_email(), Any, main()

### Community 61 - "Deploy Cloudrun"
Cohesion: 0.31
Nodes (11): deploy_cloudrun.sh script, g(), secret_exists(), grant_secret_access(), supabase_secret_bindings(), ensure_secret(), infra(), build() (+3 more)

### Community 85 - "Graphify Check"
Cohesion: 0.43
Nodes (7): fail(), md5_file(), Path, is_sensitive(), source_locations(), Any, main()

### Community 86 - "Issue Api Key"
Cohesion: 0.43
Nodes (7): parse_args(), Namespace, require_env(), find_user_by_email(), Any, resolve_user_id(), main()

### Community 87 - "Serve"
Cohesion: 0.50
Nodes (6): serve.sh script, ensure_token(), is_running(), start_service(), stop_service(), print_urls()

### Community 40 - "Smoke Async Api"
Cohesion: 0.26
Nodes (18): main(), parse_args(), Namespace, make_run_id(), wait_for_run(), Session, Any, get_json() (+10 more)

### Community 73 - "Smoke Async Mcp"
Cohesion: 0.33
Nodes (10): main(), run_smoke(), Path, _call_tool_data(), Client, Any, _assert_success(), _resolve_image() (+2 more)

### Community 48 - "Test Grid Removal"
Cohesion: 0.21
Nodes (16): remove_grid_lines(), ndarray, isolate_colored_ink(), remove_grid_protect_ink(), remove_grid_protect_handwriting(), extract_progressive_score(), Path, compare_with_gt() (+8 more)

### Community 37 - "Test Mcp Client"
Cohesion: 0.20
Nodes (4): OcrApiClientTest, FakeSession, FakeResponse, Any

### Community 49 - "Docs"
Cohesion: 0.16
Nodes (12): AGENTS.md (Agent Guardrails & Skill Index), Graphify & Engram Agent Workflow, CLAUDE.md (@AGENTS.md Pointer), DOCS.md (Canonical Technical Reference), Documentation Authority Matrix, Documentation Surface Catalog, Canonical Env, API, MCP, CLI & Supabase Contracts, README.md (Project Landing & Quickstart) (+4 more)

### Community 62 - "Repo Guardrails & Contributing"
Cohesion: 0.17
Nodes (10): Hard Inward Dependency Direction, Trunk-Based Git Workflow (--ff-only), Hybrid Skill Authoring Standard, Codebase Compass & Runtime Split, Golden Placement Rule & Package Ownership, skills/catalog.md (Centralized Skills Catalog), Skill: architecture-guardrails, Skill: commit-hygiene (+2 more)

### Community 82 - "Cloud Run & Vercel Deployment"
Cohesion: 0.25
Nodes (6): cloudbuild.yaml (Cloud Run Continuous Deployment), Image-Only Cloud Run Swap Rationale, docs/DEPLOYMENT.md (Cloud Run, Vercel & Supabase Ops), Vercel Post-Deploy OCR_CORS_ORIGINS Sync, packages/mcp/AGENTS.md (MCP Guardrails Stub), packages/web/AGENTS.md (Web Guardrails Stub)

## Knowledge Gaps
- **138 isolated node(s):** `ocr-engine-mcp`, `__filename`, `__dirname`, `compat`, `eslintConfig` (+133 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `authorizeDemoApiAccess()` connect `Submissions Route` to `CLI & Adapters Docs`, `Account`, `Nav`?**
  _High betweenness centrality (0.207) - this node is a cross-community bridge._
- **Why does `main()` connect `CLI & Adapters Docs` to `Pipeline Config`, `Image Utils`, `Run Dataset`, `Core Pipeline Docs`, `Exceptions`, `Test Hardening`, `FibaOcrPipeline Orchestrator`?**
  _High betweenness centrality (0.173) - this node is a cross-community bridge._
- **Why does `TokenUsage` connect `Docstrange` to `Extractor`, `Output Builder`, `Openrouter`, `Base`, `Interfaze`, `Test Provider Http Base`, `Http Base`, `Core Pipeline Docs`, `Qubrid`, `Base`, `Test Phase2 Quality`, `Gemini`, `Cropper`, `Tracing`, `FibaOcrPipeline Orchestrator`, `Toolbox`, `Cropper`?**
  _High betweenness centrality (0.086) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `TokenUsage` (e.g. with `Cropper` and `ExtractionTarget`) actually correct?**
  _`TokenUsage` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `OcrApiClient` (e.g. with `McpTokenVerifier` and `Middleware JSONResponse vs FastAPI HTTPException(detail=...) Split`) actually correct?**
  _`OcrApiClient` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `RunRepository` (e.g. with `RunExecutor` and `ApiHardeningPhase3Test`) actually correct?**
  _`RunRepository` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `OcrToolbox` (e.g. with `RunExecutor` and `FibaOcrPipeline`) actually correct?**
  _`OcrToolbox` has 19 INFERRED edges - model-reasoned connections that need verification._