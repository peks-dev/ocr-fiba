# Graph Report - ocr-engine  (2026-11-19)

## Corpus Check
- 253 files · ~105,913 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2066 nodes · 4650 edges · 102 communities (93 shown, 9 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 287 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a71a1f5e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Result-Utils
- Extractor
- Stats-Utils
- Output Builder
- Async Run Execution & Repo
- Rate Limit
- Api
- Package
- Auth Supabase
- FastAPI App & Auth Docs
- Test Provider Http Base
- Interfaze
- Http Base
- Plugins Core
- Core Pipeline Docs
- Test Api
- Reconcile-Utils
- Test Api
- Tsconfig
- Exceptions
- Runs
- MCP HTTP Client
- Test Hardening
- Docstrange
- MCP Auth Verifier
- Cropper
- Test Mcp Auth
- Api Keys
- Registry
- Toolbox
- Sections
- Ui
- Tsconfig.Test
- Server
- Auth Api Key
- Artifact Store
- Account
- Test Mcp Client
- Enhancer
- Fiba Rules
- Smoke Async Api
- Me
- Test Phase2 Quality
- Preprocessor
- Base
- Image Utils
- Ocr Engine Core Types
- Referee Demo Types
- Test Grid Removal
- Docs
- Evaluate Dataset
- Gemini
- Nav
- Club Layout
- Cv Progressive Score
- Tracing
- Plugins
- Validation
- Tracing
- FibaOcrPipeline Orchestrator
- Invite-Setup-Card
- Deploy Cloudrun
- Repo Guardrails & Contributing
- Validation Engine & Plugins
- Tools
- Registry
- Test Auth
- League-Store
- Pipeline Config
- Image Utils
- Base
- Submissions Route
- CLI & Adapters Docs
- Test Auth
- Qubrid
- Origin
- App Layout
- Evaluate Header
- Evaluate Player Fouls
- Evaluate Progressive Score
- Evaluate Team Identity
- Login Page
- Evaluate Entry Marks
- Evaluate Player Points
- Eslint.Config
- Pyproject
-   Init  
-   Init  
-   Init  
- Next.Config
- Postcss.Config
- Graphify-Check
- Graphify-Update
- Setup-Graphify

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
- `60s Key Cache & Mandatory Eviction on Delete` --rationale_for--> `invalidate_api_key_cache()`  [EXTRACTED]
  skills/api-key-auth/SKILL.md → packages/api/src/ocr_engine_api/auth_api_key.py
- `Seven-Phase FIBA OCR Pipeline Flow` --references--> `OcrToolbox`  [EXTRACTED]
  docs/ARCHITECTURE.md → packages/core-engine/src/ocr_engine_core/toolbox.py
- `Middleware JSONResponse vs FastAPI HTTPException(detail=...) Split` --conceptually_related_to--> `OcrApiClient`  [INFERRED]
  skills/api-error-envelope/SKILL.md → packages/mcp/src/ocr_engine_mcp/client.py
- `Skill: api-key-auth` --references--> `validate_supabase_session()`  [EXTRACTED]
  skills/api-key-auth/SKILL.md → packages/api/src/ocr_engine_api/auth_supabase.py
- `Canonical Env, API, MCP, CLI & Supabase Contracts` --references--> `create_app()`  [EXTRACTED]
  DOCS.md → packages/api/src/ocr_engine_api/main.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Engram-Style Layered Documentation Architecture** — readme_md_landing, docs_md_technical_reference, docs_codebase_guide_landing, agents_md_root_index [INFERRED 0.95]
- **Centralized Agent Skills & Package Stub System** — agents_md_root_index, skills_catalog_index, packages_core_engine_agents_stub, packages_api_agents_stub [INFERRED 0.95]

## Communities (102 total, 9 thin omitted)

### Community 0 - "Result-Utils"
Cohesion: 0.14
Nodes (18): CaptureClient(), INITIAL_STORE, INITIAL_STORE, RosterClient(), addClubGame(), addDetectedPlayersToRoster(), deleteRosterPlayer(), EMPTY_STORE (+10 more)

### Community 1 - "Extractor"
Cohesion: 0.05
Nodes (54): ExtractionError, Error durante la fase de extracción de datos., _convert_interfaze_team_json(), ExtractionTarget, Any, Path, Core Extractor — Model-agnostic structured extraction from FIBA sections.  This, Extract data from a single section image. (+46 more)

### Community 2 - "Stats-Utils"
Cohesion: 0.11
Nodes (23): HistoryClient(), ProgressClient(), getPlayerInsight(), average(), computeSummary(), computeTrend(), GamesPeriod, PERIOD_OPTIONS (+15 more)

### Community 3 - "Output Builder"
Cohesion: 0.06
Nodes (52): build_final_output(), _coerce_bool(), _coerce_int(), _compute_points_from_running_score(), _derive_entry_flags(), _derive_fouls_from_cells(), _foul_token(), _is_illegible_entry_mark() (+44 more)

### Community 4 - "Async Run Execution & Repo"
Cohesion: 0.07
Nodes (21): Future, run_links(), Any, Path, Execute OCR runs and update filesystem-backed status., Submit a local/preview run without holding the HTTP response open., RunExecutor, _is_relative_to() (+13 more)

### Community 5 - "Rate Limit"
Cohesion: 0.17
Nodes (19): average(), clubSummary(), computeRegularity(), computeTrend(), createGameFromResult(), extractTeamStats(), normalizeNumber(), normalizeText() (+11 more)

### Community 6 - "Api"
Cohesion: 0.06
Nodes (51): AccountKeysPanel(), KeyStatusChip(), NewApiKeyBanner(), ApiKeysPanel(), AccountPayload, AccountRole, AssignedDemo, demoHomePaths (+43 more)

### Community 7 - "Package"
Cohesion: 0.05
Nodes (39): eslint, eslint-config-next, next, dependencies, next, react, react-dom, sonner (+31 more)

### Community 8 - "Auth Supabase"
Cohesion: 0.11
Nodes (21): forbidden_response(), is_auth_exempt(), JSONResponse, extract_bearer_token(), is_jwt_request(), _jwt_cache_get(), _jwt_cache_key(), _jwt_cache_set() (+13 more)

### Community 9 - "FastAPI App & Auth Docs"
Cohesion: 0.04
Nodes (43): create_app(), _load_project_env(), Load .env from cwd or the repository root without overriding env vars., Run the API app with uvicorn for the ocr-api console script., run(), client_key(), create_rate_limit_store(), is_run_creation() (+35 more)

### Community 10 - "Test Provider Http Base"
Cohesion: 0.15
Nodes (13): ProviderAuthError, ProviderError, ProviderRateLimitError, ProviderServerError, Error originado en un provider de IA externo., Error de autenticación (401/403) — API key inválida o sin permisos., Rate limit excedido (429) — reintentable con backoff., Error del lado del servidor (5xx) — reintentable. (+5 more)

### Community 11 - "Interfaze"
Cohesion: 0.13
Nodes (18): ProviderInvalidResponseError, Excepción base y jerarquía para el OCR Engine.  Toda excepción del engine hereda, El provider devolvió una respuesta que no se puede interpretar., ModelProvider, ABC, Base abstraction for AI model providers.  This module defines the common interfa, Abstract base class for all model providers.      Each provider (Interfaze, Gemi, Gemini provider implementation via Google Generative AI. (+10 more)

### Community 12 - "Http Base"
Cohesion: 0.09
Nodes (16): HttpJsonProvider, Any, Path, Sleep ``BACKOFF_BASE * 2**(attempt-1)`` (capped) plus jitter., Encode an image as a base64 ``data:`` URI., Encode an image as raw base64 (no data URI prefix)., Strip markdown code fences (```json ... ```) wrapped around JSON., Parse content as JSON, tolerating code fences; fall back to raw_text. (+8 more)

### Community 13 - "Plugins Core"
Cohesion: 0.10
Nodes (23): DuplicateNumbersPlugin, EntryAndFoulsConsistencyPlugin, GhostPlayersPlugin, IllegibleMarksPlugin, _player_shot_counts(), _player_table_points(), PlayerVsProgressivePlugin, PreprocessFallbackPlugin (+15 more)

### Community 14 - "Core Pipeline Docs"
Cohesion: 0.10
Nodes (15): PipelineConfig, Configuration object that defines which model/provider to use     for each phase, Get the API key for the cropper provider., Get the API key for the extractor provider., Resolve the API key for a given provider., ErrorCode, Catálogo de códigos de error machine-readable., Extractor (+7 more)

### Community 15 - "Test Api"
Cohesion: 0.07
Nodes (35): File, FileResponse, Form, ge, le, is_authorized(), HTTPException, unsupported_upload_type_error() (+27 more)

### Community 16 - "Reconcile-Utils"
Cohesion: 0.17
Nodes (26): collectSuspiciousProgressiveIndices(), FooterScoreSection(), HeaderSection(), matchWinner(), ProgressiveScoreSection(), QUARTERS, SectionProps, TeamFoulsSection() (+18 more)

### Community 17 - "Test Api"
Cohesion: 0.11
Nodes (9): Canonical Env, API, MCP, CLI & Supabase Contracts, ApiSettings, _env_bool(), get_api_settings(), Path, True when the service-role client can be constructed (URL + service key)., resolve_runs_dir(), validate_api_settings() (+1 more)

### Community 18 - "Tsconfig"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 19 - "Exceptions"
Cohesion: 0.11
Nodes (13): ConfigurationError, InputError, OcrEngineError, PipelineError, Any, Exception, Serializar al formato de respuesta de error estandarizado., Error en la configuración del pipeline (.env, providers, API keys). (+5 more)

### Community 20 - "Runs"
Cohesion: 0.18
Nodes (11): Agent-ready tool layer for the FIBA OCR engine.  The toolbox exposes atomic oper, _exception_to_dict(), Any, Trace recording for OCR engine runs., Collects step traces and persists them as JSON., RunTracer, _sum_usage(), _timestamp_iso() (+3 more)

### Community 21 - "MCP HTTP Client"
Cohesion: 0.22
Nodes (6): OcrApiClient, Any, Response, Session, HTTP client used by the remote MCP adapter., _validate_run_id()

### Community 22 - "Test Hardening"
Cohesion: 0.23
Nodes (10): BaseModel, apply_server_defaults(), build_config(), parse_options_json(), Fill extractor provider/model/reasoning from server env when the client did not, create_run(), CreateRunRequest, PipelineOptions (+2 more)

### Community 23 - "Docstrange"
Cohesion: 0.16
Nodes (15): ProviderConnectionError, ProviderTimeoutError, Timeout en la llamada al provider — reintentable., Error de conexión (DNS, network unreachable) — reintentable., DocstrangeProvider, Any, Path, DocStrange (Nanonets) provider implementation via Document Extraction API.  Uses (+7 more)

### Community 24 - "MCP Auth Verifier"
Cohesion: 0.14
Nodes (6): AccessToken, McpTokenVerifier, Accept the static MCP_AUTH_TOKEN or a validated ``ocr_live_`` API key.      ``oc, McpTokenVerifierTest, McpHardeningPhase3Test, TokenVerifier

### Community 25 - "Cropper"
Cohesion: 0.09
Nodes (30): Cropper, Any, Path, Core Cropper — Model-agnostic section detection, validation, and cropping.  This, Sub-crop team fouls from already-cropped team sections.          For each team (, Detect the team-fouls bounding box for one team (network-bound)., Validate and normalize a list of detected bounding boxes., Validate a single team fouls bounding box. (+22 more)

### Community 26 - "Test Mcp Auth"
Cohesion: 0.14
Nodes (11): api_key_for_request(), probe_ocr_api_key(), _probe_with_session(), Session, API key to send upstream: the caller's ``ocr_live_`` token, else OCR_API_KEY., Return True when the OCR API accepts ``token`` as a bearer key.      Uses GET /v, _encode_artifact_name(), OcrApiError (+3 more)

### Community 27 - "Api Keys"
Cohesion: 0.06
Nodes (55): FastAPI, delete_api_key(), find_active_key_by_hash(), generate_api_key(), get_account_by_id(), get_account_by_supabase_user_id(), hash_api_key(), list_accounts() (+47 more)

### Community 28 - "Registry"
Cohesion: 0.15
Nodes (18): Validation Engine — orchestrates plugin execution and determines match status., Args:             plugins: List of plugin names, "all" for every registered plug, Validation plugin system for FIBA scoresheet OCR.  Architecture: - base: Validat, get(), get_all(), get_by_category(), get_core_names(), get_names() (+10 more)

### Community 29 - "Toolbox"
Cohesion: 0.27
Nodes (11): _emit(), OcrToolbox, Any, Path, Composable OCR operations with structured results and tracing., Execution context shared by tool-layer operations., Structured response returned by each engine tool operation., Build usage from TokenUsage or a usage dict. (+3 more)

### Community 30 - "Sections"
Cohesion: 0.11
Nodes (23): readDraft(), DEFAULT_REFEREE_PLUGIN_IDS, pluginLabel(), REFEREE_PLUGINS, RefereePlugin, pluginsFromWarnings(), ReconcileClient(), ReconcileSectionEditor() (+15 more)

### Community 31 - "Ui"
Cohesion: 0.16
Nodes (13): buildSubmissionPayload(), formatFinalScore(), gameTitle(), text(), buildPreview(), SubmitClient(), IssueSeverity, EmptyState() (+5 more)

### Community 32 - "Tsconfig.Test"
Cohesion: 0.09
Nodes (21): compilerOptions, incremental, isolatedModules, module, moduleResolution, noEmit, outDir, target (+13 more)

### Community 33 - "Server"
Cohesion: 0.13
Nodes (13): FastMCP, auth_from_env(), Build the HTTP token verifier from the environment.      When MCP_AUTH_TOKEN is, Remote MCP adapter for the OCR Engine API., _call_with_client(), _client(), create_mcp(), _json_resource() (+5 more)

### Community 34 - "Auth Api Key"
Cohesion: 0.27
Nodes (5): _cache_get(), _cache_set(), Return (account_id, status) from cache if present and not expired., Store a validated key in the bounded cache., ApiKeyCacheTest

### Community 35 - "Artifact Store"
Cohesion: 0.15
Nodes (10): ArtifactStore, _guess_image_mime_type(), Any, Path, Small filesystem-backed artifact registry for one run., Copy the source image into the run input directory., Write the final engine result to the run result path., Artifact (+2 more)

### Community 36 - "Account"
Cohesion: 0.18
Nodes (17): POST(), getSafeNextPath(), LoginPayload, POST(), Home(), Account, AccountLookupResult, AccountRole (+9 more)

### Community 37 - "Test Mcp Client"
Cohesion: 0.20
Nodes (4): FakeResponse, FakeSession, OcrApiClientTest, Any

### Community 38 - "Enhancer"
Cohesion: 0.17
Nodes (19): _apply_clahe(), _apply_gamma(), _enhance_image(), enhance_sections(), _normalize_grid_mode(), ndarray, Path, Enhancer — Image preprocessing phase for FIBA section crops.  Applies three enha (+11 more)

### Community 39 - "Fiba Rules"
Cohesion: 0.13
Nodes (14): create_warning(), Create a standardized validation warning., PlayerFoulsPlugin, Any, FIBA rules validation plugins — rules of the sport of basketball.  These check t, Validate that no player has more than 5 personal fouls (FIBA rule)., Validate that teams do not exceed 4 team fouls per quarter (FIBA rule)., TeamFoulsPlugin (+6 more)

### Community 40 - "Smoke Async Api"
Cohesion: 0.05
Nodes (59): Graphify & Engram Agent Workflow, Hard Inward Dependency Direction, AGENTS.md (Agent Guardrails & Skill Index), CLAUDE.md (@AGENTS.md Pointer), Hybrid Skill Authoring Standard, Trunk-Based Git Workflow (--ff-only), Seven-Phase FIBA OCR Pipeline Flow, Maintainer Warning Signs & Hard Questions (+51 more)

### Community 41 - "Me"
Cohesion: 0.16
Nodes (11): INITIAL_STORE, OverviewClient(), computePlayerTotals(), INITIAL_STORE, PlayersClient(), formatDateLabel(), playerSeries(), EmptyState() (+3 more)

### Community 42 - "Test Phase2 Quality"
Cohesion: 0.17
Nodes (16): CaptureClient(), createSavedGame(), extractPlayers(), extractTeamPlayers(), formatFinalScore(), formatGameTitle(), normalizeText(), toDemoPlayer() (+8 more)

### Community 43 - "Preprocessor"
Cohesion: 0.27
Nodes (18): _apply_inverse_rotation(), _contour_metrics(), _estimate_rotation_angle(), _expand_quad(), _find_best_sheet_contour(), _find_canny_sheet_candidates(), _find_paper_mask_candidates(), _find_sheet_contour() (+10 more)

### Community 44 - "Base"
Cohesion: 0.14
Nodes (13): compute_confidence(), determine_match_status(), ABC, Any, Base types for the validation plugin system.  Defines the ValidationPlugin proto, Run validations on extracted data. Returns a list of warnings., Determine the overall match status based on warning severities., Compute a deterministic, explainable confidence summary per section and globally (+5 more)

### Community 45 - "Image Utils"
Cohesion: 0.16
Nodes (18): binarize_adaptive(), binarize_otsu(), main(), Path, Binarize a FIBA scoresheet section image for OCR testing.  Standalone utility —, Binarize using adaptive Gaussian thresholding.      Good for images with uneven, Binarize using Otsu's global threshold.      Good for images with even lighting, encode_file() (+10 more)

### Community 46 - "Ocr Engine Core Types"
Cohesion: 0.18
Nodes (7): new_run_id(), ProviderUsage, Path, Create a compact, sortable-enough run identifier for local executions., Usage reported by a model/provider call., FakeToolbox, CoreContractsTest

### Community 47 - "Referee Demo Types"
Cohesion: 0.12
Nodes (16): LeagueValidationResult, ConfidenceLevel, ConfidenceSectionKey, ConfidenceSummary, LeagueSubmissionPayload, OcrFooter, OcrPlayer, OcrTeam (+8 more)

### Community 48 - "Test Grid Removal"
Cohesion: 0.21
Nodes (16): compare_with_gt(), extract_progressive_score(), isolate_colored_ink(), main(), ndarray, Path, Test: Preprocessing variants for progressive_score section.  Compares multiple p, Extract only colored ink (red/blue handwriting) onto a clean background. (+8 more)

### Community 49 - "Docs"
Cohesion: 0.19
Nodes (13): ACCEPTED_IMAGE_TYPES, CheckIcon(), extractRunError(), formatFileSize(), RunStatusBadge(), UploadIcon(), buttonLabel(), CaptureClient() (+5 more)

### Community 50 - "Evaluate Dataset"
Cohesion: 0.19
Nodes (14): docs/EVALUATION.md (Dataset Ground-Truth Evaluation), compare_values(), count_fields(), count_matches(), evaluate_sheet(), main(), print_mismatches(), Any (+6 more)

### Community 51 - "Gemini"
Cohesion: 0.09
Nodes (16): Represents token usage from a model call., TokenUsage, GeminiProvider, Any, Path, Attempt to repair truncated JSON by removing incomplete values and closing struc, Provider for Google Gemini models (via Google AI Studio)., Extract text content from a Gemini response. (+8 more)

### Community 52 - "Nav"
Cohesion: 0.17
Nodes (9): AdminLayout(), QuickstartPage(), TestLayout(), AccountRole, adminLinks, AssignedDemo, Nav(), testerLinks (+1 more)

### Community 53 - "Club Layout"
Cohesion: 0.17
Nodes (10): ClubDemoLayout(), metadata, metadata, PlayerDemoLayout(), metadata, RefereeDemoLayout(), DemoTabs(), DemoTabs() (+2 more)

### Community 54 - "Cv Progressive Score"
Cohesion: 0.21
Nodes (14): cell_has_ink(), create_ink_masks(), detect_row_positions(), evaluate(), extract_progressive_score(), main(), ndarray, Path (+6 more)

### Community 55 - "Tracing"
Cohesion: 0.12
Nodes (14): ProviderType, Factory method to create a Cropper from configuration., GlmProvider, Any, Path, Provider for Z.AI VLM models (GLM-5V-Turbo, GLM-4.6V, etc.)     via the OpenAI-c, create_provider(), ProviderType (+6 more)

### Community 56 - "Plugins"
Cohesion: 0.25
Nodes (12): DocsLinksTest, extract_heading_anchors(), extract_relative_targets(), github_slug(), iter_markdown_files(), Path, Return tracked/source Markdown files outside ignored/generated directories., Return lines outside fenced code blocks. (+4 more)

### Community 57 - "Validation"
Cohesion: 0.28
Nodes (14): computeReconciliation(), ENGINE_WARNING_TITLES, engineTitle(), finalScore(), normalize(), normalizeSeverity(), playerPointsSum(), quarterLabel() (+6 more)

### Community 58 - "Tracing"
Cohesion: 0.15
Nodes (8): Helpers for recording OCR run artifacts., FibaOcrPipeline — Complete pipeline orchestrator (model-agnostic).  This module, _duration_ms(), Any, Shared contracts for the OCR engine tool layer.  These types are intentionally l, Convert engine values to plain JSON-compatible structures., to_jsonable(), toolbox_usage()

### Community 59 - "FibaOcrPipeline Orchestrator"
Cohesion: 0.21
Nodes (7): FibaOcrPipeline, Any, Path, Save the result JSON to a file., Pipeline completo para procesar hojas de anotación FIBA.     Usa la arquitectura, Run the full pipeline on a FIBA scoresheet image.          Args:             ima, Build TokenUsage from another TokenUsage, ProviderUsage, dict, or None.

### Community 60 - "Invite-Setup-Card"
Cohesion: 0.21
Nodes (6): 13 Validation Plugins (11 Default Core, 2 Opt-In) & Confidence, Runs selected validation plugins against extracted data.      Usage:         # D, Names of currently active plugins., ValidationEngine, Unit tests for Phase 1 validation plugins, illegible mark propagation, and confi, ValidationAndConfidenceTest

### Community 61 - "Deploy Cloudrun"
Cohesion: 0.09
Nodes (34): cloudbuild.yaml (Cloud Run Continuous Deployment), Image-Only Cloud Run Swap Rationale, Vercel Post-Deploy OCR_CORS_ORIGINS Sync, docs/DEPLOYMENT.md (Cloud Run, Vercel & Supabase Ops), find_user_by_email(), main(), parse_args(), Any (+26 more)

### Community 62 - "Repo Guardrails & Contributing"
Cohesion: 0.36
Nodes (10): findBestRosterNameMatch(), hasRosterNameMatch(), initials(), levenshtein(), NameMatch, nameSimilarity(), normalizePlayerName(), partialTokenScore() (+2 more)

### Community 64 - "Tools"
Cohesion: 0.42
Nodes (12): OcrApiError, _async_next_actions(), handle_api_error(), inspect_run(), poll_run(), process_submit_response(), Any, _resources() (+4 more)

### Community 65 - "Registry"
Cohesion: 0.15
Nodes (10): Base class for validation plugins.      Every plugin must define:     - name: un, ValidationPlugin, Internal singleton-style registry for validation plugins., Register a validation plugin. Overwrites if name already exists., Get a plugin by name, or None if not found., Get all registered plugins., Get all plugins in a given category., Get all registered plugin names. (+2 more)

### Community 66 - "Test Auth"
Cohesion: 0.39
Nodes (8): AdminPage(), demoLabels, inviteTester(), redirectWithMessage(), AssignedDemo, DEMOS, requireAdminAccount(), createAdminClient()

### Community 67 - "League-Store"
Cohesion: 0.26
Nodes (8): LeagueClient(), createSubmission(), errorText(), LeagueStoreError, listSubmissions(), safeJson(), LeagueRecord, Panel()

### Community 68 - "Pipeline Config"
Cohesion: 0.15
Nodes (18): find_image(), main(), Path, Batch runner: process the entire FIBA scoresheet dataset through the pipeline., Find the .jpg image inside a sheet directory., build_reasoning_config(), default_extractor_reasoning(), parse_reasoning_config() (+10 more)

### Community 72 - "Image Utils"
Cohesion: 0.20
Nodes (8): env_names_for_provider(), get_api_key(), Candidate env var names for a provider (falls back to the default)., Resolve a provider's API key from its candidate env vars., Resolve an API key from environment variables.      If ``api_key_env`` is given, resolve_provider_api_key(), ApiKeyResolutionTest, M7 — single source of truth for provider → env var names.

### Community 74 - "Base"
Cohesion: 0.40
Nodes (4): Any, Path, Perform a completion on an image.          If schema is provided, uses structure, Detect bounding boxes in an image (used for section cropping).          Args:

### Community 75 - "Submissions Route"
Cohesion: 0.40
Nodes (9): AirtableConfig, AirtableRecord, airtableUrl(), GET(), notConfigured(), POST(), readConfig(), validateLeagueSubmissionPayload() (+1 more)

### Community 76 - "CLI & Adapters Docs"
Cohesion: 0.12
Nodes (13): packages/cli/AGENTS.md (CLI Guardrails Stub), main(), _output_error(), _output_success(), Entry point for running the FIBA OCR pipeline with model selection., Output a successful pipeline result., Output a pipeline error in standardized format., Override the default extractor for a specific section. (+5 more)

### Community 77 - "Test Auth"
Cohesion: 0.14
Nodes (13): Fail-Closed Shared Quotas & Production Sanitization, packages/api/AGENTS.md (API Guardrails Stub), is_api_key_request(), JSONResponse, Request, Return True when the Bearer token is a per-client ``ocr_live_`` API key.      Th, Validate an OCR API key from the request.      Returns None on success (request, _unauthorized_response() (+5 more)

### Community 79 - "Qubrid"
Cohesion: 0.33
Nodes (5): Any, Path, QubridProvider, Provider for Qubrid-hosted multimodal models such as Qwen/Qwen3-VL-Flash., Extract the first choice finish reason, if present.

### Community 80 - "Origin"
Cohesion: 0.39
Nodes (8): cleanHost(), firstHeaderValue(), HeaderReader, isLocalHost(), OriginEnv, parseHttpOrigin(), resolveAppOrigin(), withHttpsScheme()

### Community 88 - "App Layout"
Cohesion: 0.33
Nodes (4): bodyFont, headingFont, metadata, AppToaster()

### Community 91 - "Evaluate Header"
Cohesion: 0.53
Nodes (5): evaluate_sheet(), main(), _norm(), Any, Evaluate header extraction against ground truth.  Usage:     python evaluation/e

### Community 92 - "Evaluate Player Fouls"
Cohesion: 0.53
Nodes (5): evaluate_sheet(), _foul_family(), main(), Any, Evaluate individual player foul extraction against ground truth.  This focuses o

### Community 93 - "Evaluate Progressive Score"
Cohesion: 0.53
Nodes (5): evaluate_sheet(), _events_by_running_score(), main(), Any, Evaluate progressive_score extraction against ground truth.  Reports running_sco

### Community 94 - "Evaluate Team Identity"
Cohesion: 0.53
Nodes (5): evaluate_sheet(), main(), _norm(), Any, Evaluate team/player identity extraction against ground truth.  Focuses on team.

### Community 96 - "Login Page"
Cohesion: 0.47
Nodes (3): flowSteps, AuthCard(), getSafeNextPath()

### Community 97 - "Evaluate Entry Marks"
Cohesion: 0.50
Nodes (4): evaluate_sheet(), main(), Any, Evaluate player entered/started extraction against ground truth.  Usage:     pyt

### Community 98 - "Evaluate Player Points"
Cohesion: 0.50
Nodes (4): evaluate_sheet(), main(), Any, Evaluate player points extraction against ground truth.  Usage:     python evalu

### Community 99 - "Eslint.Config"
Cohesion: 0.40
Nodes (4): compat, __dirname, eslintConfig, __filename

### Community 100 - "Pyproject"
Cohesion: 0.60
Nodes (5): ocr-engine-api, ocr-engine-cli, ocr-engine-core, ocr-engine-mcp, ocr-engine-workspace

## Knowledge Gaps
- **140 isolated node(s):** `ocr-engine-mcp`, `__filename`, `__dirname`, `compat`, `eslintConfig` (+135 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `main()` connect `CLI & Adapters Docs` to `Pipeline Config`, `Image Utils`, `Core Pipeline Docs`, `Exceptions`, `FibaOcrPipeline Orchestrator`?**
  _High betweenness centrality (0.163) - this node is a cross-community bridge._
- **Why does `authorizeDemoApiAccess()` connect `Submissions Route` to `CLI & Adapters Docs`, `Account`?**
  _High betweenness centrality (0.155) - this node is a cross-community bridge._
- **Why does `OcrApiClient` connect `MCP HTTP Client` to `Tools`, `Server`, `Artifact Store`, `Async Run Execution & Repo`, `Test Mcp Client`, `CLI & Adapters Docs`, `MCP Auth Verifier`, `Test Mcp Auth`, `Api Keys`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Are the 24 inferred relationships involving `TokenUsage` (e.g. with `Cropper` and `ExtractionTarget`) actually correct?**
  _`TokenUsage` has 24 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `OcrApiClient` (e.g. with `McpTokenVerifier` and `Middleware JSONResponse vs FastAPI HTTPException(detail=...) Split`) actually correct?**
  _`OcrApiClient` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `RunRepository` (e.g. with `RunExecutor` and `ApiHardeningPhase3Test`) actually correct?**
  _`RunRepository` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `OcrToolbox` (e.g. with `RunExecutor` and `FibaOcrPipeline`) actually correct?**
  _`OcrToolbox` has 19 INFERRED edges - model-reasoned connections that need verification._