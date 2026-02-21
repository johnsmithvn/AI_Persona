# PROJECT STRUCTURE — AI Person (Bộ Não Thứ 2)

> **Project:** AI Person — Personal Memory-First AI System  
> **Version:** V1 (Pre-release)  
> **Last Updated:** 2026-02-20  
> **Author:** tunghnhn9x@gmail.com  
> **Status:** Design Finalized → Ready for Implementation

---

## 1. Tổng Quan Dự Án

### 1.1. Bản Chất

Đây **không phải** chatbot. Không phải app ghi chú. Không phải RAG demo.

Đây là:

> **Memory Infrastructure + Reasoning Layer**  
> được thiết kế để sống lâu dài cùng một con người.

Hệ thống lưu trữ 100% nguyên văn mọi dữ liệu người dùng nạp vào, sau đó cung cấp khả năng truy xuất ngữ nghĩa (semantic search) và suy luận (reasoning) dựa trên chính lịch sử tư duy của người dùng.

### 1.2. Định Vị

| Thuộc tính | Giá trị |
|---|---|
| Loại hệ thống | Personal AI với long-term memory |
| Triết lý | Memory-first, không phải prompt-engineered chatbot |
| Đối tượng | Cá nhân (internal-first, local-first) |
| Thời gian sống thiết kế | 5–10 năm |
| Kiến trúc | Monolith 3 tầng, API-first |

---

## 2. Mục Tiêu Cốt Lõi (9 Nguyên Tắc Bất Biến)

Toàn bộ quyết định kỹ thuật phải tuân theo 9 nguyên tắc sau. Nếu lệch khỏi bất kỳ điều nào → sai triết lý thiết kế.

| # | Nguyên Tắc | Giải Thích |
|---|---|---|
| 1 | Lưu nguyên văn 100% | `raw_text` không bao giờ bị chỉnh sửa sau khi insert |
| 2 | LLM không được sửa memory | LLM chỉ đọc, không viết ngược vào memory |
| 3 | Có semantic search | Tìm kiếm theo ngữ nghĩa, không chỉ keyword |
| 4 | Có filter theo thời gian | Hỗ trợ query theo khoảng thời gian |
| 5 | Reasoning dựa trên lịch sử tư duy | AI phân tích dựa trên memory thật, không bịa |
| 6 | Có khả năng phản biện | CHALLENGE mode — chỉ ra mâu thuẫn, logic yếu |
| 7 | Có thể nói "không biết" | Không hallucinate khi không có memory liên quan |
| 8 | Backup — không mất dữ liệu | Checksum, integrity verification, backup strategy |
| 9 | Sống lâu dài (5–10 năm) | Không lock-in, không phụ thuộc 1 provider |

### 2.1. Memory-First Intelligence Principle

> Hệ thống này **không phải chatbot biết nhớ**.
> Nó là **memory infrastructure có khả năng reasoning**.

#### Intelligence Hierarchy (Thứ tự ưu tiên tuyệt đối)

```
1. MEMORY        — nguồn sự thật duy nhất (single source of truth)
2. RETRIEVAL     — trái tim hệ thống (quyết định chất lượng output)
3. REASONING     — suy luận DỰA TRÊN memory đã retrieve
4. EXTERNAL      — chỉ được dùng khi mode = EXPAND
```

#### Default Behavior

- **Mặc định:** memory-only. LLM không được tự ý dùng kiến thức ngoài
- **External chỉ bật khi:** `mode == "EXPAND"` — mode duy nhất cho phép
- **`external_knowledge_used` phải log** trong `reasoning_logs` — bắt buộc

#### Mode = Permission System (5-Mode)

| Mode | Mục Đích | Memory | External | Suy Diễn |
|---|---|---|---|---|
| RECALL | Trả nguyên văn | ✅ | ❌ | ❌ |
| SYNTHESIZE | Tổng hợp kiến thức đã ghi | ✅ | ❌ | ✅ (tổng hợp) |
| REFLECT | Phân tích evolution tư duy | ✅ | ❌ | ✅ (evolution) |
| CHALLENGE | Phản biện dựa trên memory | ✅ | ❌ | ✅ (phản biện) |
| EXPAND | Mở rộng kiến thức khi cần | ✅ | ✅ | ✅ (external) |

Mode không tạo ra AI khác nhau. Mode là **cấu hình quyền hạn** cho cùng một LLM.

#### Retrieval là Trái Tim

- Retrieval quyết định **50%** chất lượng output
- Ranking formula (semantic × recency × importance) là logic cốt lõi
- Diversity guard ngăn top-K bị dominate bởi memory giống nhau
- TokenGuard đảm bảo LLM không bị overwhelm

---

## 3. Kiến Trúc Tổng Thể

### 3.1. Triết Lý Kiến Trúc

- **Không microservice** — 1 monolith duy nhất
- **Không multi-tenant** — chỉ phục vụ 1 người
- **3 tầng logic** — tách rõ trách nhiệm
- **Adapter pattern** — LLM/Embedding có thể swap bất kỳ lúc nào

### 3.2. Sơ Đồ 3 Tầng

```
<!-- ┌─────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI)                     │
│              HTTP endpoints / Request validation             │
└──────────────┬──────────────────────────┬───────────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────┐    ┌──────────────────────────────────┐
│   MEMORY              │    │   REASONING LAYER                │
│   INFRASTRUCTURE      │    │                                  │
│                       │    │  ┌────────────────────────────┐  │
│  • Save raw_text      │◄───│  │  Retrieval Engine          │  │
│  • Embed async        │    │  │  (semantic search + filter) │  │
│  • Checksum           │    │  └────────────┬───────────────┘  │
│  • Insert DB          │    │               │                  │
│                       │    │  ┌────────────▼───────────────┐  │
│                       │    │  │  Mode Controller           │  │
│                       │    │  │  (5-Mode Permission)       │  │
│                       │    │  └────────────┬───────────────┘  │
│                       │    │               │                  │
│                       │    │  ┌────────────▼───────────────┐  │
│                       │    │  │  Prompt Builder             │  │
│                       │    │  └────────────┬───────────────┘  │
│                       │    │               │                  │
│                       │    │  ┌────────────▼───────────────┐  │
│                       │    │  │  LLM Adapter               │  │
│                       │    │  │  (OpenAI / Local / Gemini)  │  │
│                       │    │  └────────────────────────────┘  │
└──────────────────────┘    └──────────────────────────────────┘
               │                          │
               ▼                          ▼
┌─────────────────────────────────────────────────────────────┐
│              PostgreSQL + pgvector                           │
│         memory_records | embedding_jobs | reasoning_logs     │
└─────────────────────────────────────────────────────────────┘ -->


┌─────────────────────────────────────────────┐
│                 API LAYER                   │
└─────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│          MEMORY INFRASTRUCTURE              │
│   • Save raw_text                           │
│   • Checksum                                │
│   • Async embedding                         │
└─────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│              RETRIEVAL ENGINE               │
│   • Semantic search (cosine)                │
│   • Filters (time, type, metadata)          │
│   • Ranking formula                         │
│   • embedding_model isolation               │
└─────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│              REASONING LAYER                │
│   • Mode Controller                         │
│   • Prompt Builder                          │
│   • Token Guard                             │
│   • LLM Adapter                             │
└─────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│        PostgreSQL + pgvector                │
│   memory_records | embedding_jobs | logs    │
└─────────────────────────────────────────────┘
```

### 3.3. Tỷ Trọng Thiết Kế

| Tầng | % Hệ Thống | Lý Do |
|---|---|---|
| Memory Infrastructure | 50% | Đây là lõi — nếu memory yếu, toàn bộ reasoning vô nghĩa |
| Retrieval Engine | 25% | Tìm đúng memory quyết định chất lượng output |
| Reasoning Layer | 25% | LLM chỉ là bộ não — cần memory + mode để hoạt động |

---

## 4. Ba Tầng Chi Tiết

### 4.1. Tầng 1 — Memory Infrastructure

**Trách nhiệm:** Lưu trữ, embed, đảm bảo toàn vẹn dữ liệu.

**Nguyên tắc bất biến:**
- Không rewrite `raw_text`
- Không để LLM sửa memory
- Không phụ thuộc embedding model
- Embedding có thể thay, nhưng `raw_text` là vĩnh viễn
- **Memory phải chắc hơn AI**

**MemoryRecord chuẩn hóa:**

Mọi dữ liệu đầu vào (text, note, conversation, PDF, OCR, transcript...) đều quy về 1 cấu trúc duy nhất:

```
MemoryRecord {
    id: UUID
    raw_text: TEXT (bất biến)
    content_type: ENUM
    source_type: ENUM
    embedding: vector(1536)
    embedding_model: VARCHAR
    checksum: SHA256(raw_text)
    importance_score: FLOAT
    metadata: JSONB
    is_archived: BOOLEAN
    exclude_from_retrieval: BOOLEAN
    created_at: TIMESTAMPTZ
    is_summary: BOOLEAN (default false)
}
```

**Pipeline lưu trữ (2 giai đoạn — KHÔNG embed trực tiếp):**

```
Giai đoạn 1: Insert raw_text → DB (đồng bộ, nhanh)
Giai đoạn 2: Embedding worker xử lý async → update embedding
```

Lý do tách:
- Embedding API có thể timeout
- Cần retry logic
- Không block request của user

### 4.2. Tầng 2 — Retrieval Engine
- Retrieval Engine là tầng độc lập.
- Nó được phép query DB trực tiếp và không thuộc Reasoning Layer.

**Trách nhiệm:** Tìm đúng memory. Chỉ tìm. Không suy luận.

**Khả năng V1:**
- Semantic search (cosine similarity qua pgvector)
- Time filter (khoảng thời gian)
- Content type filter
- Metadata filter (JSONB query)
- Ranking formula (không chỉ similarity)
- Similarity threshold (không trả memory kém liên quan)

**Chiến lược retrieval: Recall cao (bao phủ rộng)**

| Tham số | Giá trị |
|---|---|
| Cosine distance threshold | < 0.7 |
| Candidate pool | 400–600 |
| Final return | 20–30 records |
| Token trimming | linh hoạt (hybrid context) |

Lý do chọn recall cao:
- Phù hợp cho REFLECT, CHALLENGE, TEMPORAL_COMPARE
- Không bỏ sót insight quan trọng
- Cần diversity guard + token guard để tránh noise

### 4.3. Tầng 3 — Reasoning Layer

**Trách nhiệm:** Suy luận dựa trên memory + mode + LLM.

**Thành phần:**

| Component | Vai Trò |
|---|---|
| Mode Controller | Chọn hành vi suy luận (user quyết định) |
| Prompt Builder | Xây prompt từ 4 phần tách biệt |
| LLM Adapter | Gọi model (adapter pattern, swap được) |
| Policy Guard | Ràng buộc hành vi theo mode |

---

## 5. Mode System (5-Mode)

### 5.1. Danh Sách Mode

| Mode | Mục Đích | Hành Vi | V1 |
|---|---|---|---|
| **RECALL** | Truy xuất nguyên văn | Trả đúng memory liên quan, không suy diễn | ✅ |
| **SYNTHESIZE** | Tổng hợp kiến thức | Gom nhiều memory → structured summary | ✅ |
| **REFLECT** | Phân tích evolution tư duy | Nhận diện pattern thay đổi theo thời gian | ✅ |
| **CHALLENGE** | Phản biện người dùng | Tìm mâu thuẫn, chỉ ra logic yếu | ✅ |
| **EXPAND** | Mở rộng kiến thức | Memory + external knowledge kết hợp | ✅ |

> ⚠️ Mode V2 cũ (ANALYZE, TEMPORAL_COMPARE) đã retired. Chức năng được merge vào SYNTHESIZE và REFLECT.

#### SYNTHESIZE vs REFLECT

| | SYNTHESIZE | REFLECT |
|---|---|---|
| Input | "Tổng hợp kiến thức về X" | "Tư duy của tao về X thay đổi thế nào?" |
| Focus | **Nội dung** — gom knowledge | **Quá trình** — phát hiện evolution |
| Output | Summary, structured knowledge | Timeline, pattern, contradiction |

## Epistemic Boundary Enforcement

Reasoning layer phải phân biệt rõ: **memory-based reasoning** vs **external knowledge reasoning**.

### Rule V1.1 (5-Mode — Single Source of Truth)

External knowledge chỉ được phép trong **EXPAND mode**:

```python
# Pseudocode — đây là rule duy nhất. Không có rule nào khác.
if mode == "EXPAND":
    external_knowledge_used = True
else:
    external_knowledge_used = False  # RECALL, SYNTHESIZE, REFLECT, CHALLENGE luôn bị khóa
```

Clean. Không conditional. Mode = permission.

### Quy Tắc Bắt Buộc

Nếu `external_knowledge_used = True`, LLM PHẢI:
- Ghi rõ `[External knowledge used]` trong response
- `external_knowledge_used = true` được set trong response và reasoning_logs

### Tại Sao Mode-Based (Không Phải Token-Threshold)

- Token-threshold V1 gắn vào REFLECT → phức tạp, conditional
- Mode-based: clean permission → EXPAND = external ON, others = OFF
- User chủ động chọn khi nào muốn external knowledge, không phải hệ thống tự quyết

> ⚠️ Rule token-threshold (MIN_CONTEXT_TOKENS = 800) cho REFLECT đã retired.
> Chuẩn duy nhất: **mode == EXPAND**.

### 5.2. Triết Lý Mode

> Mode **không phải** hệ thống khác nhau.  
> Mode là **cùng 1 LLM** với **instruction khác nhau**.

```python
# Pseudo code
prompt = build_prompt(
    system_prompt=load_personality(),
    mode_instruction=modes[selected_mode],
    memory_context=retrieved_memories,
    user_query=query
)
response = llm_adapter.generate(prompt)
```

### 5.3. Policy Guard (Ràng Buộc Theo Mode)

| Mode | External Knowledge | Cite Memory | Speculate |
|---|---|---|---|
| RECALL | ❌ Không bao giờ | Không bắt buộc | ❌ Không |
| SYNTHESIZE | ❌ Không bao giờ | ✅ Bắt buộc | ✅ Có thể (tổng hợp) |
| REFLECT | ❌ Không bao giờ | ✅ Bắt buộc | ✅ Có thể (evolution) |
| CHALLENGE | ❌ Không bao giờ | ✅ Bắt buộc | ❌ Không |
| EXPAND | ✅ Luôn bật | ✅ Bắt buộc | ✅ Có thể |

Nếu không có policy guard → mode chỉ là prompt decoration.

### 5.4. Prompt Builder — 4 Phần Tách Biệt

```
┌─────────────────────┐
│ 1. System Prompt     │  ← Personality (YAML)
├─────────────────────┤
│ 2. Mode Instruction  │  ← RECALL / REFLECT / CHALLENGE
├─────────────────────┤
│ 3. Memory Context    │  ← Retrieved records
├─────────────────────┤
│ 4. User Query        │  ← Câu hỏi thực tế
└─────────────────────┘
```

**KHÔNG được trộn** personality vào mode → hành vi sẽ loạn.

---

## 6. Data Flow

### 6.1. Flow A — Save Memory

```
User
  │
  ▼
API Layer (POST /memory)
  │
  ▼
MemoryService.save_memory()
  ├── Validate input (Pydantic schema)
  ├── Compute checksum (SHA256)
  ├── Insert raw_text → DB (sync)
  └── Create embedding_job (status: pending)
        │
        ▼
  Embedding Worker (async/background)
  ├── Gọi embedding API
  ├── Update memory_records.embedding
  └── Update embedding_jobs.status → completed
```

### 6.2. Flow B — Search Memory

```
User
  │
  ▼
API Layer (POST /search)
  │
  ▼
RetrievalService.search()
  ├── Embed query (active embedding_model)
  ├── Execute SQL (cosine + filter + embedding_model match)
  ├── Apply ranking formula
  └── Return ranked memory list
```

### 6.3. Flow C — Reasoning Query

```
User
  │
  ▼
API Layer (POST /query)
  │
  ▼
ReasoningService.process_query()
  ├── Gọi RetrievalService → lấy memory
  ├── ModeController → chọn instruction
  ├── PromptBuilder → xây prompt (4 phần)
  ├── Token Guard → kiểm soát context size
  ├── LLMAdapter.generate() → gọi model
  └── Return:
        ├── response (câu trả lời)
        ├── memory_used (list memory_ids)
        ├── external_knowledge_used (bool)
        └── Log → reasoning_logs
```

---

## 7. Technology Stack

### 7.1. Stack V1

| Layer | Technology | Lý Do |
|---|---|---|
| **API Framework** | FastAPI + Uvicorn | Async native, typed, Pydantic, phù hợp AI service |
| **Database** | PostgreSQL 16 | Stable, transaction safe, backup chuẩn |
| **Vector Search** | pgvector (HNSW index) | Không lock-in, đủ mạnh cho semantic search |
| **ORM** | SQLAlchemy 2.0 (async) | Typed, mature, tách repository dễ |
| **Embedding** | OpenAI text-embedding-3-small | Rẻ, đủ tốt cho V1 |
| **LLM** | GPT-4.1-mini (qua adapter) | V1 nhanh, sau swap được |
| **Config** | python-dotenv | Đơn giản, đủ dùng |
| **Personality** | YAML files | Dễ edit, version control được |
| **Migration** | Alembic | Chuẩn production cho SQLAlchemy |
| **Container** | Docker (chỉ DB) | PostgreSQL + pgvector, app chạy local |

### 7.2. Dependencies (requirements.txt V1)

```
fastapi
uvicorn
sqlalchemy[asyncio]
asyncpg
pgvector
openai
python-dotenv
pydantic
alembic
pyyaml
tiktoken
```

### 7.3. Công Nghệ KHÔNG Dùng (Và Lý Do)

| Không Dùng | Lý Do |
|---|---|
| Django / Flask | Overkill / thiếu async native |
| Chroma | Chỉ prototype, không production |
| Pinecone | Lock-in, tốn tiền |
| MongoDB | Không phù hợp structured memory |
| Microservice | Quá sớm, chưa cần |
| Kubernetes | Chưa cần cho 1 user |
| Multi-tenant | Thiết kế cho cá nhân |

### 7.4. Scale Sau Này (Khi > 1M records)

- Redis → cache retrieval results
- Celery / BackgroundTasks → embedding async
- Prometheus → monitoring
- Partition theo tháng
- Reindex embedding mỗi 6 tháng

---

## 8. Triết Lý Thiết Kế Cốt Lõi

### 8.1. Memory = Trí Nhớ | Mode = Cách Cư Xử | LLM = Bộ Não

> Base model chỉ là cái não.  
> AI core là cách nó cư xử.

**3 thứ này KHÔNG được nhầm lẫn.**

Nếu memory yếu → toàn bộ reasoning vô nghĩa.  
Nếu mode lỏng → AI thành ChatGPT clone.  
Nếu LLM được sửa memory → hệ thống mất triết lý.

### 8.2. Điều Nguy Hiểm Nhất

Không phải complexity.  
Mà là **trộn vai trò**.

- Memory layer KHÔNG gọi LLM
- Retrieval layer KHÔNG suy luận
- LLM Adapter KHÔNG biết gì về memory structure
- API layer KHÔNG chứa business logic

---

## 9. Rủi Ro Kỹ Thuật & Chiến Lược Phòng Ngừa

| # | Rủi Ro | Mức Nghiêm Trọng | Giải Pháp |
|---|---|---|---|
| 1 | **Memory Noise Explosion** — Sau 6 tháng, 10k records, embedding nhiễu | Cao | Re-embed định kỳ, tag clustering, importance_score |
| 2 | **Mode Drift** — LLM quên mode sau 30 lượt chat | Cao | Inject mode mỗi request, không rely conversation memory |
| 3 | **Memory Bias Lock-in** — AI chỉ reasoning từ quá khứ, củng cố sai lầm | Trung bình | CHALLENGE mode đối chiếu external knowledge |
| 4 | **Token Cost Explosion** — 10 records × 500 tokens mỗi query | Trung bình | Summarization layer, memory compression, token guard |
| 5 | **Embedding dimension thay đổi** | Thấp | Không overwrite cũ, thêm column mới |
| 6 | **Metadata phình to** | Thấp | Giới hạn JSON size, không dump raw document |
| 7 | **Search chậm > 500k records** | Trung bình | Tune HNSW ef_search, cache top results |

---

## 10. Đánh Giá Kiến Trúc

| Tiêu Chí | Điểm | Ghi Chú |
|---|---|---|
| Logic | 8.5/10 | Tách tầng đúng, flow rõ ràng |
| Triết lý | 9/10 | Memory-first, bất biến, không lock-in |
| Production readiness | 6/10 → 9/10 | Sau khi bổ sung schemas, exceptions, logging, tests |

**Kết luận:**  
Hướng đi đúng. Không mơ hồ. Không viển vông. Chỉ cần build đúng thiết kế là thành hệ thống thật.

---

## 11. Tài Liệu Liên Quan

| Tài liệu | Mô tả |
|---|---|
| [DATA_DESIGN.md](DATA_DESIGN.md) | DB schema, index, retrieval SQL, ranking formula |
| [CODEBASE_STRUCTURE.md](CODEBASE_STRUCTURE.md) | Cấu trúc thư mục, trách nhiệm từng file |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Roadmap triển khai, checklist, phân pha |
