# CODEBASE STRUCTURE — AI Person (Bộ Não Thứ 2)

> **Project:** AI Person — Personal Memory-First AI System  
> **Version:** V1 (v0.3.0)  
> **Last Updated:** 2026-02-22  
> **Framework:** FastAPI + SQLAlchemy 2.0 (async)  
> **Language:** Python 3.11+

---

## 1. Cấu Trúc Thư Mục Chuẩn V1

```
ai-person/
│
├── app/                              # Application root
│   ├── __init__.py
│   ├── main.py                       # FastAPI app entry point
│   ├── config.py                     # Environment config (dotenv)
│   ├── deps.py                       # Dependency injection (FastAPI Depends)
│   │
│   ├── api/                          # HTTP layer — chỉ xử lý request/response
│   │   ├── __init__.py
│   │   ├── memory.py                 # POST /memory, GET /memory/{id}
│   │   ├── search.py                 # POST /search
│   │   └── query.py                  # POST /query (reasoning)
│   │
│   ├── schemas/                      # Pydantic models — validation & serialization
│   │   ├── __init__.py
│   │   ├── memory.py                 # MemoryCreateRequest, MemoryResponse
│   │   ├── search.py                 # SearchRequest, SearchResponse
│   │   └── query.py                  # QueryRequest, QueryResponse
│   │
│   ├── memory/                       # Memory infrastructure — lưu & embed
│   │   ├── __init__.py
│   │   ├── service.py                # MemoryService (save, checksum, create job)
│   │   ├── repository.py             # DB operations cho memory_records
│   │   └── embedding_worker.py       # Async embedding processor
│   │
│   ├── retrieval/                    # Retrieval engine — tìm memory
│   │   ├── __init__.py
│   │   ├── search.py                 # RetrievalService (semantic search + filter)
│   │   └── ranking.py                # Ranking formula, diversity guard
│   │
│   ├── reasoning/                    # Reasoning layer — suy luận
│   │   ├── __init__.py
│   │   ├── service.py                # ReasoningService (orchestrator)
│   │   ├── mode_controller.py        # Mode selection + policy guard
│   │   └── prompt_builder.py         # Build prompt từ 4 phần
│   │
│   ├── llm/                          # LLM abstraction — adapter pattern
│   │   ├── __init__.py
│   │   ├── adapter.py                # LLMAdapter abstract base
│   │   ├── embedding_adapter.py      # EmbeddingAdapter abstract base
│   │   ├── openai_adapter.py         # OpenAI LLM implementation
│   │   ├── openai_embedding_adapter.py  # OpenAI embedding
│   │   ├── lmstudio_adapter.py       # LM Studio LLM (local)
│   │   └── lmstudio_embedding_adapter.py  # LM Studio embedding (local)
│   │
│   ├── core/                         # Core policies & configuration
│   │   ├── __init__.py
│   │   ├── personality.py            # Load personality từ YAML
│   │   ├── prompts.py                # System prompts & mode instructions
│   │   └── token_guard.py            # Token budget management
│   │
│   ├── db/                           # Database infrastructure
│   │   ├── __init__.py
│   │   ├── session.py                # Async SQLAlchemy session factory
│   │   ├── models.py                 # SQLAlchemy ORM models
│   │   └── migrations/               # Alembic migrations
│   │       ├── env.py
│   │       ├── script.py.mako
│   │       └── versions/
│   │           └── 001_initial_schema.py
│   │
│   ├── exceptions/                   # Custom exceptions — error handling chuẩn
│   │   ├── __init__.py
│   │   └── handlers.py               # Exception classes + FastAPI handlers
│   │
│   └── logging/                      # Structured logging
│       ├── __init__.py
│       └── logger.py                 # Logger setup, correlation ID
│
├── cli/                              # Interactive CLI ingestion
│   ├── __init__.py
│   ├── add_memory.py                 # `ai add` — interactive memory creation
│   ├── registry.py                   # Content type, tag, type menus
│   └── person_helpers.py             # Person name normalize + suggest
│
├── AI_Chat/                          # React chat UI (Vite)
│   ├── src/
│   │   ├── api/client.js             # API client (6 endpoints)
│   │   ├── components/
│   │   │   ├── ChatPanel.jsx         # 5-mode reasoning chat
│   │   │   ├── MemoryPanel.jsx       # Add + lookup memory
│   │   │   ├── SearchPanel.jsx       # Semantic search + filters
│   │   │   └── Sidebar.jsx           # Navigation + status
│   │   ├── App.jsx                   # Layout + health polling
│   │   ├── App.css                   # Component styles
│   │   ├── index.css                 # Design system (dark theme)
│   │   └── main.jsx                  # Entry point
│   ├── index.html
│   └── package.json
│
├── workers/                          # Background worker entrypoints
│   ├── __init__.py
│   └── run_embedding.py              # CLI entry: python -m workers.run_embedding
│
├── personalities/                    # YAML personality files
│   └── default.yaml                  # Default personality config
│
├── tests/                            # Test suite
│   ├── __init__.py
│   ├── test_memory/
│   │   ├── __init__.py
│   │   └── test_service.py
│   ├── test_retrieval/
│   │   ├── __init__.py
│   │   └── test_search.py
│   └── test_reasoning/
│       ├── __init__.py
│       └── test_service.py
│
├── docs/                             # Documentation
│   ├── PROJECT_STRUCTURE.md
│   ├── DATA_DESIGN.md
│   ├── CODEBASE_STRUCTURE.md
│   └── IMPLEMENTATION_PLAN.md
│
├── docker-compose.yml                # PostgreSQL + pgvector
├── .env                              # Environment variables (KHÔNG commit)
├── .env.example                      # Template cho .env
├── .gitignore
├── requirements.txt
├── alembic.ini
└── README.md
```

---

## 2. Phân Cấp Trách Nhiệm (Layer Responsibility)

### 2.1. Bảng Tổng Quan

| Layer | Thư mục | Trách Nhiệm | KHÔNG Được Làm |
|---|---|---|---|
| **API** | `app/api/` | Nhận HTTP request, validate, trả response | Chứa business logic |
| **Schemas** | `app/schemas/` | Định nghĩa request/response model (Pydantic) | Chứa logic xử lý |
| **Memory** | `app/memory/` | Lưu raw_text, tính checksum, tạo embedding job | Gọi LLM |
| **Retrieval** | `app/retrieval/` | Semantic search, filter, ranking | Gọi LLM, suy luận |
| **Reasoning** | `app/reasoning/` | Orchestrate retrieval → mode → prompt → LLM | Trực tiếp query DB |
| **LLM** | `app/llm/` | Gọi model, trả response | Biết gì về memory structure |
| **Core** | `app/core/` | Personality, prompts, token budget | DB operations |
| **DB** | `app/db/` | Session, ORM models, migrations | Business logic |
| **CLI** | `cli/` | Interactive ingestion (reuses MemoryService) | Query DB trực tiếp, bypass schema |
| **Chat UI** | `AI_Chat/` | React frontend, calls API qua HTTP | Business logic, DB access |
| **Workers** | `workers/` | Background job execution | HTTP handling |
| **Exceptions** | `app/exceptions/` | Error classes, error handlers | Business logic |
| **Logging** | `app/logging/` | Structured logging, correlation ID | Business logic |

### 2.2. Nguyên Tắc Tách Layer

```
API → KHÔNG chứa logic
Memory → KHÔNG gọi LLM
Retrieval → KHÔNG suy luận
LLM → KHÔNG biết memory
Reasoning → KHÔNG query DB trực tiếp
```

**Thứ nguy hiểm nhất không phải complexity. Mà là TRỘN VAI TRÒ.**

---

## 3. Chi Tiết Từng File

### 3.1. `app/main.py` — Entry Point

```python
# Trách nhiệm:
# - Khởi tạo FastAPI app
# - Mount routers
# - Startup/shutdown events (DB connection)
# - Exception handlers
```

**Endpoints đăng ký:**
- `POST /api/v1/memory` → Lưu memory
- `GET  /api/v1/memory/{id}` → Lấy 1 memory
- `POST /api/v1/search` → Semantic search
- `POST /api/v1/query` → Reasoning query

### 3.2. `app/config.py` — Configuration

```python
# Trách nhiệm:
# - Load .env
# - Định nghĩa Settings class (Pydantic BaseSettings)
# - Tất cả config tập trung 1 nơi
```

**Biến môi trường cần có:**

| Variable | Mô tả | Ví dụ |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://user:pass@localhost/ai_person` |
| `LLM_PROVIDER` | Provider: `"openai"` hoặc `"lmstudio"` | `lmstudio` |
| `LMSTUDIO_BASE_URL` | LM Studio server URL | `http://localhost:1234/v1` |
| `OPENAI_API_KEY` | API key (chỉ cần nếu provider=openai) | `sk-...` |
| `EMBEDDING_MODEL` | Tên model embedding | `text-embedding-3-small` |
| `LLM_MODEL` | Tên model LLM | `gpt-4.1-mini` |
| `EMBEDDING_DIMENSION` | Dimension vector | `1536` |
| `MAX_CONTEXT_TOKENS` | Token budget tối đa | `3000` |
| `LOG_LEVEL` | Log level | `INFO` |
| `DEBUG` | Enable Swagger UI | `false` |

### 3.3. `app/deps.py` — Dependency Injection (Provider Factory)

```python
# Trách nhiệm:
# - Factory pattern: chọn adapter dựa trên LLM_PROVIDER setting
# - get_llm_adapter() → OpenAIAdapter hoặc LMStudioAdapter
# - get_embedding_adapter() → OpenAIEmbeddingAdapter hoặc LMStudioEmbeddingAdapter
# - Lazy import: chỉ import adapter được chọn
# - Singleton caching qua @lru_cache
```

---

### 3.4. `app/api/` — HTTP Layer

#### `app/api/memory.py`

```python
# Endpoints:
# POST /api/v1/memory     → Tạo memory mới
# GET  /api/v1/memory/{id} → Lấy memory theo ID
#
# Flow:
# Request → Validate (schema) → MemoryService.save() → Response
#
# KHÔNG chứa logic save/embed
```

#### `app/api/search.py`

```python
# Endpoints:
# POST /api/v1/search → Semantic search
#
# Flow:
# Request → Validate → RetrievalService.search() → Response
#
# KHÔNG chứa logic search/ranking
```

#### `app/api/query.py`

```python
# Endpoints:
# POST /api/v1/query → Reasoning query
#
# Flow:
# Request → Validate → ReasoningService.process() → Response
#
# KHÔNG chứa logic reasoning/prompt
```

---

### 3.5. `app/schemas/` — Pydantic Models

#### `app/schemas/memory.py`

```python
# Classes:
# - MemoryCreateRequest
#     raw_text: str (required)
#     content_type: ContentTypeEnum (default: 'note')
#     metadata: dict (optional)
#     importance_score: float (optional, 0.0–1.0)
#
# - MemoryResponse
#     id: UUID
#     raw_text: str
#     content_type: str
#     created_at: datetime
#     checksum: str
```

#### `app/schemas/search.py`

```python
# Classes:
# - SearchRequest
#     query: str (required)
#     content_type: ContentTypeEnum (optional)
#     start_date: datetime (optional)
#     end_date: datetime (optional)
#     limit: int (default: 20)
#     threshold: float (default: 0.7)
#
# - SearchResponse
#     results: list[MemorySearchResult]
#     total: int
#     query: str
#     ranking_profile: str  # NEUTRAL on /search
```

#### `app/schemas/query.py`

```python
# Classes:
# - QueryRequest
#     query: str (required)
#     mode: ModeEnum (default: 'RECALL')
#     content_type: ContentTypeEnum (optional)
#
# - QueryResponse
#     response: str
#     mode: str
#     memory_used: list[UUID]
#     token_usage: dict
```

---

### 3.6. `app/memory/` — Memory Infrastructure

#### `app/memory/service.py`
MemoryService không tự động chunk document dài.
Ingestion layer phải xử lý chunking trước khi gọi save_memory().
```python
# Class: MemoryService
#
# Methods:
# - save_memory(request) → MemoryResponse
#     1. Validate input
#     2. Compute SHA256 checksum
#     3. Check duplicate (by checksum)
#     4. Insert raw_text → DB
#     5. Create embedding_job (status: pending)
#     6. Return MemoryResponse
#
# - get_memory(id) → MemoryResponse
#
# KHÔNG gọi LLM. KHÔNG embed trực tiếp.
```

#### `app/memory/repository.py`

```python
# Class: MemoryRepository
#
# Methods:
# - insert(record) → UUID
# - get_by_id(id) → MemoryRecord
# - get_by_checksum(checksum) → MemoryRecord | None
# - update_embedding(id, embedding, model) → None
#
# Tầng truy cập DB thuần. Không business logic.
```

#### `app/memory/embedding_worker.py`

```python
# Class: EmbeddingWorker
#
# Methods:
# - process_pending_jobs() → int (số jobs xử lý)
#     1. Query embedding_jobs WHERE status = 'pending'
#     2. Cho mỗi job:
#        a. Gọi embedding API
#        b. Update memory_records.embedding
#        c. Update job status → completed
#        d. Nếu fail → increment attempts, status = failed nếu max
#
# Chạy background, không block API.
```

---

### 3.7. `app/retrieval/` — Retrieval Engine

#### `app/retrieval/search.py`

```python
# Class: RetrievalService
#
# Methods:
# - search(query: str, filters) → list[RankedMemory]
#     1. Gọi EmbeddingAdapter.embed_query(query)
#     2. Execute SQL (cosine + filter + candidate pool)
#     3. Apply ranking formula
#     4. Return ranked list
#
# RetrievalService không được gọi OpenAI trực tiếp.
# Chỉ gọi EmbeddingAdapter interface.
# KHÔNG gọi LLM. Chỉ tìm.
```

#### `app/retrieval/ranking.py`

```python
# compute_final_score(similarity, created_at, importance, mode=None)
#
# /search: mode=None -> NEUTRAL profile (0.60 / 0.15 / 0.25)
# /query: mode in 5-mode system -> mode-aware weights:
# - RECALL     → semantic 0.70, recency 0.10, importance 0.20
# - SYNTHESIZE → semantic 0.60, recency 0.05, importance 0.35  (giảm recency, tăng importance)
# - REFLECT    → semantic 0.40, recency 0.30, importance 0.30  (tăng recency để thấy evolution)
# - CHALLENGE  → semantic 0.50, recency 0.10, importance 0.40  (giảm recency, focus logic)
# - EXPAND     → semantic 0.70, recency 0.05, importance 0.25  (semantic cao, recency thấp)
#
# - deduplicate_memories(memories, threshold=0.95) → list
#     Loại bỏ memory quá giống nhau (diversity guard)
#
# - apply_token_budget(memories, max_tokens) → list
#     Sort by final_score
#     Keep memories within token budget
#     Drop excess memories
#
#     V1 RULE:
#     - No runtime summarization
#     - Only use pre-computed summaries (is_summary = true)
#     - TokenGuard only trims/drops
```

---

### 3.8. `app/reasoning/` — Reasoning Layer

#### `app/reasoning/service.py`

```python
# Class: ReasoningService
#
# Methods:
# - process_query(request) → QueryResponse
#     1. Gọi RetrievalService → lấy relevant memories
#     2. Gọi ModeController → lấy mode instruction + policy
#     3. Gọi PromptBuilder → xây prompt (4 phần)
#     4. Apply TokenGuard → kiểm soát context size
#     5. Source Decision Layer:
#        - if mode == "EXPAND": external_knowledge_used = True
#        - else: external_knowledge_used = False
#     6. Gọi LLMAdapter.generate() → lấy response
#     7. Log → reasoning_logs
#     8. Return QueryResponse (response + memory_used)
#
# Đây là ORCHESTRATOR. Không trực tiếp query DB.
```

#### `app/reasoning/mode_controller.py`

```python
# Class: ModeController
#
# Methods:
# - get_instruction(mode) → str
#     Trả mode-specific instruction
#
# - get_policy(mode) → Policy
#     RECALL     → không suy diễn, không external
#     SYNTHESIZE → tổng hợp, cite memory_id, không external
#     REFLECT    → phân tích evolution, cite memory_id, không external
#     CHALLENGE  → phản biện, cite memory_id, không external
#     EXPAND     → mở rộng, cite memory_id, external bật
#
# Modes: RECALL, SYNTHESIZE, REFLECT, CHALLENGE, EXPAND
#
# VALID_MODES = frozenset(MODE_INSTRUCTIONS.keys())
# Raises InvalidModeError (422) on bad mode input
```

#### `app/reasoning/prompt_builder.py`

```python
# Class: PromptBuilder
#
# Methods:
# - build(personality, mode_instruction, memories, user_query) → str
#
# Prompt structure (4 phần KHÔNG trộn):
# 1. System Prompt (personality từ YAML)
# 2. Mode Instruction (từ ModeController)
# 3. Memory Context (retrieved records)
# 4. User Query (câu hỏi thực tế)
```

---

### 3.9. `app/llm/` — LLM Abstraction

#### `app/llm/adapter.py` + `app/llm/embedding_adapter.py`

```python
# Abstract Classes:
# - LLMAdapter: generate(prompt, config) → LLMResponse, count_tokens(text) → int
# - EmbeddingAdapter: embed(text) → list[float], embed_batch(texts) → list[list[float]]
#
# LLM adapter KHÔNG biết gì về memory structure.
# Chỉ nhận prompt → trả response.
```

#### `app/llm/openai_adapter.py` + `app/llm/openai_embedding_adapter.py`

```python
# Class: OpenAIAdapter(LLMAdapter), OpenAIEmbeddingAdapter(EmbeddingAdapter)
# Dùng OpenAI API qua openai SDK
# Cần OPENAI_API_KEY
```

#### `app/llm/lmstudio_adapter.py` + `app/llm/lmstudio_embedding_adapter.py`

```python
# Class: LMStudioAdapter(LLMAdapter), LMStudioEmbeddingAdapter(EmbeddingAdapter)
# Dùng LM Studio local model qua OpenAI-compatible API
# base_url = LMSTUDIO_BASE_URL (default: http://localhost:1234/v1)
# api_key = "lm-studio" (placeholder, LM Studio không cần key thật)
# Token counting: cl100k_base (approximate)
# Xử lý usage=None edge case
```

---

### 3.10. `app/core/` — Core Policies

#### `app/core/personality.py`

```python
# Functions:
# - load_personality(path) → dict
#     Load YAML personality file
#     Ví dụ: name, tone, rules, constraints
```

#### `app/core/prompts.py`

```python
# Constants & Templates:
# - MODE_INSTRUCTIONS: dict[mode → instruction_text]
#     Keys: RECALL, SYNTHESIZE, REFLECT, CHALLENGE, EXPAND
# - MODE_POLICIES: dict[mode → ModePolicy]
#     ModePolicy(can_use_external_knowledge, must_cite_memory_id, can_speculate, description)
#     Keys: RECALL, SYNTHESIZE, REFLECT, CHALLENGE, EXPAND
#     EXPAND.can_use_external_knowledge = True (duy nhất)
#     Tất cả modes khác: can_use_external_knowledge = False
```

#### `app/core/token_guard.py`

```python
# Class: TokenGuard
#
# Methods:
# - check_budget(memories, max_tokens) → list[Memory]
#     1. Sort theo final_score
#     2. Cộng dồn token
#     3. Stop khi vượt budget
#     4. Return memories trong budget
```

---

### 3.11. `app/db/` — Database Infrastructure

#### `app/db/session.py`

```python
# Functions:
# - get_async_session() → AsyncSession
#     SQLAlchemy async session factory
#     Dùng với FastAPI Depends()
```

#### `app/db/models.py`

```python
# ORM Models (SQLAlchemy 2.0):
# - MemoryRecord
# - EmbeddingJob
# - ReasoningLog
#
# Mapping 1:1 với DB tables
```

---

### 3.12. `app/exceptions/handlers.py`

```python
# Exception Classes:
# - MemoryNotFoundError
# - DuplicateMemoryError
# - EmbeddingFailedError
# - LLMTimeoutError
# - RetrievalError
# - TokenBudgetExceededError
#
# Handler:
# - register_exception_handlers(app) → None
#     Gắn FastAPI exception handlers
#     Chuẩn hóa error response format
#     Không leak stacktrace
```

---

### 3.13. `app/logging/logger.py`

```python
# Functions:
# - setup_logger(name, level) → Logger
# - get_correlation_id() → str
#
# Features:
# - Structured logging (JSON format)
# - Correlation ID cho mỗi request
# - Log retrieval scores
# - Log memory_ids được sử dụng
# - Log token usage
```

---

### 3.14. `workers/run_embedding.py`

```python
# Entry point cho background embedding worker
#
# Usage:
#   python -m workers.run_embedding
#
# Logic:
#   while True:
#       worker.process_pending_jobs()
#       sleep(interval)
```

---

### 3.15. `personalities/default.yaml`

```yaml
# Ví dụ:
name: "AI Person"
tone: "direct, honest, analytical"
language: "vi"
rules:
  - "Không bịa thông tin"
  - "Cite memory khi trả lời"
  - "Nói 'không biết' khi không có memory liên quan"
constraints:
  - "Không sửa memory"
  - "Không tự thêm memory"
```

---

## 4. Dependency Flow (Import Graph)

```
main.py
  ├── api/memory.py     → schemas/memory.py, memory/service.py
  ├── api/search.py     → schemas/search.py, retrieval/search.py
  ├── api/query.py      → schemas/query.py, reasoning/service.py
  └── deps.py           → config.py, llm/adapter.py (factory switch)

deps.py (provider factory)
  ├── LLM_PROVIDER=openai   → llm/openai_adapter.py, llm/openai_embedding_adapter.py
  └── LLM_PROVIDER=lmstudio → llm/lmstudio_adapter.py, llm/lmstudio_embedding_adapter.py

memory/service.py       → memory/repository.py, db/models.py
memory/repository.py    → db/session.py, db/models.py
memory/embedding_worker → llm/embedding_adapter.py (via deps.py)

retrieval/search.py     → db/session.py, retrieval/ranking.py
retrieval/ranking.py    → core/token_guard.py

reasoning/service.py    → retrieval/search.py, reasoning/mode_controller.py,
                          reasoning/prompt_builder.py, llm/adapter.py,
                          core/token_guard.py, logging/logger.py

llm/openai_adapter.py       → llm/adapter.py (inherits)
llm/lmstudio_adapter.py     → llm/adapter.py (inherits)
llm/openai_embedding_adapter.py   → llm/embedding_adapter.py (inherits)
llm/lmstudio_embedding_adapter.py → llm/embedding_adapter.py (inherits)
```

**Quy tắc import:**
- Layer dưới KHÔNG import layer trên
- `api/` → chỉ import `schemas/` và service layer
- `memory/` → KHÔNG import `llm/` hoặc `reasoning/`
- `llm/` → KHÔNG import bất kỳ layer nào khác
- `db/` → KHÔNG import business logic
- `deps.py` → lazy import adapter dựa trên provider config

---

## 5. Những Thứ KHÔNG Thêm

| Không Thêm | Lý Do |
|---|---|
| `services/` folder riêng | Đã có `memory/service.py`, `reasoning/service.py` |
| `helpers/` lung tung | Logic phải nằm đúng layer |
| `constants.py` lộn xộn | Config tập trung ở `config.py` |
| `utils/` chung chung | Mỗi utility phải nằm trong layer phù hợp |
| Nhiều file `__init__.py` phức tạp | Giữ đơn giản, explicit import |

---

## 6. API Design V1

### 6.1. Endpoints

| Method | Path | Mô Tả | Request Body | Response |
|---|---|---|---|---|
| `POST` | `/api/v1/memory` | Tạo memory mới | `MemoryCreateRequest` | `MemoryResponse` |
| `GET` | `/api/v1/memory/{id}` | Lấy memory theo ID | — | `MemoryResponse` |
| `POST` | `/api/v1/search` | Semantic search | `SearchRequest` | `SearchResponse` |
| `POST` | `/api/v1/query` | Reasoning query | `QueryRequest` | `QueryResponse` |

### 6.2. Error Response Format

```json
{
    "error": {
        "code": "MEMORY_NOT_FOUND",
        "message": "Memory with ID xxx not found",
        "correlation_id": "abc-123"
    }
}
```

---

## 7. Tài Liệu Liên Quan

| Tài liệu | Mô tả |
|---|---|
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | Kiến trúc tổng thể, triết lý, flows |
| [DATA_DESIGN.md](DATA_DESIGN.md) | DB schema, index, retrieval SQL |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Roadmap, checklist triển khai |
