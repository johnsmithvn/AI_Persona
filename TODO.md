# TODO — AI Person (Bộ Não Thứ 2)

> **Version:** v0.1.2
> **Last Updated:** 2026-02-20
> **Status:** Migration done → API server running → manual end-to-end test next

---

## 🔥 P0 — Phải làm ngay (trước khi dùng thực tế)

- [ ] **Setup `.env`** — copy `.env.example` → `.env`, điền `OPENAI_API_KEY`
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
  - [ ] `POST /api/v1/query` với `mode=RECALL` → răn đúng
  - [ ] `POST /api/v1/query` với `mode=REFLECT` → verify `external_knowledge_used` flag
  - [ ] `POST /api/v1/query` với `mode=CHALLENGE` → verify `external_knowledge_used=false` luôn

---

## 🟡 P1 — Nên làm sớm

- [ ] **Wire `EPISTEMIC_MIN_CONTEXT_TOKENS` vào `config.py`**
  - Hiện tại `MIN_CONTEXT_TOKENS = 800` đang hardcode trong `app/reasoning/service.py`
  - Cần đưa vào `Settings` class trong `config.py` để config qua `.env`
- [ ] **Phase 0: Behavior Freeze**
  - [ ] Chốt system prompt final trong `personalities/default.yaml`
  - [ ] Test 30 lượt chat tay, verify AI giữ đúng nhân cách
  - [ ] Verify mode RECALL / REFLECT / CHALLENGE hoạt động đúng
  - [ ] Document kết quả vào `docs/BEHAVIOR_FREEZE.md`
- [ ] **Verify epistemic boundary thực tế:**
  - [ ] REFLECT với 0 memory → `external_knowledge_used=true`
  - [ ] REFLECT với nhiều memory dài (>800 tokens) → `external_knowledge_used=false`
- [ ] **Cập nhật GitHub repo URLs trong `CHANGELOG.md`** (khi có remote)
- [ ] **Cập nhật Project Context** trong `PROMPT.md` skill:
  - `Project name:` AI Person — Bộ Não Thứ 2
  - `Current version:` v0.1.1
  - `Tech stack:` FastAPI, SQLAlchemy 2.0, asyncpg, pgvector, OpenAI
  - `Current progress:` All phases complete, pending first real run

---

## 🔵 P2 — Backlog / V2

- [ ] **`local_adapter.py`** — LM Studio / Ollama local model adapter (V2)
- [ ] **Summary persistence** — LLM-generated summary với user approval flow (V2)
  - `is_summary=true`, `metadata.parent_id`, `metadata.generated_by="system"`
  - Mặc định excluded khỏi retrieval
- [ ] **TEMPORAL_COMPARE mode** — so sánh memory theo mốc thời gian (V2)
- [ ] **ANALYZE mode** — technical review, logic phân tích trung lập (V2)
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
