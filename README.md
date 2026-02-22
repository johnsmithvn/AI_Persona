# AI Person — Bộ Não Thứ 2

> **Personal Memory-First AI System** — Version 0.3.0

A production-grade personal AI that stores your thinking history and reasons over it. Not a chatbot. Not a RAG demo. A long-term memory infrastructure designed to live alongside you for 5–10 years.

---

## 🏗 Architecture

```
API Layer (FastAPI)
    ↓
Memory Infrastructure   →   Retrieval Engine   →   Reasoning Layer
(save, checksum, embed)     (semantic search)       (mode + prompt + LLM)
    ↓                              ↓                       ↓
              PostgreSQL 16 + pgvector (HNSW)
```

**5 modes:** `RECALL` (fetch verbatim) · `SYNTHESIZE` (combine knowledge) · `REFLECT` (analyze evolution) · `CHALLENGE` (find contradictions) · `EXPAND` (supplement with external knowledge)

**LLM Provider:** OpenAI API hoặc **LM Studio** (local model) — chuyển đổi qua 1 env var.

---

## ⚡ Quick Start

### 1. Prerequisites

- Python 3.11+
- Docker + Docker Compose
- **Một trong hai:**
  - OpenAI API key, hoặc
  - [LM Studio](https://lmstudio.ai/) chạy local model

### 2. Setup

```bash
# Clone and enter
cd AI_Person

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate      # Windows
# source venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env — xem hướng dẫn bên dưới
```

### 3. Start Database

```bash
docker compose up -d
```

### 4. Run Migrations

```bash
alembic upgrade head
```

### 5. Start API Server

```bash
uvicorn app.main:app --reload --port 8000
```

### 6. Start Embedding Worker (separate terminal)

```bash
python -m workers.run_embedding
```

API docs: `http://localhost:8000/docs` (chỉ khi `DEBUG=true`)

---

## ⚙️ Cấu Hình LLM Provider

Hệ thống hỗ trợ 2 provider, chuyển đổi qua biến `LLM_PROVIDER` trong `.env`.

### Option A: LM Studio (Local — Recommended cho dev)

```env
LLM_PROVIDER=lmstudio
LMSTUDIO_BASE_URL=http://localhost:1234/v1

# Đổi tên model cho khớp với model bạn load trong LM Studio
LLM_MODEL=your-chat-model-name
EMBEDDING_MODEL=your-embedding-model-name
EMBEDDING_DIMENSION=768                    # Đổi theo dimension model embedding
```

**Cách setup LM Studio:**

1. Mở LM Studio → load **2 models**:
   - 1 **chat model** (vd: `llama-3.2-3b-instruct`, `qwen2.5-7b-instruct`)
   - 1 **embedding model** (vd: `nomic-embed-text-v1.5`, `bge-small-en-v1.5`)
2. Start server trong LM Studio (default port: `1234`)
3. Verify: `curl http://localhost:1234/v1/models` — phải thấy danh sách models
4. Copy tên model chính xác vào `LLM_MODEL` và `EMBEDDING_MODEL` trong `.env`

> ⚠️ **EMBEDDING_DIMENSION** phải match với model bạn dùng:
> - `nomic-embed-text-v1.5` → `768`
> - `bge-small-en-v1.5` → `384`
> - `text-embedding-3-small` (OpenAI) → `1536`

### Option B: OpenAI API

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-real-key-here

LLM_MODEL=gpt-4.1-mini
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
```

---

## ⚙️ Tất Cả Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `LLM_PROVIDER` | `openai` | `"openai"` hoặc `"lmstudio"` |
| `LMSTUDIO_BASE_URL` | `http://localhost:1234/v1` | LM Studio server URL |
| `OPENAI_API_KEY` | *(required nếu openai)* | OpenAI API key |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Tên embedding model |
| `EMBEDDING_DIMENSION` | `1536` | Vector dimension |
| `LLM_MODEL` | `gpt-4.1-mini` | Tên chat/LLM model |
| `MAX_CONTEXT_TOKENS` | `3000` | Token budget cho memory context |
| `LOG_LEVEL` | `INFO` | Log level |
| `DEBUG` | `false` | Enable Swagger UI + debug mode |
| `EMBEDDING_WORKER_INTERVAL_SECONDS` | `5` | Worker polling interval |
| `EMBEDDING_WORKER_BATCH_SIZE` | `10` | Batch size cho embedding worker |

---

## 🔌 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/memory` | Save a new memory |
| `GET` | `/api/v1/memory/{id}` | Get memory by ID |
| `PATCH` | `/api/v1/memory/{id}/archive` | Soft-archive (selective forgetting) |
| `POST` | `/api/v1/search` | Semantic search |
| `POST` | `/api/v1/query` | Reasoning query (5 modes) |
| `GET` | `/health` | Health check |

### CLI — Add Memory (Interactive)

```powershell
.\ai add
```

Interactive flow:
1. Nhập nội dung (multiline, kết thúc bằng `::end`)
2. Chọn `content_type` (6 loại)
3. Flow người (person_name suggestion)
4. Chọn tags (22 tags cố định)
5. Xác nhận → lưu qua `MemoryService`

### Chat UI — React (Vite)

```powershell
.\ai chat
```

Mở browser tại `http://localhost:5173`. Giao diện gồm 3 tab:
- **Chat** — Trò chuyện với AI, chọn 1 trong 5 mode (RECALL, SYNTHESIZE, REFLECT, CHALLENGE, EXPAND)
- **Memory** — Thêm memory mới (form) + tra cứu theo ID
- **Search** — Semantic search với filter (content_type, threshold, limit)

### Save Memory

```bash
curl -X POST http://localhost:8000/api/v1/memory \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "Hôm nay tôi nhận ra rằng momentum trong ML không chỉ là kỹ thuật mà là tư duy.",
    "content_type": "reflection",
    "importance_score": 0.8,
    "metadata": {
      "tags": ["ai", "deep"],
      "source": "api"
    }
  }'
```

### Search

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "suy nghĩ về machine learning",
    "limit": 10
  }'
```

### Reasoning Query (5 modes)

```bash
# RECALL — trả nguyên văn
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Tao từng viết gì về LoRA?", "mode": "RECALL"}'

# SYNTHESIZE — tổng hợp từ nhiều memory
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Tổng hợp hiểu biết về fine-tuning", "mode": "SYNTHESIZE"}'

# REFLECT — phân tích evolution
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Tư duy của tao về AI thay đổi thế nào?", "mode": "REFLECT"}'

# CHALLENGE — phản biện
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Tìm mâu thuẫn trong suy nghĩ về ML của tao", "mode": "CHALLENGE"}'

# EXPAND — bổ sung external knowledge
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "So sánh hiểu biết của tao với industry best practice", "mode": "EXPAND"}'
```

---

## 🗂 Project Structure

```
AI_Person/
├── app/
│   ├── api/              # HTTP endpoints (no business logic)
│   ├── core/             # Personality, prompts, token guard
│   ├── db/               # SQLAlchemy models + Alembic migrations
│   ├── exceptions/       # Custom exception classes + handlers
│   ├── llm/              # LLM + Embedding adapters (OpenAI + LM Studio)
│   ├── logging/          # Structured JSON logger
│   ├── memory/           # Save + checksum + embedding job creation
│   ├── reasoning/        # Mode controller + prompt builder + orchestrator
│   ├── retrieval/        # Semantic search + ranking
│   ├── schemas/          # Pydantic request/response models
│   ├── config.py         # Settings (all env vars)
│   ├── deps.py           # DI factory (provider switching)
│   └── main.py           # FastAPI app entry point
├── cli/                  # Interactive CLI ingestion
│   ├── add_memory.py     # `ai add` — main interactive flow
│   ├── registry.py       # Content type, tag, type menus
│   └── person_helpers.py # Person name suggest + normalize
├── workers/
│   └── run_embedding.py  # Background embedding CLI
├── personalities/
│   └── default.yaml      # AI personality config (5-mode hints)
├── docs/                 # Architecture documentation
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## 🌿 Git Workflow

```
main                    ← production-ready
├── develop             ← integration
│   ├── feat/lmstudio-adapter
│   ├── fix/audit-gaps
│   └── feature/phase1–5
```

---

## 📚 Documentation

| Doc | Description |
|---|---|
| [MEMORY_CONTRACT.md](docs/MEMORY_CONTRACT.md) | **Memory Contract V1** — data schema, tag registry, examples |
| [PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) | Architecture philosophy + data flow |
| [DATA_DESIGN.md](docs/DATA_DESIGN.md) | DB schema, indexes, retrieval SQL |
| [CODEBASE_STRUCTURE.md](docs/CODEBASE_STRUCTURE.md) | File responsibilities |
| [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | Phase roadmap + checklists |
| [API_DOCS.md](docs/API_DOCS.md) | Full API reference (endpoints, schemas, errors, cURL) |

---

## 📦 Version

Current: **v0.3.0** — Memory Contract V1 + Reasoning Layer safety fixes + LM Studio support
