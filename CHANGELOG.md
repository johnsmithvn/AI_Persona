# Changelog

All notable changes to **AI Person — Bộ Não Thứ 2** will be documented in this file.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)  
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [Unreleased]

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

[Unreleased]: https://github.com/username/ai-person/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/username/ai-person/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/username/ai-person/releases/tag/v0.1.0
