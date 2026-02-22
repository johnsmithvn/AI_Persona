# API Documentation — AI Person v0.3.0

> **Base URL:** `http://localhost:8000`  
> **OpenAPI (Swagger):** `http://localhost:8000/docs`  
> **ReDoc:** `http://localhost:8000/redoc`

---

## 📋 Quick Reference

| Method | Endpoint | Mục Đích |
|---|---|---|
| `POST` | `/api/v1/memory` | Lưu memory mới |
| `GET` | `/api/v1/memory/{id}` | Lấy memory theo ID |
| `PATCH` | `/api/v1/memory/{id}/archive` | Archive / soft-delete |
| `POST` | `/api/v1/search` | Semantic search |
| `POST` | `/api/v1/query` | Reasoning (6-Mode) |
| `GET` | `/health` | Health check |

---

## 1. Memory Endpoints

### 1.1 POST `/api/v1/memory` — Tạo Memory

Lưu một memory mới vào hệ thống. Embedding được tạo **bất đồng bộ** bởi worker.

**Request Body:**

```json
{
    "raw_text": "LoRA giúp fine-tune LLM hiệu quả hơn full fine-tuning rất nhiều.",
    "content_type": "note",
    "importance_score": 0.8,
    "metadata": {
        "tags": ["ai", "technical"],
        "source": "api"
    }
}
```

| Field | Type | Required | Default | Ghi Chú |
|---|---|---|---|---|
| `raw_text` | `string` | ✅ | — | Min 1 char. **Immutable** sau khi insert |
| `content_type` | `string` | ❌ | `"note"` | 6 giá trị: `note`, `conversation`, `reflection`, `idea`, `article`, `log` |
| `importance_score` | `float` | ❌ | `null` | Range: `0.0` – `1.0` |
| `metadata` | `object` | ❌ | `{}` | Memory Contract V1 — xem [MEMORY_CONTRACT.md](../docs/MEMORY_CONTRACT.md) |

> ⚠️ `source_type` đã bị xóa từ v0.3.0. Nguồn gốc data lưu trong `metadata.source`.

**Response (201 Created):**

```json
{
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "raw_text": "LoRA giúp fine-tune LLM hiệu quả hơn full fine-tuning rất nhiều.",
    "content_type": "note",
    "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4...",
    "importance_score": 0.8,
    "metadata": {"tags": ["ai", "technical"], "source": "api"},
    "is_archived": false,
    "exclude_from_retrieval": false,
    "is_summary": false,
    "has_embedding": false,
    "created_at": "2026-02-20T23:00:00Z",
    "updated_at": "2026-02-20T23:00:00Z"
}
```

> **Note:** `has_embedding` sẽ là `false` ngay sau khi tạo. Khi worker xử lý xong embedding job → trở thành `true`.

**Errors:**

| Code | HTTP | Khi Nào |
|---|---|---|
| `DUPLICATE_MEMORY` | `409` | `raw_text` trùng checksum SHA256 với record đã tồn tại |

---

### 1.2 GET `/api/v1/memory/{memory_id}` — Lấy Memory

**Path Parameters:**

| Param | Type | Ghi Chú |
|---|---|---|
| `memory_id` | `UUID` | ID của memory record |

**Response (200 OK):** Same schema as `MemoryResponse` above.

**Errors:**

| Code | HTTP | Khi Nào |
|---|---|---|
| `MEMORY_NOT_FOUND` | `404` | UUID không tồn tại |

---

### 1.3 PATCH `/api/v1/memory/{memory_id}/archive` — Archive Memory

Selective forgetting: soft-archive memory. **`raw_text` không bao giờ bị xóa.**

**Path Parameters:**

| Param | Type |
|---|---|
| `memory_id` | `UUID` |

**Request Body:**

```json
{
    "is_archived": true,
    "exclude_from_retrieval": true
}
```

| Field | Type | Default | Ghi Chú |
|---|---|---|---|
| `is_archived` | `bool` | `true` | Đánh dấu archived |
| `exclude_from_retrieval` | `bool` | `false` | Loại khỏi search results |

**Response (200 OK):** `MemoryResponse` với flags đã update.

---

## 2. Search Endpoint

### 2.1 POST `/api/v1/search` — Semantic Search

Tìm kiếm memory bằng ngôn ngữ tự nhiên.
`/api/v1/search` luôn dùng **neutral ranking profile** để tính `final_score`:
- semantic: `0.60`
- recency: `0.15`
- importance: `0.25`

Mode-aware ranking chỉ áp dụng trong `/api/v1/query` (vì endpoint này có field `mode`).

**Request Body:**

```json
{
    "query": "Tôi đã nghiên cứu gì về LoRA?",
    "content_type": "note",
    "start_date": "2025-01-01T00:00:00Z",
    "end_date": null,
    "limit": 20,
    "threshold": 0.45,
    "metadata_filter": {"tags": ["ai"]},
    "include_summaries": false
}
```

| Field | Type | Required | Default | Ghi Chú |
|---|---|---|---|---|
| `query` | `string` | ✅ | — | Natural language search |
| `content_type` | `string` | ❌ | `null` | Filter theo loại. 6 giá trị: `note`, `conversation`, `reflection`, `idea`, `article`, `log` |
| `start_date` | `datetime` | ❌ | `null` | ISO 8601 |
| `end_date` | `datetime` | ❌ | `null` | ISO 8601 |
| `limit` | `int` | ❌ | `20` | Range: `1` – `100` |
| `threshold` | `float` | ❌ | `0.45` | Cosine distance threshold. App layer chuyển sang similarity floor theo `similarity = 1 - threshold` |
| `metadata_filter` | `object` | ❌ | `null` | JSONB containment filter (`@>`). Ví dụ: `{"tags": ["ai"]}`, `{"extra": {"person_name": "Linh"}}` |
| `include_summaries` | `bool` | ❌ | `false` | Include `is_summary=true` records (V1: luôn `false`) |

**Response (200 OK):**

```json
{
    "results": [
        {
            "id": "a1b2c3d4-...",
            "raw_text": "LoRA giúp fine-tune LLM hiệu quả...",
            "content_type": "note",
            "importance_score": 0.8,
            "created_at": "2026-02-20T23:00:00Z",
            "metadata": {"tags": ["ai"]},
            "similarity": 0.92,
            "final_score": 0.87,
            "is_summary": false
        }
    ],
    "total": 1,
    "query": "Tôi đã nghiên cứu gì về LoRA?",
    "ranking_profile": "NEUTRAL"
}
```

| Response Field | Ghi Chú |
|---|---|
| `similarity` | Raw cosine similarity (`0.0` – `1.0`) |
| `final_score` | Composite ranking score (semantic + recency + importance) |
| `ranking_profile` | Profile dùng để tính `final_score`. `/search` luôn là `NEUTRAL` |
| `total` | Số lượng kết quả trả về |

---

## 3. Query (Reasoning) Endpoint

### 3.1 POST `/api/v1/query` — Reasoning Pipeline

Full reasoning pipeline:
`Retrieval → TokenGuard → Mode → (Deterministic Recall OR Prompt → LLM) → Response`

**Request Body:**

```json
{
    "query": "Tư duy của tao về AI thay đổi thế nào?",
    "mode": "REFLECT",
    "content_type": null,
    "threshold": 0.45
}
```

| Field | Type | Required | Default | Ghi Chú |
|---|---|---|---|---|
| `query` | `string` | ✅ | — | Question hoặc prompt |
| `mode` | `string` | ❌ | `"RECALL"` | Enum: `RECALL`, `RECALL_LLM_RERANK`, `SYNTHESIZE`, `REFLECT`, `CHALLENGE`, `EXPAND` |
| `content_type` | `string` | ❌ | `null` | Restrict retrieval to type |
| `threshold` | `float` | ❌ | `0.45` | Cosine distance threshold. App layer chuyển sang similarity floor theo `similarity = 1 - threshold` |

> **Production Retrieval Gate (v0.3.x):** Sau khi lấy Top-K candidates từ SQL, app layer áp 4 lớp:
> absolute similarity floor (`>= 0.55`), mode-specific floor (RECALL 0.65, RECALL_LLM_RERANK 0.60, SYNTHESIZE 0.60, REFLECT 0.55, CHALLENGE 0.60, EXPAND 0.52),
> score-gap filter (`top_final_score - final_score <= 0.15`) và mode hard cap (RECALL 5, RECALL_LLM_RERANK 12, SYNTHESIZE 8, REFLECT 8, CHALLENGE 4, EXPAND 10).  
> **Exposure-Aware Diversity (v0.3.x):** /query adds `+0.02 * (1 / (1 + retrieval_count))`, chỉ áp dụng khi `similarity >= 0.70`, bonus cap tối đa `0.02`.
> `retrieval_count` được suy ra từ `reasoning_logs.memory_ids` (không thêm cột DB mới).
> **Query Replay Cooldown (v0.3.x):** với `RECALL`/`RECALL_LLM_RERANK`/`CHALLENGE`, nếu user lặp lại đúng cùng câu hỏi, memory đã dùng ở vài log gần nhất sẽ bị đẩy xuống sau để tăng cơ hội cho memory khác trong cùng cụm liên quan.
> **Lexical Anchor (v0.3.x):** ở `RECALL`, `RECALL_LLM_RERANK` và `CHALLENGE`, hệ thống cộng thêm lexical bonus nhỏ khi memory chứa keyword trực tiếp từ query.
> Với `RECALL`, nếu sau gate không còn memory phù hợp, API trả trực tiếp: `"Không có memory liên quan đến câu hỏi này."`
> Với `RECALL`, nếu có memory phù hợp, API trả deterministic danh sách `[Memory N]` (không gọi LLM để diễn đạt lại).
> Với `RECALL_LLM_RERANK`, hệ thống gọi LLM để chọn memory index phù hợp nhất từ candidate pool, sau đó vẫn trả deterministic memory gốc (LLM không được rewrite nội dung memory).
> **AI_Chat mapping:** nút `RECALL+` trong UI tương ứng mode API `RECALL_LLM_RERANK`.

#### Modes

| Mode | Hành Vi | External Knowledge |
|---|---|---|
| `RECALL` | Trả nguyên văn memory liên quan. Không suy diễn, không thêm bớt | ❌ NEVER |
| `RECALL_LLM_RERANK` | LLM re-rank candidate memories theo ngữ cảnh query, sau đó trả memory gốc dạng deterministic | ❌ NEVER |
| `SYNTHESIZE` | Tổng hợp nhiều memory thành structured summary | ❌ NEVER |
| `REFLECT` | Phân tích evolution tư duy, nhận diện pattern thay đổi | ❌ NEVER |
| `CHALLENGE` | Chỉ ra mâu thuẫn giữa các memory, logic yếu, gaps | ❌ NEVER |
| `EXPAND` | Mở rộng kiến thức, memory + external kết hợp | ✅ ALWAYS |

> **V1.1 Epistemic Rule:** External knowledge chỉ được dùng ở `EXPAND` mode. Mode = permission. Xem [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) Section 5.

**Response (200 OK):**

```json
{
    "response": "Dựa trên các memory, tư duy của mày về AI đã thay đổi...",
    "mode": "REFLECT",
    "memory_used": [
        "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "b2c3d4e5-f6a7-8901-bcde-f12345678901"
    ],
    "token_usage": {
        "prompt_tokens": 850,
        "completion_tokens": 320,
        "total": 1170
    },
    "external_knowledge_used": false,
    "latency_ms": 2340
}
```

| Response Field | Ghi Chú |
|---|---|
| `response` | LLM-generated answer |
| `memory_used` | List UUID của memory đã dùng làm context |
| `token_usage` | LLM token consumption (cả OpenAI lẫn LM Studio) |
| `external_knowledge_used` | `true` nếu LLM dùng external knowledge |
| `latency_ms` | Toàn bộ pipeline latency |

---

## 4. Health Check

### GET `/health`

```json
{
    "status": "ok"
}
```

---

## 5. Error Response Format

Tất cả errors đều trả về format chuẩn. **Không bao giờ leak stacktrace.**

```json
{
    "error": {
        "code": "MEMORY_NOT_FOUND",
        "message": "Memory with ID 'abc...' not found.",
        "correlation_id": "req-123e4567-e89b-12d3-a456-426614174000"
    }
}
```

### Error Codes

| Code | HTTP Status | Mô Tả |
|---|---|---|
| `MEMORY_NOT_FOUND` | `404` | Memory UUID không tồn tại |
| `DUPLICATE_MEMORY` | `409` | Trùng checksum SHA256 |
| `EMBEDDING_FAILED` | `503` | Embedding service lỗi |
| `LLM_TIMEOUT` | `504` | LLM request timeout |
| `LLM_ERROR` | `503` | LLM request thất bại |
| `RETRIEVAL_ERROR` | `500` | Retrieval pipeline lỗi |
| `TOKEN_BUDGET_EXCEEDED` | `422` | Token budget vượt ngưỡng |
| `INVALID_MODE` | `422` | Mode không hợp lệ (phải là RECALL/RECALL_LLM_RERANK/SYNTHESIZE/REFLECT/CHALLENGE/EXPAND) |
| `INTERNAL_ERROR` | `500` | Unhandled error (no detail) |

---

## 6. Headers

### Request Headers

| Header | Ghi Chú |
|---|---|
| `Content-Type` | `application/json` (required) |
| `X-Correlation-ID` | Optional — nếu không gửi, server tự generate |

### Response Headers

| Header | Ghi Chú |
|---|---|
| `X-Correlation-ID` | Unique request ID cho log correlation |

---

## 7. cURL Examples

### Insert memory

```bash
curl -X POST http://localhost:8000/api/v1/memory \
  -H "Content-Type: application/json" \
  -d '{
    "raw_text": "LoRA cho phép fine-tune model lớn với ít tài nguyên.",
    "content_type": "note",
    "importance_score": 0.8,
    "metadata": {"tags": ["ai", "lora"]}
  }'
```

### Search

```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "fine-tuning techniques",
    "limit": 10
  }'
```

### Query with RECALL mode

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Tao từng viết gì về LoRA?",
    "mode": "RECALL"
  }'
```

### Query with RECALL_LLM_RERANK mode

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "những câu nào thật sự liên quan đến chủ đề phước lành",
    "mode": "RECALL_LLM_RERANK"
  }'
```

### Query with REFLECT mode

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Tư duy của tao về AI thay đổi thế nào?",
    "mode": "REFLECT"
  }'
```

### Query with SYNTHESIZE mode

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Tổng hợp những gì tao biết về LoRA",
    "mode": "SYNTHESIZE"
  }'
```

### Query with EXPAND mode (external knowledge)

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "So sánh LoRA với QLoRA theo kiến thức mới nhất",
    "mode": "EXPAND"
  }'
```

### Archive memory

```bash
curl -X PATCH http://localhost:8000/api/v1/memory/{id}/archive \
  -H "Content-Type: application/json" \
  -d '{"is_archived": true, "exclude_from_retrieval": true}'
```
