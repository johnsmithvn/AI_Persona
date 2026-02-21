# TODO — AI Person (Bộ Não Thứ 2)

> **Version:** v0.3.0
> **Last Updated:** 2026-02-21
> **Status:** Memory Contract V1 + CLI V1 + Reasoning safety → E2E test

---

## 🔥 P0 — v0.3.0 Completed

- [x] **Memory Contract V1:**
  - [x] `content_type` → 6 fixed values (note, conversation, reflection, idea, article, log)
  - [x] Drop `source_type` column → `metadata.source` (migration 004)
  - [x] Create `docs/MEMORY_CONTRACT.md` — full spec with tag registry, examples
  - [x] Update all docs (DATA_DESIGN, API_DOCS, README, etc.)
- [x] **CLI V1 — Interactive `ai add`:**
  - [x] `cli/registry.py` — content_type, tag, type menus
  - [x] `cli/add_memory.py` — 9-step interactive flow
  - [x] `cli/person_helpers.py` — normalize + suggest
  - [x] `MemoryRepository.get_distinct_person_names()`
  - [x] `ai.ps1` — `.\ai add` command
- [x] **Reasoning Layer Safety Fixes:**
  - [x] RECALL `must_cite_memory_id = True` (was False)
  - [x] `validate_citations()` in ReasoningService — enforces `[Memory N]` format
  - [x] EXPAND "No Override" guard — memory is source of truth
  - [x] REFLECT "No Psychological Inference" guard
  - [x] Citation format instruction in PromptBuilder
  - [x] `PolicyViolationError` exception class
- [x] **ENUM → VARCHAR migration** (003) — fixes asyncpg type mismatch

- [ ] **Setup `.env`** — copy `.env.example` → `.env`, điền `OPENAI_API_KEY`
- [x] **✅ Fix REFLECT epistemic conflict:**
  - [x] `prompts.py`: đổi `REFLECT.can_use_external_knowledge = True` → `False`
  - [x] `prompts.py`: xóa external mention trong REFLECT instruction
  - [x] `service.py`: đổi sang EXPAND-only, xóa `MIN_CONTEXT_TOKENS` + token-threshold
  - [x] `service.py`: thay bằng mode-based rule (`policy.can_use_external_knowledge`)
- [x] **✅ Upgrade to 5-mode:**
  - [x] `prompts.py`: thêm SYNTHESIZE + EXPAND vào `MODE_INSTRUCTIONS` + `MODE_POLICIES`
  - [x] `mode_controller.py`: `VALID_MODES` = 5 modes, raises `InvalidModeError`
  - [x] `schemas/query.py`: `ModeEnum` với 5 values + `content_type` validator
  - [x] `ranking.py`: 5-mode weights per DATA_DESIGN 7.2.1
  - [x] `exceptions/handlers.py`: `InvalidModeError` (422)
  - [x] `prompt_builder.py`: docstring updated to 5 modes
- [x] **Chạy Docker** — `docker compose up -d` ✅
- [x] **Chạy migration** — `alembic upgrade head` ✅ — all 7 indexes created
  - `idx_memory_embedding` (HNSW)
  - `idx_memory_created_at`
  - `idx_memory_content_type`
  - `idx_memory_metadata` (GIN)
  - `idx_memory_checksum` (UNIQUE)
  - `idx_embedding_jobs_status`
  - `idx_memory_embedding_model`
- [ ] **End-to-end test thủ công:**
  - [ ] `POST /api/v1/memory` → insert thành công
  - [ ] Check `embedding_jobs` status = `pending`
  - [ ] Chạy worker: `python -m workers.run_embedding`
  - [ ] Verify `memory_records.embedding != NULL`
  - [ ] Check `embedding_jobs` status = `completed`
  - [ ] `POST /api/v1/search` → trả kết quả đúng
  - [ ] `POST /api/v1/query` với `mode=RECALL` → tra đúng
  - [ ] `POST /api/v1/query` với `mode=SYNTHESIZE` → tổng hợp memory
  - [ ] `POST /api/v1/query` với `mode=REFLECT` → nhận diện evolution
  - [ ] `POST /api/v1/query` với `mode=CHALLENGE` → verify `external_knowledge_used=false`
  - [ ] `POST /api/v1/query` với `mode=EXPAND` → verify `external_knowledge_used=true`

---

## 🟡 P1 — Nên làm sớm

- [x] **5-Mode code migration** (completed)
  - [x] 🔴 Update `_EXTERNAL_KNOWLEDGE_ALLOWED_MODES` → `{"EXPAND"}` in `reasoning/service.py`
  - [x] 🔴 Remove `MIN_CONTEXT_TOKENS` + token-threshold logic in `reasoning/service.py`
  - [x] 🔴 Replace token-threshold conditional with `if mode == "EXPAND"` in `reasoning/service.py`
  - [x] Add SYNTHESIZE + EXPAND weights to `_MODE_WEIGHTS` in `retrieval/ranking.py`
  - [x] Update `personalities/default.yaml` with SYNTHESIZE + EXPAND prompts
  - [x] Implement `metadata_filter` → SQL JSONB containment (`@>`) in `retrieval/search.py`
  - [x] Add `content_type` enum validation to `schemas/search.py`
  - [x] Add `INVALID_MODE` error to `exceptions/handlers.py`
- [ ] **Phase 0: Behavior Freeze**
  - [ ] Chốt system prompt final trong `personalities/default.yaml`
  - [ ] Test 30 lượt chat tay, verify AI giữ đúng nhân cách
  - [ ] Verify mode RECALL / REFLECT / CHALLENGE hoạt động đúng
  - [ ] Document kết quả vào `docs/BEHAVIOR_FREEZE.md`
- [ ] **Verify epistemic boundary thực tế:**
  - [ ] REFLECT với 0 memory → trả "không có memory liên quan", external_knowledge_used=false 
  - [ ] REFLECT với nhiều memory dài (>800 tokens) → `external_knowledge_used=false`
- [ ] **Cập nhật GitHub repo URLs trong `CHANGELOG.md`** (khi có remote)
- [ ] **Cập nhật Project Context** trong `PROMPT.md` skill:
  - `Project name:` AI Person — Bộ Não Thứ 2
  - `Current version:` v0.1.1
  - `Tech stack:` FastAPI, SQLAlchemy 2.0, asyncpg, pgvector, OpenAI
  - `Current progress:` All phases complete, pending first real run

---

## 🔵 P2 — Backlog / V2

- [x] **`local_adapter.py`** — LM Studio local model adapter (via OpenAI-compatible API)
- [ ] **Summary persistence** — LLM-generated summary với user approval flow (V2)
  - `is_summary=true`, `metadata.parent_id`, `metadata.generated_by="system"`
  - Mặc định excluded khỏi retrieval
- [ ] **Chunking tự động** — auto-chunk PDF / article dài trước khi insert (V2)
- [ ] **Partition strategy** — khi > 1M records, partition `memory_records` theo tháng
- [ ] **Re-embed pipeline** — khi đổi embedding model, re-embed toàn bộ records (V2)
- [ ] **Backup strategy** — cron daily backup, verify checksum integrity

---

## ✅ Đã hoàn thành

- [x] **Phase 1: Foundation** — DB, ORM (3 tables + 7 indexes), migration, session, config, logging, exceptions
- [x] **Phase 2: Memory Infrastructure** — MemoryService, EmbeddingWorker, repository, embedding adapters
- [x] **Phase 3: Retrieval Engine** — RetrievalService, ranking formula (mode-aware), diversity guard, TokenGuard
- [x] **Phase 4: Reasoning Layer** — ReasoningService, ModeController, PromptBuilder, LLM adapters
- [x] **Phase 5: API Layer** — memory / search / query endpoints, deps DI, main.py, CORS, correlation ID middleware
- [x] **Documentation** — README.md, .env.example, docker-compose.yml, personalities/default.yaml
- [x] **Fix #1: Epistemic Boundary** — token-threshold (800) replaces count-based rule in code + docs
- [x] **Fix #2: Index count** — 5 → 7, named in IMPLEMENTATION_PLAN checklist
- [x] **Fix #3: Migration path** — `alembic init alembic` corrected to `app/db/migrations` in DATA_DESIGN
- [x] **Fix #4: is_summary filter** — `AND is_summary = false` added to retrieval SQL in DATA_DESIGN
- [x] **Fix #5: Summary policy** — V1 Strict: LLM không persist, section 8.2 drop-only
- [x] **Worker concurrency** — `SELECT FOR UPDATE SKIP LOCKED` in `get_pending_jobs()`
- [x] **CHANGELOG.md** — created, v0.1.0 + v0.1.1 documented
- [x] **TODO.md** — this file
- [x] **API_DOCS.md** — full API reference (5 endpoints, schemas, modes, error codes, cURL examples)
- [x] **OpenClaw analysis** — applied doc recommendations (Memory-First Principle, engagement V2, etc.)
- [x] **5-Mode Design** — docs migration: RECALL/SYNTHESIZE/REFLECT/CHALLENGE/EXPAND
  - `idea.md`: full rewrite with 5-mode ideal + architecture flow
  - `PROJECT_STRUCTURE.md`: sections 2.1, 5, Epistemic Boundary, Policy Guard
  - `API_DOCS.md`: modes table, cURL examples
  - `IMPLEMENTATION_PLAN.md`: Phase 4 checklist + test scenarios
  - Retired: ANALYZE, TEMPORAL_COMPARE → merged into SYNTHESIZE, REFLECT
  - Retired: token-threshold (800) → mode-based (EXPAND = external ON)
- [x] **Fix #6: metadata_filter** — JSONB `@>` containment implemented in `retrieval/search.py`
- [x] **Fix #7: content_type validator** — `field_validator` added to `schemas/search.py`
- [x] **Fix #8: Personality mode_hints** — `personalities/default.yaml` updated with 5-mode focus + style hints
- [x] **LM Studio Adapter** — `lmstudio_adapter.py` + `lmstudio_embedding_adapter.py`, provider switch via `LLM_PROVIDER` env var
