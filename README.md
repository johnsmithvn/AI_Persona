# AI Person — Bộ Não Thứ 2

> **Personal Memory-First AI System** — Version 0.1.0

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

**3 modes:** `RECALL` (fetch what I wrote) · `REFLECT` (synthesize patterns) · `CHALLENGE` (find contradictions)

---

## ⚡ Quick Start

### 1. Prerequisites

- Python 3.11+
- Docker + Docker Compose
- OpenAI API key

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
# Edit .env: set OPENAI_API_KEY
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

API docs available at: `http://localhost:8000/docs` (only when `DEBUG=true`)

---

## 🔌 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/memory` | Save a new memory |
| `GET` | `/api/v1/memory/{id}` | Get memory by ID |
| `PATCH` | `/api/v1/memory/{id}/archive` | Soft-archive (selective forgetting) |
| `POST` | `/api/v1/search` | Semantic search |
| `POST` | `/api/v1/query` | Reasoning query |
| `GET` | `/health` | Health check |

### Save Memory

```bash
curl -X POST http://localhost:8000/api/v1/memory \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "Hôm nay tôi nhận ra rằng momentum trong ML không chỉ là kỹ thuật mà là tư duy.",
    "content_type": "reflection",
    "importance_score": 0.8
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

### Reasoning Query

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Tư duy của tôi về AI thay đổi thế nào theo thời gian?",
    "mode": "REFLECT"
  }'
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
│   ├── llm/              # LLM + Embedding adapters (swappable)
│   ├── logging/          # Structured JSON logger
│   ├── memory/           # Save + checksum + embedding job creation
│   ├── reasoning/        # Mode controller + prompt builder + orchestrator
│   ├── retrieval/        # Semantic search + ranking
│   ├── schemas/          # Pydantic request/response models
│   ├── config.py         # Settings (all env vars)
│   ├── deps.py           # Dependency injection
│   └── main.py           # FastAPI app entry point
├── workers/
│   └── run_embedding.py  # Background embedding CLI
├── personalities/
│   └── default.yaml      # AI personality config
├── docs/                 # Architecture documentation
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `OPENAI_API_KEY` | *(required)* | OpenAI API key |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model name |
| `LLM_MODEL` | `gpt-4.1-mini` | LLM model name |
| `MAX_CONTEXT_TOKENS` | `3000` | Token budget for memory context |
| `LOG_LEVEL` | `INFO` | Log level |
| `DEBUG` | `false` | Enable debug mode + API docs |
| `EMBEDDING_WORKER_INTERVAL_SECONDS` | `5` | Worker polling interval |

---

## 🌿 Git Workflow

```
main                    ← production-ready
├── develop             ← integration
│   ├── feature/phase1-foundation
│   ├── feature/phase2-memory
│   ├── feature/phase3-retrieval
│   ├── feature/phase4-reasoning
│   └── feature/phase5-polish
```

---

## 📚 Documentation

| Doc | Description |
|---|---|
| [PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) | Architecture philosophy + data flow |
| [DATA_DESIGN.md](docs/DATA_DESIGN.md) | DB schema, indexes, retrieval SQL |
| [CODEBASE_STRUCTURE.md](docs/CODEBASE_STRUCTURE.md) | File responsibilities |
| [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | Phase roadmap + checklists |

---

## 📦 Version

Current: **v0.1.0** — Phase 1 Foundation (Database + Memory Infrastructure)
