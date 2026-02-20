# DATA DESIGN — AI Person (Bộ Não Thứ 2)

> **Project:** AI Person — Personal Memory-First AI System  
> **Version:** V1 (Pre-release)  
> **Last Updated:** 2026-02-20  
> **Database:** PostgreSQL 16 + pgvector  
> **ORM:** SQLAlchemy 2.0 (async)  
> **Migration:** Alembic

---

## 1. Triết Lý Thiết Kế Database

4 nguyên tắc bất biến trước khi viết bất kỳ bảng nào:

| # | Nguyên Tắc | Hệ Quả |
|---|---|---|
| 1 | **Raw text là vĩnh viễn** | Không UPDATE, không DELETE `raw_text` |
| 2 | **Embedding có thể thay đổi** | Track `embedding_model`, hỗ trợ re-embed |
| 3 | **Metadata có thể version** | `raw_text` bất biến, metadata có version |
| 4 | **Không để bảng phình không kiểm soát** | Partition strategy, size guard cho JSONB |

---

## 2. ENUM Types

### 2.1. content_type

Chuẩn hóa loại nội dung memory. Không cho phép free text.

```sql
CREATE TYPE content_type AS ENUM (
    'note',          -- ghi chú cá nhân
    'conversation',  -- đoạn chat
    'quote',         -- câu nói hay
    'repo',          -- github / project link
    'article',       -- blog / bài viết
    'pdf',           -- file dài (đã extract text)
    'transcript',    -- speech to text
    'idea',          -- ý tưởng chợt nảy
    'reflection',    -- suy nghĩ sâu
    'log'            -- hệ thống
);
```

### 2.2. source_type

Xác định nguồn gốc dữ liệu — phục vụ audit.

```sql
CREATE TYPE source_type AS ENUM (
    'manual',     -- user tự nhập
    'api',        -- qua API
    'import',     -- import batch
    'ocr',        -- từ ảnh/scan
    'whisper',    -- speech-to-text
    'crawler'     -- crawl từ web
);
```

---

## 3. Bảng Chính: `memory_records`

Đây là **lõi của toàn bộ hệ thống**. Mọi dữ liệu đều quy về bảng này.

### 3.1. Schema

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

CREATE TABLE memory_records (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    raw_text        TEXT NOT NULL,
    content_type    content_type NOT NULL DEFAULT 'note',
    source_type     source_type NOT NULL DEFAULT 'manual',
    
    -- Embedding
    embedding       vector(1536),
    embedding_model VARCHAR(100),
    
    -- Integrity
    checksum        VARCHAR(64) NOT NULL,      -- SHA256(raw_text)
    version         INTEGER NOT NULL DEFAULT 1,
    
    -- Scoring
    importance_score FLOAT CHECK (importance_score >= 0 AND importance_score <= 1),
    
    -- Flexible metadata
    metadata        JSONB DEFAULT '{}',

    is_archived BOOLEAN NOT NULL DEFAULT false,
    exclude_from_retrieval BOOLEAN NOT NULL DEFAULT false,
    is_summary BOOLEAN NOT NULL DEFAULT false,
    
    -- Timestamps
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 3.2. Giải Thích Từng Field

| Field | Type | Mục Đích | Ghi Chú |
|---|---|---|---|
| `id` | UUID | Primary key | An toàn, không đoán được |
| `raw_text` | TEXT | Nội dung gốc | **BẤT BIẾN — không bao giờ UPDATE** |
| `content_type` | ENUM | Loại nội dung | Chuẩn hóa, index được |
| `source_type` | ENUM | Nguồn gốc | Phục vụ audit trail |
| `embedding` | vector(1536) | Vector embedding | Khớp với OpenAI text-embedding-3-small |
| `embedding_model` | VARCHAR(100) | Tên model đã dùng | Biết khi nào cần re-embed |
| `checksum` | VARCHAR(64) | SHA256(raw_text) | Phát hiện sửa đổi, verify backup, chống duplicate |
| `version` | INTEGER | Metadata version | raw_text bất biến, metadata có thể nâng version |
| `importance_score` | FLOAT | Điểm quan trọng (0.0–1.0) | Ranking, token trimming, decay theo thời gian |
| `metadata` | JSONB | Dữ liệu mở rộng | Tags, source_url, project, mood... |
| `created_at` | TIMESTAMPTZ | Thời điểm tạo | Timezone-safe |
| `updated_at` | TIMESTAMPTZ | Thời điểm cập nhật | Chỉ update khi metadata/embedding thay đổi |

⚠️ Nếu lưu document dài (PDF, article),
nên chunk trước khi insert để đảm bảo chất lượng embedding.
V1 không tự động chunk.
### 3.3. Ví Dụ metadata JSONB

```json
{
    "tags": ["architecture", "AI"],
    "project": "ai-person",
    "source_url": "https://...",
    "mood": "focused",
    "language": "vi"
}
```
⚠️ Long Document Handling (Knowledge Base Use Case)

Nếu content_type là 'pdf', 'article', hoặc document dài (> 2,000–3,000 tokens),
nên thực hiện chunking trước khi insert.

Mỗi chunk là một memory_records riêng,
metadata nên chứa:

{
  "parent_id": "<document_id>",
  "chunk_index": 1,
  "total_chunks": 20
}

V1 không tự động chunk.
Chunking là trách nhiệm của ingestion layer.

**Quy tắc metadata:**
- Giới hạn size JSON (khuyến nghị < 4KB)
- KHÔNG dump raw document vào metadata
- Dùng cho filter linh hoạt, không phải lưu trữ chính

---

## 4. Bảng Phụ: `embedding_jobs`

**Tại sao cần?** Không embed trực tiếp khi insert. Phải tách 2 giai đoạn để tránh block request.

### 4.1. Schema

```sql
CREATE TABLE embedding_jobs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    memory_id       UUID NOT NULL REFERENCES memory_records(id) ON DELETE CASCADE,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- status: 'pending' | 'processing' | 'completed' | 'failed'
    attempts        INTEGER DEFAULT 0,
    max_attempts    INTEGER DEFAULT 3,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);
```

### 4.2. Lifecycle

```
pending → processing → completed
                    ↘ failed (retry nếu attempts < max_attempts)
```

---

## 5. Bảng Phụ: `reasoning_logs`

**Mục đích:** Debug hallucination, audit suy luận, theo dõi chất lượng.

### 5.1. Schema

```sql
CREATE TABLE reasoning_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_query      TEXT NOT NULL,
    mode            VARCHAR(30) NOT NULL,
    memory_ids      UUID[] DEFAULT '{}',
    prompt_hash VARCHAR(64),
    debug_prompt TEXT,
    external_knowledge_used BOOLEAN DEFAULT false,
    confidence_score FLOAT DEFAULT 0.5,
    response        TEXT,
    token_usage     JSONB DEFAULT '{}',
    -- token_usage: {"prompt_tokens": 500, "completion_tokens": 200, "total": 700}
    latency_ms      INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```
- prompt_hash: SHA256(prompt) để audit.
- debug_prompt: chỉ lưu khi DEBUG mode.
- external_knowledge_used: đánh dấu epistemic boundary.
- confidence_score: LLM tự ước lượng độ chắc chắn.

### 5.2. Tại Sao Quan Trọng

- Khi AI trả lời sai → xem `memory_ids` để biết nó dựa vào memory nào
- Khi tốn token → xem `token_usage` để tối ưu
- Khi chậm → xem `latency_ms` để debug
- Audit toàn bộ lịch sử suy luận

---

## 6. Index Strategy — Production Grade

### 6.1. Tổng Quan Index

| # | Index | Loại | Mục Đích |
|---|---|---|---|
| 1 | `idx_memory_embedding` | HNSW | Semantic search nhanh |
| 2 | `idx_memory_created_at` | B-Tree | Filter theo thời gian |
| 3 | `idx_memory_content_type` | B-Tree | Filter theo loại nội dung |
| 4 | `idx_memory_metadata` | GIN | Filter JSONB linh hoạt |
| 5 | `idx_memory_checksum` | B-Tree UNIQUE | Chống duplicate insert |
| 6 | `idx_embedding_jobs_status` | B-Tree | Worker poll nhanh |

### 6.2. SQL Tạo Index

```sql
-- 1. HNSW index cho semantic search (quan trọng nhất)
CREATE INDEX idx_memory_embedding
ON memory_records
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 200);

-- 2. Index theo thời gian
CREATE INDEX idx_memory_created_at
ON memory_records (created_at DESC);

-- 3. Index theo content_type
CREATE INDEX idx_memory_content_type
ON memory_records (content_type);

-- 4. GIN index cho metadata (JSONB)
CREATE INDEX idx_memory_metadata
ON memory_records USING GIN (metadata);

-- 5. Unique checksum (chống duplicate)
CREATE UNIQUE INDEX idx_memory_checksum
ON memory_records (checksum);

-- 6. Embedding jobs status (cho worker poll)
CREATE INDEX idx_embedding_jobs_status
ON embedding_jobs (status, created_at ASC);

-- 7. Index theo embedding_model
CREATE INDEX idx_memory_embedding_model
ON memory_records (embedding_model);
```

### 6.3. Tại Sao HNSW Thay Vì IVFFlat

| Tiêu chí | HNSW | IVFFlat |
|---|---|---|
| Chất lượng recall | Cao hơn | Thấp hơn |
| Tốc độ build | Chậm hơn | Nhanh hơn |
| Tốc độ query | Nhanh | Nhanh |
| Production grade | ✅ Tốt hơn | Prototype |
| Không cần retrain | ✅ | Cần retrain clusters |

---

## 7. Retrieval Query — SQL Chuẩn Production

### 7.1. Công Thức Ranking

Không bao giờ chỉ dùng cosine similarity. Phải có **scoring formula tổng hợp**:

```
final_score = (w1 × semantic_score) + (w2 × recency_score) + (w3 × importance_score)
```

**Trọng số mặc định (Recall cao):**

| Trọng số | Giá trị | Ý nghĩa |
|---|---|---|
| w1 (semantic) | 0.60 | 60% dựa trên similarity |
| w2 (recency) | 0.15 | 15% ưu tiên memory mới |
| w3 (importance) | 0.25 | 25% ưu tiên memory quan trọng |
⚠️ Lưu ý:
Trọng số trên là mặc định.
Retrieval có thể điều chỉnh trọng số theo mode:

- RECALL: có thể giảm hoặc bỏ recency
- REFLECT: giữ recency
- CHALLENGE: recency thấp
### 7.2. Query SQL Chuẩn — Recall Cao

```sql
WITH candidates AS (
    SELECT
        id,
        raw_text,
        content_type,
        importance_score,
        created_at,
        metadata,
        -- Semantic score (1 - cosine_distance = cosine_similarity)
        1 - (embedding <=> $1::vector) AS similarity
    FROM memory_records
    WHERE embedding IS NOT NULL
    AND exclude_from_retrieval = false
    AND is_archived = false
    AND embedding_model = $5
      -- Optional filters
      AND ($2::content_type IS NULL OR content_type = $2)
      AND ($3::timestamptz IS NULL OR created_at >= $3)
      AND ($4::timestamptz IS NULL OR created_at <= $4)
      -- Distance threshold (< 0.7 cho recall cao)
      AND (embedding <=> $1::vector) < $6
    ORDER BY embedding <=> $1::vector
    LIMIT 500  -- Candidate pool lớn cho recall cao
)
SELECT
    id,
    raw_text,
    content_type,
    importance_score,
    created_at,
    metadata,
    similarity,
    -- Final ranking score
    (
        0.60 * similarity
      + 0.15 * EXP(
    - EXTRACT(EPOCH FROM (NOW() - created_at)) 
      / (86400.0 * 30.0)
)
      + 0.25 * COALESCE(importance_score, 0.5)
    ) AS final_score
FROM candidates
ORDER BY final_score DESC
LIMIT 30;


```
- Recency dùng exponential decay thay vì inverse linear decay.
- Half-life mặc định = 30 ngày.
- Mode-specific ranking có thể override decay rate.
⚠ Bắt buộc filter theo embedding_model.
Không được search cross-model embeddings.
⚠️ Lưu ý:
Công thức recency hiện tại ưu tiên mạnh memory mới.
Nếu hệ thống cần so sánh evolution dài hạn (REFLECT),
có thể cần giảm trọng số recency.
### 7.3. Giải Thích Các Phần Quan Trọng

#### Early Candidate Limit (500)
- HNSW lấy top 500 gần nhất trước
- Sau đó re-rank bằng scoring formula
- Nếu không tách 2 bước → recency + importance không hiệu quả

#### Similarity Threshold (< 0.7)
- Cosine distance < 0.7 ≈ similarity > 0.3
- Nếu không có threshold → LLM bị ép dùng memory không liên quan → hallucination

#### Recency Decay
```sql
EXP(
    - EXTRACT(EPOCH FROM (NOW() - created_at))
      / (86400.0 * 30.0)
)
```
- Memory 1 ngày trước → ≈ 0.97
- Memory 7 ngày trước → ≈ 0.79
- Memory 30 ngày trước → ≈ 0.37
- Memory 60 ngày trước → ≈ 0.14
### 7.4. Metadata Filter

```sql
-- Filter theo tag
WHERE metadata @> '{"tags": ["architecture"]}'

-- Filter theo project
WHERE metadata @> '{"project": "ai-person"}'

-- Phải có GIN index để nhanh
```

### 7.5. Multi-Type Filter

```sql
WHERE content_type IN ('note', 'reflection', 'idea')
```

### 7.6. Query Tối Giản (V1 Quick Start)

Nếu chưa cần ranking formula:

```sql
SELECT id, raw_text, content_type,
       1 - (embedding <=> $1::vector) AS similarity
FROM memory_records
WHERE embedding IS NOT NULL
  AND (embedding <=> $1::vector) < $6
ORDER BY embedding <=> $1::vector
LIMIT 20;
```

---

## 8. Token Budget (App Layer)

SQL chỉ trả `id`, `raw_text`, `score`. App layer phải kiểm soát token.

### 8.1. Token Trimming Strategy

```python
def select_memories_within_budget(
    memories: list,
    max_tokens: int = 3000
) -> list:
    selected = []
    total_tokens = 0
    
    for memory in sorted(memories, key=lambda m: m.final_score, reverse=True):
        tokens = count_tokens(memory.raw_text)
        if total_tokens + tokens > max_tokens:
            break
        selected.append(memory)
        total_tokens += tokens
    
    return selected
```

### 8.2. Hybrid Context Strategy (Cho Recall Cao)

1. Lấy top 30 records
2. Tính token
3. Nếu vượt budget:
   - Giữ full text cho **top 5**
   - Tóm tắt **10 cái tiếp theo**
   - Drop phần còn lại

### 8.3. Diversity Guard

Recall cao dễ gặp vấn đề top 10 giống nhau 90%.

```python
def deduplicate_memories(memories: list, threshold: float = 0.95) -> list:
    """Nếu 2 memory cosine > threshold → chỉ giữ 1"""
    unique = []
    for m in memories:
        if not any(cosine_sim(m.embedding, u.embedding) > threshold for u in unique):
            unique.append(m)
    return unique
```

---

## 9. Data Types Reference

| Field | PostgreSQL Type | Python Type | Lý Do |
|---|---|---|---|
| `id` | UUID | `uuid.UUID` | An toàn, không đoán được |
| `raw_text` | TEXT | `str` | Không giới hạn kích thước |
| `embedding` | vector(1536) | `list[float]` | Khớp OpenAI model dimension |
| `metadata` | JSONB | `dict` | Filter linh hoạt, GIN index |
| `created_at` | TIMESTAMPTZ | `datetime` | Timezone-safe |
| `checksum` | VARCHAR(64) | `str` | SHA256 hash = 64 hex chars |
| `importance_score` | FLOAT | `float` | 0.0–1.0 |
| `memory_ids` | UUID[] | `list[uuid.UUID]` | Array trong reasoning_logs |

---

## 10. Tối Ưu Cho Scale (> 1M Records)

### 10.1. Partition Strategy

Khi > 1M records, partition `memory_records` theo tháng:

```sql
CREATE TABLE memory_records (
    ...
) PARTITION BY RANGE (created_at);

CREATE TABLE memory_records_2026_01 
    PARTITION OF memory_records 
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
```

### 10.2. HNSW Tuning

```sql
-- Tăng ef_search cho accuracy cao hơn (mặc định 40)
SET hnsw.ef_search = 200;

-- Hoặc tạo index với params custom
CREATE INDEX idx_memory_embedding_tuned
ON memory_records
USING hnsw (embedding vector_cosine_ops)
WITH (m = 24, ef_construction = 300);
```

### 10.3. Maintenance

| Task | Tần Suất |
|---|---|
| VACUUM | Tự động (autovacuum) |
| REINDEX embedding | Mỗi 6 tháng |
| Autovacuum tuning | Theo load |
| Backup full | Hàng ngày |

---

## 11. Rủi Ro Data & Cách Phòng

### 11.1. Embedding Dimension Thay Đổi

**Vấn đề:** Đổi sang model mới có dimension khác (vd: 1536 → 3072)

**Giải pháp:**
- KHÔNG overwrite embedding cũ
- Thêm column mới: `embedding_v2 vector(3072)`
- Migrate dần, không bắt buộc tất cả cùng lúc
- Field `embedding_model` giúp track model nào đang dùng

### 11.2. Metadata Phình To

**Vấn đề:** JSONB lớn → query chậm, storage phình

**Giải pháp:**
- Giới hạn size JSON < 4KB
- Không cho dump raw document vào metadata
- Validate size ở app layer trước khi insert

### 11.3. Search Chậm Khi > 500K Records

**Vấn đề:** HNSW performance giảm ở scale lớn

**Giải pháp:**
- Tune `hnsw.ef_search` (tăng = chính xác hơn nhưng chậm hơn)
- Giảm candidate pool size nếu latency quá cao
- Cache top results cho query phổ biến
- Partition table

### 11.4. Retrieval Trả Về Quá Ít

**Vấn đề:** Query trả về < 5 records

**Giải pháp (app layer):**
- Hạ threshold từ 0.7 xuống 0.6
- Retry search
- KHÔNG để LLM tự quyết có đủ context không

### 11.5. Memory Domination

**Vấn đề:** 1 record quá dài (10K tokens) chiếm hết budget

**Giải pháp:**
- Lưu summary song song với raw_text
- Retrieval trả summary trước
- Khi cần expand → lấy full text

---
### 11.6 Selective Forgetting Strategy

Memory không bị DELETE.
Nhưng có thể:

- is_archived = true → vẫn tồn tại, không xuất hiện trong retrieval.
- exclude_from_retrieval = true → loại khỏi reasoning layer.

Selective forgetting là loại khỏi lớp suy luận, không phải xóa khỏi storage.


### 11.7 Summary Strategy (V1 Locked)

Summary được phép lưu trong memory_records.

Quy tắc bắt buộc:

- raw_text gốc không bao giờ bị thay thế.
- Summary phải có metadata.parent_id trỏ tới memory gốc.
- is_summary = true.
- Summary không được dùng trong RECALL mode.
- Summary không được dùng trong CHALLENGE mode.
- Retrieval mặc định loại bỏ is_summary = true.
- REFLECT mode có thể sử dụng summary nếu thiếu token budget.

Summary là lớp tối ưu hóa retrieval,
không phải memory gốc.

## 12. Migration Strategy (Alembic)

### 12.1. Setup

```bash
pip install alembic
alembic init alembic
```

### 12.2. Cấu Hình `alembic.ini`

```ini
sqlalchemy.url = postgresql+asyncpg://user:pass@localhost:5432/ai_person
```

### 12.3. Revision Đầu Tiên

```bash
alembic revision --autogenerate -m "initial_schema"
```

### 12.4. Upgrade

```bash
alembic upgrade head
```

### 12.5. Quy Tắc Migration

- Mỗi thay đổi schema = 1 migration file
- KHÔNG sửa migration đã chạy
- Test migration trên DB copy trước khi chạy production
- Backup trước mỗi migration

---

## 13. Entity Relationship Diagram

```
┌─────────────────────────────────────────────┐
│              memory_records                  │
├─────────────────────────────────────────────┤
│ PK  id              UUID                     │
│     raw_text         TEXT (IMMUTABLE)         │
│     content_type     content_type ENUM        │
│     source_type      source_type ENUM         │
│     embedding        vector(1536)             │
│     embedding_model  VARCHAR(100)             │
│     checksum         VARCHAR(64) UNIQUE       │
│     version          INTEGER                  │
│     importance_score FLOAT                    │
│     metadata         JSONB                    │
│     is_archived      BOOLEAN                  │
│     exclude_from_retrieval BOOLEAN            │
│     created_at       TIMESTAMPTZ              │
│     updated_at       TIMESTAMPTZ              │
├─────────────────────────────────────────────┤
│ IDX  HNSW(embedding)                         │
│ IDX  B-Tree(created_at DESC)                 │
│ IDX  B-Tree(content_type)                    │
│ IDX  GIN(metadata)                           │
│ IDX  UNIQUE(checksum)                        │
└──────────────────────┬──────────────────────┘
                       │ 1:N
                       ▼
┌─────────────────────────────────────────────┐
│              embedding_jobs                  │
├─────────────────────────────────────────────┤
│ PK  id              UUID                     │
│ FK  memory_id        UUID → memory_records   │
│     status           VARCHAR(20)              │
│     attempts         INTEGER                  │
│     max_attempts     INTEGER                  │
│     error_message    TEXT                      │
│     created_at       TIMESTAMPTZ              │
│     completed_at     TIMESTAMPTZ              │
├─────────────────────────────────────────────┤
│ IDX  B-Tree(status, created_at ASC)          │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│              reasoning_logs                  │
├─────────────────────────────────────────────┤
│ PK  id              UUID                     │
│     user_query       TEXT                     │
│     mode             VARCHAR(30)              │
│     memory_ids       UUID[]                   │
│     prompt_hash      VARCHAR(64)              │
│     debug_prompt     TEXT                     │
│     external_knowledge_used BOOLEAN           │
│     confidence_score FLOAT                    │
│     response         TEXT                     │
│     token_usage      JSONB                    │
│     latency_ms       INTEGER                  │
│     created_at       TIMESTAMPTZ              │
└─────────────────────────────────────────────┘
```

---

## 14. Tài Liệu Liên Quan

| Tài liệu | Mô tả |
|---|---|
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | Kiến trúc tổng thể, triết lý, flows |
| [CODEBASE_STRUCTURE.md](CODEBASE_STRUCTURE.md) | Cấu trúc thư mục, file responsibilities |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Roadmap, checklist triển khai |
