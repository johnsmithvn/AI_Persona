# AI Core — Memory-First Personal Intelligence

## 1. Why This Exists

Tôi hay quên.

Tôi đọc một comment hay, lưu một repo thú vị,
viết một reflection sâu sắc.
Vài tuần sau, tôi không còn nhớ mình từng nghĩ gì.

Tôi không cần một chatbot chung chung.
Tôi cần một hệ thống có thể:

- Nhớ điều tôi từng viết
- Nhớ kỹ năng tôi từng đọc
- Nhớ note ghi chú của tôi
- Nhắc nhở tôi
- Trả lời dựa vào những gì tôi đã note
- Trò truyện như một bản thân thứ 2, một tư duy của mình training
- Nhớ cách tôi từng suy nghĩ
- So sánh tôi của hôm nay với tôi của 3 tháng trước
- Chỉ ra khi tôi tự mâu thuẫn

Dự án này tồn tại để trở thành "bộ não thứ hai".

Không thay thế tôi.
Mà giúp tôi nhìn thấy chính mình rõ hơn.

---

## 2. Core Philosophy

> Base model chỉ là cái não.
> AI Core là cách cái não đó cư xử.

Hệ thống này không phải là một chatbot.
Nó là một Memory-First Personal Intelligence System.

### 2.1. Nguyên Tắc Lõi

1. **Memory là trung tâm.** Mọi câu trả lời mặc định phải dựa trên memory.
2. **Mode kiểm soát hành vi.** Mode là permission system, không phải AI khác nhau.
3. **External knowledge không tự động bật.** Chỉ bật khi mode cho phép (EXPAND only).
4. **Hệ thống phải phân biệt nguồn thông tin.** Memory-based vs External-based phải rõ ràng.
5. **Retrieval quyết định chất lượng nhiều hơn prompt.** 50% output quality nằm ở retrieval.
6. **LLM không được sửa hoặc ghi trực tiếp vào memory.** Chỉ đọc.
7. **Nếu không chắc → nói không chắc.** Không bịa kiến thức.

Đây là Memory-First AI.
Không phải Prompt-Engineered Chatbot.

---

## 3. Memory Principles

### 3.1 Append-Only

Raw text là bất biến.

Memory không được chỉnh sửa.
Chỉ có thể thêm mới.

Điều này đảm bảo:

- REFLECT trung thực.
- CHALLENGE có thể dựa trên dữ liệu gốc.
- Không bóp méo quá khứ.

### 3.2 Context Decay (Sự phai mờ ký ức)

Không phải mọi memory đều bình đẳng.

Hệ thống phải:

- Nhận diện độ quan trọng (importance_score).
- Ưu tiên ký ức gần và quan trọng.
- Cho phép ký ức ít quan trọng mờ dần trong retrieval.

Memory tồn tại.
Nhưng không phải memory nào cũng được ưu tiên ngang nhau.

### 3.3 Selective Forgetting

Mặc dù raw text là bất biến,
hệ thống phải có khả năng:

- Archive hoặc soft-delete memory.
- Loại bỏ chúng khỏi lớp retrieval.
- Vẫn giữ lại trong storage nếu cần audit.

Quên không phải là xóa khỏi tồn tại.
Mà là loại khỏi lớp suy luận.

---

## 4. Epistemic Boundary (Ranh Giới Nhận Thức)

Hệ thống phải phân biệt rõ:

1. Reasoning dựa trên memory cá nhân.
2. Reasoning dựa trên kiến thức bên ngoài.

Không được giả vờ rằng mọi suy luận đều xuất phát từ memory.
Minh bạch nguồn suy luận là bắt buộc.

### 4.1 External Knowledge Rules (V1.1 — 5-Mode)

| Rule | Chi Tiết |
|---|---|
| Default | **Memory-only.** LLM không tự ý dùng kiến thức ngoài |
| RECALL | External: ❌ NEVER |
| SYNTHESIZE | External: ❌ NEVER |
| REFLECT | External: ❌ NEVER |
| CHALLENGE | External: ❌ NEVER |
| EXPAND | External: ✅ **ALLOWED** — mode duy nhất cho phép |
| Logging | `external_knowledge_used` bắt buộc log trong `reasoning_logs` |
| Minh bạch | LLM phải nói rõ khi dùng external |

### 4.2 Source Decision Layer

```
Pipeline step 4 (trong ReasoningService):

if mode == "EXPAND":
    external_knowledge_used = True
else:
    external_knowledge_used = False
```

Clean. Không có conditional threshold. Mode = permission.

---

## 5. Behavior Modes (5-Mode System)

Modes không phải là AI khác nhau.
Chỉ là cấu hình quyền hạn khác nhau cho cùng một LLM.

### Mode Permission Matrix

| Mode | Mục Đích | Memory | External | Suy Diễn |
|---|---|---|---|---|
| **RECALL** | Trả nguyên văn memory | ✅ | ❌ | ❌ |
| **SYNTHESIZE** | Tổng hợp kiến thức đã ghi | ✅ | ❌ | ✅ (tổng hợp) |
| **REFLECT** | Phân tích evolution tư duy | ✅ | ❌ | ✅ (evolution) |
| **CHALLENGE** | Phản biện dựa trên memory | ✅ | ❌ | ✅ (phản biện) |
| **EXPAND** | Mở rộng kiến thức khi cần | ✅ | ✅ | ✅ (external) |

Memory luôn ưu tiên.
External chỉ bật khi mode = EXPAND.

### Ranh giới SYNTHESIZE vs REFLECT

| | SYNTHESIZE | REFLECT |
|---|---|---|
| Input | "Tổng hợp kiến thức về X" | "Tư duy của tao về X thay đổi thế nào?" |
| Focus | **Nội dung** — gom knowledge | **Quá trình** — phát hiện evolution |
| Output | Summary, structured knowledge | Timeline, pattern, contradiction |
| Ví dụ | "Tao biết gì về LoRA?" | "Quan điểm của tao về AI thay đổi ra sao?" |

### Citation Requirement

Bất kỳ mode nào sử dụng memory để suy luận
phải chỉ ra:

- Memory ID
hoặc
- Mốc thời gian

để người dùng có thể kiểm chứng.

---

## 6. Retrieval Intelligence

Retrieval không phải helper — nó là **trái tim hệ thống**.

50% chất lượng output phụ thuộc vào retrieval tìm đúng memory.

### Retrieval cần có:

1. **Semantic similarity** — cosine distance qua HNSW index (core)
2. **Ranking formula** — composite scoring: semantic + recency + importance
3. **Engagement boost** — memory được dùng nhiều nổi lên tự nhiên (V2: access_count)
4. **Anti-repeat** — session penalty: memory vừa dùng bị hạ rank (V2)
5. **Diversity guard** — cosine > 0.95 giữa 2 memory → giữ 1

### V1 Ranking:
```
final_score = 0.60 * semantic + 0.15 * recency + 0.25 * importance
```

### V2 Ranking (Planned):
```
final_score = 0.50 * semantic + 0.10 * recency + 0.20 * importance
             + 0.10 * engagement_boost + 0.10 * decay_score
```

Nếu retrieval tìm sai → reasoning sai.
Không có retrieval tốt thì LLM giỏi mấy cũng vô nghĩa.

---

## 7. Audit & Transparency

Mọi reasoning session phải để lại dấu vết:

| Audit Field | Mục Đích |
|---|---|
| `reasoning_logs` | Log toàn bộ query → response |
| `memory_used` | List UUID memory đã dùng |
| `external_knowledge_used` | Flag: LLM có dùng external không |
| `prompt_hash` | SHA256 hash prompt (detect drift) |
| `token_usage` | Cost tracking cho OpenAI |
| `latency_ms` | Performance monitoring |

Minh bạch không phải feature.
Nó là **yêu cầu kiến trúc**.

---

## 8. Architecture Flow

```
User Query
    │
    ▼
┌─────────────────┐
│  Retrieval       │ ← semantic search + ranking + diversity
│  (Trái Tim)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Mode Controller │ ← RECALL / SYNTHESIZE / REFLECT / CHALLENGE / EXPAND
│  (Permission)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Source Decision  │ ← EXPAND → external ON, others → OFF
│  Layer           │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Prompt Builder  │ ← system + mode_instruction + memory + query
│  + LLM Adapter   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Reasoning Log   │ ← audit trail
└─────────────────┘
```

Không có magic.
Không có rối.
Không có mode tự ý chọn memory.

---

## 9. Scope — Version 1

V1 tập trung vào:

- Single-user
- Text-based memory
- Semantic retrieval
- 5 modes: RECALL, SYNTHESIZE, REFLECT, CHALLENGE, EXPAND
- Logging cơ bản

Không làm:

- Multi-tenant
- Auth phức tạp
- Mobile app
- Auto mode classifier
- Streaming
- Microservices

Giữ hệ thống nhỏ và sạch.

---

## 10. Long-Term Direction (Not V1)

Có thể phát triển thêm:

- Engagement tracking (access_count, like_count, decay_score)
- Anti-repeat (session penalty cho retrieval)
- Memory compression layer
- Re-embedding toàn bộ DB
- LoRA để khóa hành vi
- Tool integration
- Multi-user memory partition

Nhưng chỉ sau khi V1 ổn định
và triết lý không bị phá vỡ.

---

## 11. Final Statement

Đây không phải sản phẩm AI đại trà.

Đây là hệ thống giúp tôi:

- Nhìn rõ lịch sử tư duy của mình.
- Nhận diện sự thay đổi.
- Chấp nhận mâu thuẫn.
- Suy nghĩ sâu hơn.

Nếu hệ thống bắt đầu:
- Bịa,
- Che giấu mâu thuẫn,
- Hoặc làm mượt sự thật,

thì nó đã đi sai hướng.