# DATA DESIGN — AI Person (Bộ Não Thứ 2)

> **Project:** AI Person — Personal Memory-First AI System  
> **Version:** v0.3.0  
> **Last Updated:** 2026-02-22  
> **Database:** PostgreSQL 16 + pgvector  
> **ORM:** SQLAlchemy 2.0 (async)  
> **Migration:** Alembic  
> **Data Contract:** [MEMORY_CONTRACT.md](MEMORY_CONTRACT.md)

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

## 2. Column Types

### 2.1. content_type (VARCHAR — 6 giá trị cố định)

Chuẩn hóa loại nội dung memory. Validate ở Pydantic layer.

| Giá trị | Dùng khi | Ý nghĩa |
|---|---|---|
| `note` | Ghi chú chung | Fallback trung tính |
| `conversation` | Chat, bình luận | Nội dung dạng đối thoại |
| `reflection` | Quan điểm cá nhân | Phục vụ REFLECT mode |
| `idea` | Ý tưởng | Có thể phát triển |
| `article` | Kiến thức, link, repo, video, nhạc | Nội dung từ bên ngoài |
| `log` | Dữ kiện có cấu trúc | Chi tiêu, todo, tracking |

> ⚠️ Đã gộp `quote`, `repo`, `pdf`, `transcript` vào `note` / `article` từ v0.3.0.  
> ⚠️ `source_type` column đã bị xóa — thông tin nguồn gốc nằm trong `metadata.source`.

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
    content_type    VARCHAR(30) NOT NULL DEFAULT 'note',
    
    -- Embedding (dimension configurable via EMBEDDING_DIMENSION env var)
    embedding       vector(768),
    embedding_model VARCHAR(100),
    
    -- Integrity
    checksum        VARCHAR(64) NOT NULL,      -- SHA256(raw_text)
    version         INTEGER NOT NULL DEFAULT 1,
    
    -- Scoring
    importance_score FLOAT CHECK (importance_score >= 0 AND importance_score <= 1),
    
    -- Flexible metadata (Memory Contract V1 — see MEMORY_CONTRACT.md)
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
| `content_type` | VARCHAR(30) | Loại nội dung | 6 giá trị cố định, validate ở Pydantic |
| `embedding` | vector(768) | Vector embedding | Dimension configurable qua `EMBEDDING_DIMENSION` env var |
| `embedding_model` | VARCHAR(100) | Tên model đã dùng | Biết khi nào cần re-embed |
| `checksum` | VARCHAR(64) | SHA256(raw_text) | Phát hiện sửa đổi, verify backup, chống duplicate |
| `version` | INTEGER | Metadata version | raw_text bất biến, metadata có thể nâng version |
| `importance_score` | FLOAT | Điểm quan trọng (0.0–1.0) | Ranking, token trimming, decay theo thời gian |
| `metadata` | JSONB | Dữ liệu mở rộng | **Memory Contract V1** — xem [MEMORY_CONTRACT.md](MEMORY_CONTRACT.md) |
| `created_at` | TIMESTAMPTZ | Thời điểm tạo | Timezone-safe |
| `updated_at` | TIMESTAMPTZ | Thời điểm cập nhật | Chỉ update khi metadata/embedding thay đổi |

> ⚠️ `source_type` column đã bị xóa ở v0.3.0 — thông tin nguồn nằm trong `metadata.source`.

### 3.3. metadata JSONB — Memory Contract V1

Metadata tuân theo cấu trúc chuẩn hóa (chi tiết đầy đủ tại [MEMORY_CONTRACT.md](MEMORY_CONTRACT.md)):

```json
{
    "tags": ["ai", "code", "technical"],
    "type": "expense",
    "source": "cli",
    "source_urls": ["https://..."],
    "extra": {
        "person_name": "Linh",
        "amount": 45000,
        "currency": "VND"
    }
}
```

| Sub-field | Type | Mô tả |
|---|---|---|
| `tags` | `string[]` | Phân nhóm — 22 tags cố định (domain/format/style/system) |
| `type` | `string` | Logic đặc biệt: `expense`, `todo`, `bookmark` |
| `source` | `string` | Nguồn gốc: `cli`, `telegram`, `import`, `api` |
| `source_urls` | `string[]` | Links liên quan |
| `extra` | `object` | Mở rộng tự do — `person_name`, amount, etc. |

⚠️ Long Document Handling (Knowledge Base Use Case)

Nếu `content_type` là `article` hoặc document dài (> 2,000–3,000 tokens),
nên thực hiện chunking trước khi insert.

Mỗi chunk là một `memory_records` riêng, metadata nên chứa:

```json
{
  "parent_id": "<document_id>",
  "chunk_index": 1,
  "total_chunks": 20
}
```

V1 không tự động chunk. Chunking là trách nhiệm của ingestion layer.

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
| 7 | `idx_memory_embedding_model` | B-Tree | Isolation cross-model embedding — bắt buộc filter |

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

**Trọng số mặc định (Neutral cho `/search`):**

| Trọng số | Giá trị | Ý nghĩa |
|---|---|---|
| w1 (semantic) | 0.60 | 60% dựa trên similarity |
| w2 (recency) | 0.15 | 15% ưu tiên memory mới |
| w3 (importance) | 0.25 | 25% ưu tiên memory quan trọng |
⚠️ Lưu ý:
Trọng số trên là profile trung lập cho endpoint `/api/v1/search`.
Mode-aware weights chỉ dùng trong `/api/v1/query` (vì có `mode`).

### 7.2. Query SQL Chuẩn — App Layer Scoring

```sql
WITH candidates AS (
    SELECT
        id,
        raw_text,
        content_type,
        importance_score,
        created_at,
        metadata,
        is_summary,
        -- Semantic score (1 - cosine_distance = cosine_similarity)
        1 - (embedding <=> $1::vector) AS similarity
    FROM memory_records
    WHERE embedding IS NOT NULL
    AND exclude_from_retrieval = false
    AND is_archived = false
    AND embedding_model = $5
    AND ($7::boolean = true OR is_summary = false)
      -- Optional filters
      AND ($2::content_type IS NULL OR content_type = $2)
      AND ($3::timestamptz IS NULL OR created_at >= $3)
      AND ($4::timestamptz IS NULL OR created_at <= $4)
      -- No distance threshold in SQL (app layer controls relevance floors)
      ORDER BY embedding <=> $1::vector
    LIMIT 200  -- Candidate pool gọn để giữ latency ổn định
)
SELECT
    id,
    raw_text,
    content_type,
    importance_score,
    created_at,
    metadata,
    is_summary,
    similarity
FROM candidates
ORDER BY similarity DESC;


```
- SQL chỉ làm candidate retrieval + optional filters.
- Relevance control nằm ở app layer theo nguyên tắc `No-memory > Wrong-memory`.
- Recency dùng exponential decay thay vì inverse linear decay.
- Half-life mặc định = 30 ngày.

### 7.2.1 Ranking Profiles (Neutral + Reasoning Modes)

SQL chỉ lấy candidate theo `similarity`.
`final_score` được tính ở **app layer** (`retrieval/ranking.py`) theo profile:
- `/api/v1/search` → `NEUTRAL` (0.60 / 0.15 / 0.25)
- `/api/v1/query` → mode-aware

| Mode | Semantic | Recency | Importance | Lý Do |
|---|---|---|---|---|
| **NEUTRAL** (`/search`) | 0.60 | 0.15 | 0.25 | Ranking trung lập cho semantic search API |
| **RECALL** | 0.70 | 0.10 | 0.20 | Focus đúng memory, giảm recency bias |
| **RECALL_LLM_RERANK** | 0.70 | 0.10 | 0.20 | Recall có thêm bước LLM chọn memory liên quan nhất trong candidate pool |
| **SYNTHESIZE** | 0.60 | 0.05 | 0.35 | Gom toàn bộ knowledge, importance cao |
| **REFLECT** | 0.40 | 0.30 | 0.30 | Cần thấy evolution theo thời gian |
| **CHALLENGE** | 0.50 | 0.10 | 0.40 | Focus logic/mâu thuẫn, không thiên recency |
| **EXPAND** | 0.70 | 0.05 | 0.25 | Semantic cao vì cần tìm đúng memory để bổ sung external |

> ⚠️ **Architecture note:** `final_score` KHÔNG hardcode trong SQL.
> SQL trả candidate + `similarity`; app layer tính recency decay + composite score.
> `/query` có thêm diversity bonus nhỏ để giảm lặp memory:
> `bonus = min(0.02, 0.02 * (1 / (1 + retrieval_count)))`,
> chỉ áp dụng khi `similarity >= 0.70`.

```python
# App layer (retrieval/ranking.py)
# /search: mode=None -> NEUTRAL weights from settings
NEUTRAL_WEIGHTS = {"semantic": 0.60, "recency": 0.15, "importance": 0.25}

MODE_WEIGHTS = {
    "RECALL":     {"semantic": 0.70, "recency": 0.10, "importance": 0.20},
    "RECALL_LLM_RERANK": {"semantic": 0.70, "recency": 0.10, "importance": 0.20},
    "SYNTHESIZE": {"semantic": 0.60, "recency": 0.05, "importance": 0.35},
    "REFLECT":    {"semantic": 0.40, "recency": 0.30, "importance": 0.30},
    "CHALLENGE":  {"semantic": 0.50, "recency": 0.10, "importance": 0.40},
    "EXPAND":     {"semantic": 0.70, "recency": 0.05, "importance": 0.25},
}
```
### 7.3. Giải Thích Các Phần Quan Trọng

#### Early Candidate Limit (200)
- HNSW lấy top 200 gần nhất trước (candidate pool cố định).
- App layer mới quyết định record nào đủ liên quan để đi tiếp.
- Cách này tránh DB-level threshold quá lỏng và dễ debug hơn.

#### Production Relevance Floors (App Layer)
- `absolute_similarity_floor = 0.55` (mọi mode đều phải qua).
- `mode_similarity_floor`:
  - `RECALL = 0.65`
  - `RECALL_LLM_RERANK = 0.60`
  - `SYNTHESIZE = 0.60`
  - `REFLECT = 0.55`
  - `CHALLENGE = 0.60`
  - `EXPAND = 0.52`
- `requested_similarity_floor = 1 - threshold` (từ request).
- Floor dùng thực tế: `max(absolute_floor, mode_floor, requested_floor)`.
- Nếu không còn candidate sau floor → trả rỗng ngay (không ép LLM dùng memory gần gần).

#### Score Gap + Hard Cap
- Sau khi tính `final_score`, giữ cluster gần top:
  - `top_final_score - final_score <= 0.15`.
- Sau đó áp hard cap theo mode:
  - `RECALL = 5`
  - `RECALL_LLM_RERANK = 12` (LLM re-rank từ pool này rồi trả top 5)
  - `SYNTHESIZE = 8`
  - `REFLECT = 8`
  - `CHALLENGE = 4`
  - `EXPAND = 10`
- Triết lý: precision trước, giảm context noise.

#### Query Replay Cooldown (RECALL/CHALLENGE)
- Khi user lặp lại cùng `query` và `mode`, hệ thống lấy memory_ids từ một số log gần nhất.
- Những memory vừa dùng gần đây không bị loại bỏ, nhưng bị reorder xuống sau các memory "fresh".
- Cooldown chỉ chạy sau khi đã qua semantic floors + gap filter, nên không làm giảm precision.

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
WHERE metadata @> '{"tags": ["ai"]}'

-- Filter theo person_name
WHERE metadata @> '{"extra": {"person_name": "Linh"}}'

-- Filter theo metadata.type
WHERE metadata @> '{"type": "expense"}'

-- Filter theo source
WHERE metadata @> '{"source": "cli"}'

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

### 8.2. Hybrid Context Strategy — V1 Drop-Only

1. Lấy top 30 records (đã rank theo final_score)
2. Tính tổng token của từng record
3. Nếu vượt budget (`MAX_CONTEXT_TOKENS = 3000`):
   - Giữ các memory fit trong budget (theo thứ tự final_score DESC)
   - **Drop phần còn lại** — không summarize, không truncate text

> ⚠️ **V1 Strict: Không có runtime summarization.**
> "Tóm tắt 10 cái tiếp theo" là V2 feature, không được implement ở V1.
> Lý do: LLM không được ghi vào memory (nguyên tắc #2).
> Đây là trách nhiệm của `TokenGuard.check_budget()` — drop-only.

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
| `content_type` | VARCHAR(30) | `str` | 6 giá trị cố định, validate ở Pydantic |
| `embedding` | vector(768) | `list[float]` | Dimension configurable qua env var |
| `metadata` | JSONB | `dict` | Memory Contract V1 — filter linh hoạt, GIN index |
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
- Nới `threshold` theo bước nhỏ (ví dụ 0.45 → 0.50), nhưng vẫn bị chặn bởi `absolute_similarity_floor = 0.55`
- Không hạ `absolute_similarity_floor` trừ khi đã phân tích distribution thực tế
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


### 11.7 Summary Strategy (V1 Locked — Strict)

**V1: LLM không được persist summary vào memory_records.**

Lý do: Nguyên tắc #2 của hệ thống — "LLM không được sửa hoặc ghi trực tiếp vào memory."
Nếu LLM insert summary → vi phạm core principle.

#### V1 Rules

| Rule | Chi Tiết |
|---|---|
| LLM không insert summary | Summary do LLM tạo là **ephemeral** — dùng trong request, không ghi DB |
| `is_summary` field | **Reserved cho V2**. V1 không dùng |
| Token trimming | **Drop-only**: nếu vượt budget → drop memory thấp nhất, không summarize |
| Retrieval | `is_summary = false` filter luôn bật (vì V1 không có summary records) |

#### V2 — Summary Persistence (Planned)

Khi implement V2, summary được phép lưu **với điều kiện nghiêm ngặt**:
- `is_summary = true` — bắt buộc
- `metadata.parent_id` → trỏ memory gốc
- `metadata.generated_by = "system"` — không phải user
- Không được dùng trong RECALL và CHALLENGE
- Mặc định bị loại khỏi retrieval trừ khi `include_summaries=true`
- User phải approve trước khi persist (hoặc auto-expire)

### 11.8 Engagement Tracking (V2 Planned)

V2 sẽ thêm engagement fields vào `memory_records` để ranking formula thông minh hơn:

```sql
-- V2: Thêm 3 cột
ALTER TABLE memory_records ADD COLUMN access_count INTEGER DEFAULT 0;
ALTER TABLE memory_records ADD COLUMN last_accessed_at TIMESTAMPTZ;
ALTER TABLE memory_records ADD COLUMN decay_score FLOAT DEFAULT 1.0;
```

| Field | Type | Mục Đích |
|---|---|---|
| `access_count` | `int` | Số lần memory được retrieve (popularity) |
| `last_accessed_at` | `timestamptz` | Lần cuối memory xuất hiện trong context |
| `decay_score` | `float` | Precomputed decay (cron update hàng ngày) |

**V2 Ranking formula update:**

```
final_score =
    0.50 * semantic_similarity
  + 0.10 * recency_decay
  + 0.20 * importance_score
  + 0.10 * engagement_boost      ← NEW
  + 0.10 * decay_score            ← NEW
```

> ⚠️ **V1:** Không implement. Dùng formula hiện tại (0.60/0.15/0.25).

## 12. Migration Strategy (Alembic)

### 12.1. Setup

Migration files được đặt tại `app/db/migrations/` (không phải root `alembic/`).
Cấu hình trong `alembic.ini`:

```ini
script_location = app/db/migrations
```

Cấu trúc đúng:
```
app/db/migrations/
├── env.py              # Async migration runner
├── script.py.mako      # Template
└── versions/
    └── 001_initial_schema.py
```

### 12.2. Cấu Hình `alembic.ini`

```ini
script_location = app/db/migrations
prepend_sys_path = .
# sqlalchemy.url được load từ .env qua app/config.py — không hardcode ở đây
```

### 12.3. Revision Đầu Tiên

Revision đầu tiên đã được tạo thủ công tại `app/db/migrations/versions/001_initial_schema.py`.
Với schema thay đổi sau này:

```bash
alembic revision --autogenerate -m "describe_change"
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
│     content_type     VARCHAR(30)              │
│     embedding        vector(768)              │
│     embedding_model  VARCHAR(100)             │
│     checksum         VARCHAR(64) UNIQUE       │
│     version          INTEGER                  │
│     importance_score FLOAT                    │
│     metadata         JSONB (Contract V1)      │
│     is_archived      BOOLEAN                  │
│     exclude_from_retrieval BOOLEAN            │
│     is_summary       BOOLEAN                  │
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
| [MEMORY_CONTRACT.md](MEMORY_CONTRACT.md) | **Memory Contract V1** — chuẩn data import, tag registry |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | Kiến trúc tổng thể, triết lý, flows |
| [CODEBASE_STRUCTURE.md](CODEBASE_STRUCTURE.md) | Cấu trúc thư mục, file responsibilities |
| [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Roadmap, checklist triển khai |
