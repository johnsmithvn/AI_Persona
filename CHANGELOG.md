# Changelog

All notable changes to **AI Person — Bộ Não Thứ 2** will be documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [v0.3.0] — 2026-02-21

### Added
- `docs/MEMORY_CONTRACT.md` — full Memory Contract V1 spec (content_type registry, metadata schema, tag registry, golden rules, examples)
- `cli/` package — interactive `ai add` command (content_type, tags, person_name flow, metadata.type)
- `cli/registry.py` — content_type, tag, type menus (mirrors MEMORY_CONTRACT.md)
- `cli/person_helpers.py` — person name normalization + suggestion
- `MemoryRepository.get_distinct_person_names()` — JSONB query for CLI person flow
- `AI_Chat/` — React chat UI (Vite) with 6-mode reasoning, memory management, semantic search
- `AI_Chat/src/api/client.js` — fetch wrapper for all 6 API endpoints
- `.\ ai chat` command in `ai.ps1` — launches React dev server
- `validate_citations()` in `ReasoningService` — enforces `[Memory N]` citation format, detects fabricated references
- `PolicyViolationError` exception for mode policy violations
- `CITATION_FORMAT_RULE` shared constant across all mode instructions
- Migration `004_drop_source_type_column.py` — moves `source_type` to `metadata.source`

### Changed
- **BREAKING:** `source_type` top-level column removed → use `metadata.source` instead
- **BREAKING:** `content_type` reduced from 10 → 6 values (`quote`, `repo`, `pdf`, `transcript` removed)
- RECALL policy: `must_cite_memory_id` changed from `False` → `True`
- REFLECT instruction: added "No Psychological Inference" guard
- EXPAND instruction: added "No Override" guard + Memory/External section format
- PromptBuilder: added citation format header in MEMORY CONTEXT section
- All docs bumped to v0.3.0

### Fixed
- Migration `003_enum_to_varchar.py` — fixed CASCADE issue when dropping ENUM types

---

## [Unreleased]

### Added
- `docs/API_DOCS.md` — comprehensive API documentation (5 endpoints, schemas, error codes, cURL examples)
- `PROJECT_STRUCTURE.md` section 2.1: Memory-First Intelligence Principle
- `DATA_DESIGN.md` section 11.8: Engagement Tracking (V2 Planned)

### Changed
- **BREAKING (docs):** 6-Mode System replaces 3-Mode (RECALL/RECALL_LLM_RERANK/SYNTHESIZE/REFLECT/CHALLENGE/EXPAND)
- `idea.md` — full rewrite with 6-mode ideal, architecture flow, retrieval intelligence
- `PROJECT_STRUCTURE.md` — sections 2.1, 5, Epistemic Boundary updated to 6-mode
- `API_DOCS.md` — modes table, cURL examples updated to 6-mode
- `IMPLEMENTATION_PLAN.md` — Phase 4 checklist + test scenarios + deliverables updated to 6-mode
- `CODEBASE_STRUCTURE.md` — ModeController (6-mode), ranking.py (mode-aware weights), service.py (Source Decision Layer)
- `DATA_DESIGN.md` — section 7.2.1: Mode-Aware Ranking Weights table + app-layer architecture note
- `/api/v1/search` ranking profile standardized to **NEUTRAL** (`0.60/0.15/0.25`)
- `/api/v1/query` keeps mode-aware ranking profiles (6 modes)
- `SearchResponse` now includes `ranking_profile` for ranking-debug clarity
- Removed stale `source_type` schema references from structure docs (`CODEBASE_STRUCTURE.md`, `PROJECT_STRUCTURE.md`)
- Epistemic boundary: token-threshold (800) retired → mode-based (EXPAND = external ON)
- Retired modes: ANALYZE, TEMPORAL_COMPARE → merged into SYNTHESIZE, REFLECT
- /api/v1/query retrieval ranking now applies a small exposure-aware diversity bonus (+0.02 * 1/(1+retrieval_count), capped at 0.02) to reduce repetitive top memories.
- Exposure signal source is reasoning_logs.memory_ids (no new DB column in V1.1).
- `AI_Chat/src/components/ChatPanel.jsx` — mode selector now includes `RECALL_LLM_RERANK` (UI label `RECALL+`).
- `AI_Chat/src/components/SearchPanel.jsx` — default search threshold aligned to backend default `0.45`.
- `API_DOCS.md`, `PROJECT_STRUCTURE.md`, `CODEBASE_STRUCTURE.md`, `IMPLEMENTATION_PLAN.md` — synchronized docs for 6-mode behavior and deterministic recall branch.

### Documented (Code Gaps)
- `API_DOCS.md` — `metadata_filter` marked NOT_IMPLEMENTED, `content_type` search validation gap noted
- `API_DOCS.md` — `INVALID_MODE` error code added (422)

### Code Refactored (Reasoning Modes)
- `prompts.py` — 6-mode instructions + policies, REFLECT.external=False, EXPAND.external=True
- `prompts.py` — CHALLENGE mode now prioritizes query-matching memories, enforces Vietnamese output, and uses a 3-part challenge structure.
- `mode_controller.py` — VALID_MODES from MODE_INSTRUCTIONS keys, raises InvalidModeError
- `schemas/query.py` — ModeEnum extended with `RECALL_LLM_RERANK` for LLM-assisted memory selection
- `service.py` — EXPAND-only external, removed token-threshold + MIN_CONTEXT_TOKENS
- `ranking.py` — 6-mode weights per DATA_DESIGN 7.2.1
- `exceptions/handlers.py` — InvalidModeError (422)
- `prompt_builder.py` — docstring updated to 6 modes
- `CODEBASE_STRUCTURE.md` — all CAUTION blocks removed, specs updated
- `app/retrieval/ranking.py` — neutral profile fallback (`mode=None`) + `get_ranking_profile()`
- `app/retrieval/search.py` — `SearchFilters.mode` optional; logs resolved ranking profile
- `app/schemas/search.py` — `SearchResponse.ranking_profile` added
- `app/api/search.py` — response includes resolved `ranking_profile`

### Fixed
- `app/retrieval/search.py` — fixed asyncpg `AmbiguousParameterError` on nullable filters (`content_type`, `start_date`, `end_date`, `metadata_filter`) by adding explicit SQL casts.
- `app/exceptions/handlers.py` — `PolicyViolationError` now returns `422` instead of `500`.
- `app/reasoning/service.py` — added RECALL fallback when LLM omits citations: build deterministic `[Memory N]` response instead of failing request.
- `workers/run_embedding.py` — worker now uses `get_embedding_adapter()` (provider-aware), no hardcoded OpenAI embedding adapter.
- `app/reasoning/service.py` + `app/retrieval/relevance_gate.py` — added Relevance Gate (mode-specific top-sim floor + dynamic cutoff + max_results) to reduce semantically weak context.
- `app/reasoning/service.py` — RECALL short-circuit when no gated memories: deterministic no-memory response, skip LLM call.
- `app/schemas/query.py` + `app/schemas/search.py` — default threshold updated to `0.45` (app-layer floor model).
- `app/retrieval/search.py` + `app/retrieval/ranking.py` — controlled diversity implemented without random retrieval; semantic ranking remains primary.
- `app/reasoning/service.py` — RECALL now returns deterministic memory list when memories exist (no LLM paraphrase drift).
- `app/retrieval/ranking.py` + `app/retrieval/search.py` — added lexical anchor bonus for RECALL/CHALLENGE to prioritize direct keyword matches.
- `app/retrieval/relevance_gate.py` — tuned RECALL/CHALLENGE gate window and max_results to reduce missed same-topic memories.
- `app/retrieval/search.py` — removed DB distance-threshold filter; SQL now fetches Top-K candidates and applies relevance floors in app layer.
- `app/retrieval/search.py` — added production hardening gates: absolute floor, mode floor, score-gap filter, and mode hard cap (precision-first retrieval).
- `app/retrieval/search.py` — added same-query cooldown reorder for RECALL/CHALLENGE to reduce repeated memory sets across consecutive identical queries.
- `app/retrieval/ranking.py` — diversity bonus now capped and only applied on high-similarity memories (`similarity >= 0.70`).
- `app/config.py` — removed unused `retrieval_distance_threshold` setting.
- `app/config.py` — added `retrieval_query_cooldown_logs` to control replay anti-repeat window.
- `app/reasoning/service.py` — added `RECALL_LLM_RERANK`: LLM only reranks candidate memory indices, final response remains deterministic memory output.
- `app/retrieval/search.py` + `app/retrieval/relevance_gate.py` + `app/retrieval/ranking.py` — added mode-specific retrieval profile for `RECALL_LLM_RERANK`.
- `app/exceptions/handlers.py` + `docs/API_DOCS.md` — invalid mode list and API contract updated for `RECALL_LLM_RERANK`.

---

## [0.2.0] — 2026-02-21

### Added
- `app/llm/lmstudio_adapter.py` — LM Studio LLM adapter (OpenAI-compatible, `base_url` override)
- `app/llm/lmstudio_embedding_adapter.py` — LM Studio embedding adapter
- `LLM_PROVIDER` env var — switch between `"openai"` and `"lmstudio"` (default: `"openai"`)
- `LMSTUDIO_BASE_URL` env var — LM Studio server URL (default: `http://localhost:1234/v1`)

### Changed
- `app/deps.py` — factory pattern selects adapter based on `LLM_PROVIDER` setting (lazy imports)
- `app/config.py` — added `llm_provider` and `lmstudio_base_url` settings
- `.env` / `.env.example` — added provider configuration section

---

## [0.1.3] — 2026-02-21

### Fixed
- `metadata_filter` — previously accepted by API but silently ignored in SQL; now implemented as JSONB `@>` containment in `retrieval/search.py`
- `content_type` validation missing in `schemas/search.py` — added `field_validator` with 10 allowed content types (mirrors `schemas/query.py`)

### Added
- `personalities/default.yaml` — `mode_hints` section with per-mode `focus` + `style` for all 5 modes (RECALL/SYNTHESIZE/REFLECT/CHALLENGE/EXPAND)

### Changed
- `TODO.md` — marked 8 stale P1 sub-items as completed, bumped version to v0.1.3

---

## [0.1.2] — 2026-02-20

### Fixed
- `ImportError: cannot import name 'TIMESTAMPTZ'` — replaced with `TIMESTAMP(timezone=True)` in `app/db/models.py` (all 5 timestamp columns: `memory_records.created_at`, `.updated_at`, `embedding_jobs.created_at`, `.completed_at`, `reasoning_logs.created_at`)
- `alembic upgrade head` now runs successfully

---

## [0.1.1] — 2026-02-20

### Fixed
- Epistemic boundary rule: replaced count-based gate (`len(memories) < 3`) with token-threshold gate (`total_context_tokens < 800`). Token-threshold is now the single source of truth per V1 locked rule
- `MemoryRepository.get_pending_jobs()`: added `SELECT FOR UPDATE SKIP LOCKED` to prevent concurrent workers from processing the same embedding job
- **Docs:** `DATA_DESIGN.md` — retrieval SQL missing `AND is_summary = false` filter (added as mandatory default, overridable via `include_summaries` param)
- **Docs:** `DATA_DESIGN.md` — index overview table missing row #7 `idx_memory_embedding_model`
- **Docs:** `DATA_DESIGN.md` — migration setup referenced `alembic init alembic` (root path); corrected to `app/db/migrations/`
- **Docs:** `DATA_DESIGN.md` — section 8.2 referenced "tóm tắt 10 cái" (runtime summarization); replaced with V1 drop-only rule
- **Docs:** `DATA_DESIGN.md` — section 11.7 rewritten: V1 Strict — LLM cannot persist summaries; `is_summary` field reserved for V2
- **Docs:** `PROJECT_STRUCTURE.md` — Epistemic Boundary section rewritten with single-rule pseudocode; count-based rule explicitly retired
- **Docs:** `PROJECT_STRUCTURE.md` — Policy Guard table updated: removed "≥ 3 memory" row, added External Knowledge / Cite / Speculate columns
- **Docs:** `IMPLEMENTATION_PLAN.md` — checklist item "5 index" corrected to list all 7 named indexes

---

## [0.1.0] — 2026-02-20

### Added
- Full Phase 1–5 implementation (Foundation → Memory → Retrieval → Reasoning → API)
- `docker-compose.yml` — PostgreSQL 16 + pgvector
- `app/config.py` — Pydantic-settings, all params env-configurable
- `app/db/session.py` — Async SQLAlchemy 2.0 session factory with connection pooling
- `app/db/models.py` — ORM models: `MemoryRecord`, `EmbeddingJob`, `ReasoningLog`
- `app/db/migrations/versions/001_initial_schema.py` — Full schema: 3 tables, 2 ENUM types, 7 indexes (HNSW, GIN, UNIQUE, B-Tree), `updated_at` trigger
- `app/exceptions/handlers.py` — 7 typed exception classes + FastAPI handlers, no stacktrace leakage
- `app/logging/logger.py` — Structured JSON logger with `ContextVar` correlation ID
- `app/memory/repository.py` — Pure DB CRUD layer: `MemoryRecord`, `EmbeddingJob`
- `app/memory/service.py` — SHA256 checksum, duplicate detection, two-phase save pipeline, selective forgetting
- `app/memory/embedding_worker.py` — Async job processor: pending → processing → completed / retry (max 3)
- `app/llm/adapter.py` — Abstract `LLMAdapter` + `LLMResponse`
- `app/llm/openai_adapter.py` — OpenAI chat completions + tiktoken token counter
- `app/llm/embedding_adapter.py` — Abstract `EmbeddingAdapter`
- `app/llm/openai_embedding_adapter.py` — OpenAI async embedding, batch-safe (index-sorted)
- `app/core/token_guard.py` — `TokenGuard`: drop-only budget enforcement, V1 no summarization
- `app/core/personality.py` — YAML personality loader, LRU cached
- `app/core/prompts.py` — Locked V1 mode instructions + `ModePolicy` frozen dataclasses
- `app/retrieval/ranking.py` — Composite scoring: semantic × recency decay × importance, mode-specific weights
- `app/retrieval/search.py` — `RetrievalService`: HNSW pool → Python re-rank → diversity dedup
- `app/reasoning/mode_controller.py` — Mode → instruction + policy, safe RECALL fallback
- `app/reasoning/prompt_builder.py` — 4-part prompt assembly (System / Mode / Memory / Query)
- `app/reasoning/service.py` — `ReasoningService` orchestrator: retrieval → token guard → epistemic decision → LLM → log
- `app/api/memory.py` — `POST /api/v1/memory`, `GET /api/v1/memory/{id}`, `PATCH /api/v1/memory/{id}/archive`
- `app/api/search.py` — `POST /api/v1/search`
- `app/api/query.py` — `POST /api/v1/query`
- `app/deps.py` — Singleton LLM + embedding adapter DI providers
- `app/main.py` — FastAPI app, correlation ID middleware, CORS, DB health check
- `workers/run_embedding.py` — CLI polling loop for embedding worker
- `personalities/default.yaml` — Default AI personality (Vietnamese)
- `README.md` — Setup guide, API reference, quick start
- `.env.example` — All environment variables documented
- `requirements.txt` — Pinned dependencies

---

[Unreleased]: https://github.com/username/ai-person/compare/v0.3.0...HEAD
[0.2.0]: https://github.com/username/ai-person/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/username/ai-person/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/username/ai-person/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/username/ai-person/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/username/ai-person/releases/tag/v0.1.0

