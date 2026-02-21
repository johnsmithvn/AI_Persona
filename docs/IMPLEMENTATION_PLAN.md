# IMPLEMENTATION PLAN — AI Person (Bộ Não Thứ 2)

> **Project:** AI Person — Personal Memory-First AI System  
> **Version:** V1 (v0.2.0)  
> **Last Updated:** 2026-02-21  
> **Estimated Timeline:** 6–8 tuần  
> **Status:** Phase 4 complete, LM Studio adapter added → E2E testing next

---

## 1. Tổng Quan Triển Khai

### 1.1. Nguyên Tắc Build

| Nguyên Tắc | Chi Tiết |
|---|---|
| **Ship fast but clean** | Không overkill, không placeholder logic |
| **Memory trước, LLM sau** | Memory infrastructure phải chạy trước khi gắn LLM |
| **Test thực tế** | User test thủ công, không generate test case tự động |
| **Incremental** | Mỗi phase phải có deliverable chạy được |
| **Không trộn vai trò** | Mỗi layer có ranh giới rõ ràng |

### 1.2. Thứ Tự Ưu Tiên

```
1. Database        → Xương sống
2. Memory Layer    → Lõi hệ thống (50%)
3. Retrieval Layer → Tìm đúng memory
4. Reasoning Layer → Suy luận
5. API Layer       → Expose endpoints
6. Polish          → Logging, exceptions, worker
```

---

## 2. Phân Pha Triển Khai

### PHASE 0: Behavior Freeze (Trước khi build DB)

Mục tiêu:
- Chốt system prompt
- Chốt mode instructions
- Test 30 lượt chat tay
- Verify AI giữ đúng nhân cách

Deliverables:
[ ] System prompt final
[ ] Mode instructions final
[ ] Policy guard rõ ràng
[ ] Test transcript 30 lượt
### PHASE 1: Foundation (Tuần 1–2)

> **Mục tiêu:** Database chạy, có thể insert + query memory bằng code.

#### Deliverables

| # | Task | Output | Ưu Tiên |
|---|---|---|---|
| 1.1 | Setup project structure | Tạo toàn bộ thư mục theo CODEBASE_STRUCTURE.md | P0 |
| 1.2 | Docker Compose cho PostgreSQL + pgvector | `docker-compose.yml` chạy được | P0 |
| 1.3 | Config & Environment | `config.py`, `.env`, `.env.example` | P0 |
| 1.4 | DB Session & ORM Models | `db/session.py`, `db/models.py` | P0 |
| 1.5 | Alembic setup + initial migration | Schema DB tạo đúng | P0 |
| 1.6 | MemoryRepository | CRUD operations cho `memory_records` | P0 |
| 1.7 | Verify với script test thủ công | Insert + query thành công | P0 |

#### Checklist

```
[x] Tạo cấu trúc thư mục đầy đủ
[x] docker-compose.yml với PostgreSQL 16 + pgvector
[x] docker compose up chạy thành công
[x] .env.example với tất cả biến cần thiết
[x] config.py load env đúng
[x] SQLAlchemy async session factory
[x] ORM models: MemoryRecord, EmbeddingJob, ReasoningLog
[x] ENUM types tạo đúng trong DB
[x] Alembic init + first migration
[x] alembic upgrade head chạy không lỗi
[x] Tất cả 7 index tạo đúng:
      idx_memory_embedding (HNSW), idx_memory_created_at, idx_memory_content_type,
      idx_memory_metadata (GIN), idx_memory_checksum (UNIQUE),
      idx_embedding_jobs_status, idx_memory_embedding_model
[ ] MemoryRepository.insert() hoạt động         ← pending end-to-end test
[ ] MemoryRepository.get_by_id() hoạt động      ← pending end-to-end test
[ ] MemoryRepository.get_by_checksum() hoạt động ← pending end-to-end test
[x] requirements.txt đầy đủ
```

#### docker-compose.yml (Reference)

```yaml
version: '3.8'
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: ai_person
      POSTGRES_USER: ai_user
      POSTGRES_PASSWORD: ai_password
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

---

### PHASE 2: Memory Infrastructure (Tuần 2–3)

> **Mục tiêu:** Có thể lưu memory + embed async. Đây là 50% hệ thống.

#### Deliverables

| # | Task | Output | Ưu Tiên |
|---|---|---|---|
| 2.1 | Pydantic schemas cho Memory | `schemas/memory.py` | P0 |
| 2.2 | MemoryService | `memory/service.py` — save, checksum, dedup | P0 |
| 2.3 | Embedding Worker | `memory/embedding_worker.py` — async embed | P0 |
| 2.4 | Worker runner | `workers/run_embedding.py` — CLI entry | P0 |
| 2.5 | Memory API endpoints | `api/memory.py` — POST + GET | P1 |
| 2.6 | Exception handling cơ bản | `exceptions/handlers.py` | P1 |
| 2.7 | Test thủ công end-to-end | Insert qua API → embedding worker xử lý | P0 |

#### Checklist

```
[x] MemoryCreateRequest schema validation
[x] MemoryResponse schema
[x] SHA256 checksum computation
[x] Duplicate detection (by checksum)
[x] MemoryService.save_memory() hoàn chỉnh
[x] EmbeddingJob tạo đúng khi save memory
[x] EmbeddingWorker gọi EmbeddingAdapter interface
[x] EmbeddingWorker update memory_records.embedding
[x] EmbeddingWorker xử lý retry (max 3 attempts)
[x] EmbeddingWorker xử lý failure gracefully
[x] Worker CLI chạy được: python -m workers.run_embedding
[ ] POST /api/v1/memory trả response đúng     ← pending end-to-end test
[ ] GET /api/v1/memory/{id} trả response đúng ← pending end-to-end test
[x] DuplicateMemoryError được handle
[x] MemoryNotFoundError được handle
[ ] End-to-end: insert → worker embed → verify embedding in DB ← pending
```

#### Verification Script

```python
# Test thủ công:
# 1. POST /api/v1/memory với raw_text
# 2. Check embedding_jobs status = pending
# 3. Chạy worker
# 4. Check memory_records.embedding != NULL
# 5. Check embedding_jobs status = completed
```

---

### PHASE 3: Retrieval Engine (Tuần 3–4)

> **Mục tiêu:** Semantic search hoạt động chính xác. Ranking formula đúng.

#### Deliverables

| # | Task | Output | Ưu Tiên |
|---|---|---|---|
| 3.1 | Search schemas | `schemas/search.py` | P0 |
| 3.2 | RetrievalService | `retrieval/search.py` — semantic search + filter | P0 |
| 3.3 | Ranking module | `retrieval/ranking.py` — scoring formula | P0 |
| 3.4 | Diversity guard | Loại bỏ memory trùng lặp | P1 |
| 3.5 | Token guard cơ bản | `core/token_guard.py` | P1 |
| 3.6 | Search API endpoint | `api/search.py` — POST /search | P0 |
| 3.7 | Test search quality | Insert 50 records → search → verify relevance | P0 |

#### Checklist

```
[x] SearchRequest schema (query, content_type, date range, limit, threshold)
[x] SearchResponse schema (results + total)
[x] Embed user query (qua EmbeddingAdapter)
[x] SQL query với cosine distance + HNSW
[x] Filter embedding_model đúng với model active
[x] Filter: content_type
[x] Filter: time range (start_date, end_date)
[x] Filter: metadata JSONB
[x] Distance threshold (< 0.7)
[x] Candidate pool (500)
[x] Ranking formula configurable theo mode
[x] Diversity guard (cosine > 0.95 → giữ 1)
[x] TokenGuard.check_budget() cơ bản
[ ] POST /api/v1/search hoạt động  ← pending end-to-end test
[x] Hybrid context strategy: V1 Drop-only (không summarize — xem DATA_DESIGN 8.2)
```

#### Ranking Formula Verification

```
Cần verify:
- Memory mới + quan trọng + semantic gần → top
- Memory cũ + ít quan trọng + semantic xa → bottom
- Memory rất gần semantic nhưng cũ 5 năm → không dominate
```

---

### PHASE 4: Reasoning Layer (Tuần 4–6)

> **Mục tiêu:** Hệ thống có thể nhận câu hỏi → suy luận → trả lời dựa trên memory.

#### Deliverables

| # | Task | Output | Ưu Tiên |
|---|---|---|---|
| 4.1 | Query schemas | `schemas/query.py` | P0 |
| 4.2 | Personality YAML | `personalities/default.yaml` | P0 |
| 4.3 | Mode Controller | `reasoning/mode_controller.py` — 5 modes | P0 |
| 4.4 | Prompt Builder | `reasoning/prompt_builder.py` — 4 phần | P0 |
| 4.5 | LLM Adapter (OpenAI) | `llm/adapter.py`, `llm/openai_adapter.py` | P0 |
| 4.6 | Reasoning Service | `reasoning/service.py` — orchestrator | P0 |
| 4.7 | Reasoning Logs | Insert vào `reasoning_logs` sau mỗi query | P1 |
| 4.8 | Query API endpoint | `api/query.py` — POST /query | P0 |
| 4.9 | Policy guard cho mỗi mode | Ràng buộc hành vi LLM | P1 |
| 4.10 | Test 30 lượt chat thực tế | Verify chất lượng reasoning | P0 |
| 4.11 | Source Decision Layer | Epistemic boundary: `mode == EXPAND` → external ON, others → OFF | P0 |

#### Checklist

```
[x] QueryRequest schema (query, mode)
[x] QueryResponse schema (response, memory_used, token_usage, external_knowledge_used)
[x] default.yaml personality file
[x] ModeController.get_instruction('RECALL')
[ ] ModeController.get_instruction('SYNTHESIZE')  ← NEW
[x] ModeController.get_instruction('REFLECT')
[x] ModeController.get_instruction('CHALLENGE')
[ ] ModeController.get_instruction('EXPAND')  ← NEW
[x] ModeController.get_policy() cho mỗi mode
[x] PromptBuilder.build() — 4 phần không trộn
[x] LLMAdapter abstract class
[ ] OpenAIAdapter.generate() hoạt động  ← pending end-to-end test (cần OPENAI_API_KEY)
[ ] OpenAIAdapter.count_tokens() hoạt động ← pending
[x] ReasoningService.process_query() full flow
[x] Flow: query → retrieval → mode → prompt → LLM → response
[x] Memory_used trả về đúng list memory_ids
[x] reasoning_logs insert đúng
[ ] Source Decision Layer: EXPAND → external ON, others → OFF  ← code update needed
[ ] POST /api/v1/query hoạt động  ← pending end-to-end test
[ ] RECALL mode: trả nguyên văn, không suy diễn  ← pending
[ ] SYNTHESIZE mode: tổng hợp nhiều memory, structured  ← pending (NEW)
[ ] REFLECT mode: phân tích evolution, cite source  ← pending
[ ] CHALLENGE mode: chỉ ra mâu thuẫn, logic yếu  ← pending
[ ] EXPAND mode: memory + external kết hợp  ← pending (NEW)
[ ] Test 30 lượt chat: verify chất lượng  ← Phase 0 (Behavior Freeze)
[ ] Test: hệ thống nói "không biết" khi không có memory  ← pending
```

#### Test Scenarios

```
1. RECALL: "Tao từng viết gì về LoRA?"
   → Expect: trả nguyên văn memory liên quan

2. SYNTHESIZE: "Tổng hợp những gì tao biết về fine-tuning"
   → Expect: gom nhiều memory → structured summary

3. REFLECT: "Tư duy của tao về AI thay đổi thế nào?"
   → Expect: nhận diện pattern, timeline, evolution

4. CHALLENGE: "Hướng thiết kế này có ổn không?"
   → Expect: chỉ ra mâu thuẫn với memory cũ

5. EXPAND: "So sánh LoRA với QLoRA theo kiến thức mới nhất"
   → Expect: memory + external knowledge, flag external_knowledge_used=true

6. No memory: "Tao nghĩ gì về blockchain?"
   → Expect: "Không có memory liên quan"
```

---

### PHASE 5: Production Polish (Tuần 6–8)

> **Mục tiêu:** Hệ thống ổn định, có logging, error handling, sẵn sàng dùng hàng ngày.

#### Deliverables

| # | Task | Output | Ưu Tiên |
|---|---|---|---|
| 5.1 | Structured logging | `logging/logger.py` — JSON logging | P1 |
| 5.2 | Correlation ID | Mỗi request có unique ID | P1 |
| 5.3 | Exception handlers hoàn chỉnh | Tất cả error cases covered | P1 |
| 5.4 | Dependency injection cleanup | `deps.py` hoàn chỉnh | P1 |
| 5.5 | FastAPI main.py hoàn chỉnh | Startup/shutdown, CORS, middleware | P1 |
| 5.6 | README.md | Hướng dẫn setup + chạy | P2 |
| 5.7 | Backup strategy | pg_dump script hoặc guide | P2 |
| 5.8 | Performance baseline | Benchmark retrieval latency | P2 |

#### Checklist

```
[x] Structured logging (JSON format)
[x] Correlation ID middleware
[x] Log retrieval scores (debug)
[x] Log memory_ids used (audit)
[x] Log token usage (cost tracking)
[x] FastAPI startup event (DB connection)
[x] FastAPI shutdown event (cleanup)
[x] CORS configuration
[x] Error response format chuẩn hóa
[x] Không leak stacktrace
[x] deps.py: DB session injection
[x] deps.py: Config injection
[x] deps.py: LLM adapter injection
[x] README.md: setup guide
[x] README.md: API documentation
[ ] Backup script / guide  ← P2
[ ] Benchmark: retrieval latency < 500ms cho 10K records  ← P2
[ ] Benchmark: end-to-end query < 3s  ← P2
```

---

## 3. V1 Scope — Cái Gì LÀM / KHÔNG Làm

### 3.1. V1 LÀM

| Feature | Chi Tiết |
|---|---|
| Text memory | Lưu mọi loại text (note, quote, reflection...) |
| Semantic search | Cosine similarity qua pgvector HNSW |
| Time filter | Query theo khoảng thời gian |
| Content type filter | Query theo loại nội dung |
| Metadata filter | Query theo JSONB metadata |
| 5 modes | RECALL, SYNTHESIZE, REFLECT, CHALLENGE, EXPAND |
| Ranking formula | Semantic + recency + importance |
| Token budget | Giới hạn context gửi LLM |
| Async embedding | Worker xử lý offline |
| Checksum integrity | SHA256 verify data |
| Reasoning logs | Track toàn bộ suy luận |
| OpenAI / LM Studio integration | Embedding + LLM (dual provider) |

### 3.2. V1 KHÔNG Làm

| Feature | Lý Do | Khi Nào |
|---|---|---|
| File upload pipeline | Cần chunking, parsing phức tạp | V2 |
| OCR / Image caption | Cần thêm model + pipeline | V2 |
| ANALYZE mode | Dùng chung logic REFLECT | V2 |
| TEMPORAL_COMPARE mode | Sub-mode của REFLECT | V2 |
| Auto mode classifier | Phức tạp, user chọn thủ công trước | V2 |
| Streaming response | Complexiy thêm | V2 |
| Local LLM (LM Studio) | ✅ Implemented in v0.2.0 | Done |
| Multi-tenant | Thiết kế cho 1 user | Không cần |
| Kubernetes | 1 server đủ | Không cần |
| Microservice | Monolith tốt hơn ở scale này | Không cần |
| Sharding | Chưa cần < 1M records | Khi > 1M |
| Role system | 1 user duy nhất | Không cần |
| Automated tests | User test thủ công | Theo yêu cầu |

---

## 4. Tech Stack Setup Guide

### 4.1. Prerequisites

| Tool | Version | Mục Đích |
|---|---|---|
| Python | 3.11+ | Runtime |
| Docker | 20.10+ | PostgreSQL container |
| Docker Compose | 2.0+ | Service orchestration |
| Git | 2.40+ | Version control |

### 4.2. Setup Steps

```bash
# 1. Clone project
git clone <repo>
cd ai-person

# 2. Tạo virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# hoặc
.\venv\Scripts\activate   # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment
cp .env.example .env
# Edit .env: thêm OPENAI_API_KEY, DATABASE_URL

# 5. Start database
docker compose up -d

# 6. Run migrations
alembic upgrade head

# 7. Start API server
uvicorn app.main:app --reload --port 8000

# 8. Start embedding worker (terminal khác)
python -m workers.run_embedding
```

### 4.3. .env.example

```env
# Database
DATABASE_URL=postgresql+asyncpg://ai_user:ai_password@localhost:5432/ai_person

# OpenAI (chỉ cần nếu LLM_PROVIDER=openai)
OPENAI_API_KEY=sk-your-key-here

# Provider: "openai" hoặc "lmstudio"
LLM_PROVIDER=lmstudio
LMSTUDIO_BASE_URL=http://localhost:1234/v1

# Embedding
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# LLM
LLM_MODEL=gpt-4.1-mini

# App
MAX_CONTEXT_TOKENS=3000
LOG_LEVEL=INFO
DEBUG=false
```

---

## 5. Milestones & Acceptance Criteria

### Milestone 1: "Database Works" (End of Phase 1)
- [ ] `docker compose up` chạy PostgreSQL + pgvector
- [ ] `alembic upgrade head` tạo schema không lỗi
- [ ] Insert 1 record vào `memory_records` thành công
- [ ] Query record bằng ID thành công

### Milestone 2: "Memory Works" (End of Phase 2)
- [ ] POST `/api/v1/memory` lưu memory + tạo embedding job
- [ ] Worker embed memory thành công
- [ ] GET `/api/v1/memory/{id}` trả đúng data
- [ ] Duplicate detection hoạt động

### Milestone 3: "Search Works" (End of Phase 3)
- [ ] POST `/api/v1/search` trả kết quả semantic search
- [ ] Ranking formula cho kết quả hợp lý
- [ ] Filter theo content_type, time range hoạt động
- [ ] Threshold loại bỏ memory không liên quan

### Milestone 4: "Brain Works" (End of Phase 4)
- [ ] POST `/api/v1/query` với mode RECALL trả nguyên văn
- [ ] Mode REFLECT tổng hợp nhiều memory
- [ ] Mode CHALLENGE chỉ ra mâu thuẫn
- [ ] `memory_used` trong response chính xác
- [ ] `reasoning_logs` ghi đúng

### Milestone 5: "Production Ready" (End of Phase 5)
- [ ] Structured logging hoạt động
- [ ] Error handling không leak stacktrace
- [ ] Retrieval latency < 500ms (10K records)
- [ ] End-to-end query < 3s
- [ ] README đủ để người khác setup

---

## 6. Risk Mitigation During Implementation

### 6.1. Rủi Ro Kỹ Thuật

| Rủi Ro | Xác Suất | Tác Động | Giải Pháp |
|---|---|---|---|
| OpenAI API rate limit | Trung bình | Embedding worker chậm | Retry logic + exponential backoff |
| pgvector performance kém | Thấp | Search chậm | HNSW tuning, ef_search adjustment |
| Token cost cao | Trung bình | Chi phí hàng tháng | Token guard strict, summarization |
| Embedding quality kém | Thấp | Search không chính xác | Đổi model, re-embed |
| Schema migration lỗi | Thấp | Data loss | Backup trước migration, test DB copy |

### 6.2. Rủi Ro Quy Trình

| Rủi Ro | Giải Pháp |
|---|---|
| Scope creep (thêm feature ngoài V1) | Strict V1 scope, mọi thứ khác → V2 |
| Trộn vai trò giữa layers | Code review theo CODEBASE_STRUCTURE.md |
| Không test đủ trước khi tiếp | Mỗi phase có acceptance criteria rõ |

---

## 7. Git Workflow

### 7.1. Branch Strategy

```
main                    ← production-ready
├── develop             ← integration branch
│   ├── feature/phase1-foundation
│   ├── feature/phase2-memory
│   ├── feature/phase3-retrieval
│   ├── feature/phase4-reasoning
│   └── feature/phase5-polish
```

### 7.2. Commit Convention

```
feat: add memory service with checksum validation
fix: handle duplicate memory insert gracefully
refactor: extract ranking logic to separate module
docs: update IMPLEMENTATION_PLAN after phase 1
chore: setup alembic migrations
```

### 7.3. Versioning

| Phase | Version | Type |
|---|---|---|
| Phase 1 complete | v0.1.0 | Foundation |
| Phase 2 complete | v0.2.0 | Memory infrastructure |
| Phase 3 complete | v0.3.0 | Retrieval engine |
| Phase 4 complete | v0.4.0 | Reasoning layer |
| Phase 5 complete | v1.0.0 | **Production V1** |

---

## 8. Post-V1 Roadmap (V2 Preview)

| Feature | Ưu Tiên | Mô Tả |
|---|---|---|
| File upload (PDF, image) | P1 | Chunking + parsing pipeline |
| Local embedding model | P1 | bge-small / e5-small (replace OpenAI embedding) |
| ~~Local LLM (LM Studio)~~ | ~~P1~~ | ✅ **Done in v0.2.0** |
| ANALYZE mode | P2 | Technical review mode |
| TEMPORAL_COMPARE mode | P2 | So sánh evolution theo thời gian |
| Auto mode classifier | P2 | Tự đoán mode từ câu hỏi |
| Summarization layer | P2 | Memory compression cho memory dài |
| Redis cache | P3 | Cache retrieval results |
| Web UI | P3 | Frontend minimal |
| Streaming response | P3 | Real-time LLM output |
| Backup automation | P3 | Scheduled pg_dump |
| Re-embed pipeline | P3 | Đổi embedding model toàn bộ |

---

## 9. Tài Liệu Liên Quan

| Tài liệu | Mô tả |
|---|---|
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | Kiến trúc tổng thể, triết lý, flows |
| [DATA_DESIGN.md](DATA_DESIGN.md) | DB schema, index, retrieval SQL, ranking formula |
| [CODEBASE_STRUCTURE.md](CODEBASE_STRUCTURE.md) | Cấu trúc thư mục, file responsibilities |
