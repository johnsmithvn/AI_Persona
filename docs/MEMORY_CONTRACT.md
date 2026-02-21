# Memory Contract V1 — AI Person

> **Version:** v0.3.0  
> **Last Updated:** 2026-02-21  
> **Status:** Active — mọi data import phải tuân theo contract này

---

## I. Triết Lý Thiết Kế

1. `raw_text` là nguồn sự thật — được embed để semantic search.
2. `content_type` = hình thái dữ liệu (ít và cố định).
3. `metadata.type` = logic đặc biệt (rất hạn chế).
4. `metadata.tags` = phân nhóm nội dung (registry cố định).
5. `metadata.extra.person_name` = dùng cho memory về người (chỉ filter, không structured DB).

---

## II. Top-Level Fields

| Field | Type | Bắt buộc | Mô tả |
|---|---|---|---|
| `raw_text` | `string` | ✅ | Nội dung đầy đủ, được embed để semantic search. **Bất biến** |
| `content_type` | `string` | ✅ | Phân loại hình thái. **6 giá trị cố định** (xem §III) |
| `importance_score` | `float` | ❌ | `0.0–1.0`. Ảnh hưởng ranking retrieval |
| `metadata` | `object` | ❌ | Thông tin phụ, không ảnh hưởng embedding trực tiếp (xem §IV) |

---

## III. `content_type` Registry (6 giá trị — KHÔNG THÊM)

| Giá trị | Dùng khi | Ý nghĩa hệ thống |
|---|---|---|
| `note` | Ghi chú chung | Fallback trung tính |
| `conversation` | Chat, bình luận | Nội dung dạng đối thoại |
| `reflection` | Quan điểm cá nhân | Phục vụ REFLECT mode |
| `idea` | Ý tưởng | Có thể phát triển thêm |
| `article` | Kiến thức, link, repo, video, nhạc | Nội dung học được từ bên ngoài |
| `log` | Dữ kiện có cấu trúc | Chi tiêu, todo, tracking |

> ⚠️ Các loại cũ (`quote`, `repo`, `pdf`, `transcript`) đã được gộp vào `note` hoặc `article`.

---

## IV. `metadata` JSON Structure

```json
{
  "tags": ["ai", "code"],
  "type": "expense",
  "source": "cli",
  "source_urls": ["https://..."],
  "extra": {
    "person_name": "Linh"
  }
}
```

Tất cả sub-fields đều **optional**.

---

## V. Metadata Fields Chi Tiết

### 1. `tags` — Registry Cố Định

Dùng để phân nhóm, filter. Một memory có thể có nhiều tags.

#### A. Domain Tags

| Tag | Dùng khi |
|---|---|
| `ai` | Nội dung AI |
| `code` | Lập trình |
| `life` | Đời sống |
| `finance` | Tài chính |
| `health` | Sức khỏe |
| `startup` | Khởi nghiệp |
| `product` | Sản phẩm |
| `psychology` | Tâm lý |

#### B. Format Tags

| Tag | Dùng khi |
|---|---|
| `video` | Nội dung video |
| `music` | Nhạc |
| `repo` | GitHub |
| `file` | Import file |
| `article` | Bài viết |

#### C. Style Tags

| Tag | Dùng khi |
|---|---|
| `funny` | Nội dung hài |
| `deep` | Sâu sắc |
| `technical` | Kỹ thuật |
| `practical` | Ứng dụng |
| `random` | Không rõ nhóm |

#### D. System Tags

| Tag | Dùng khi |
|---|---|
| `knowledge` | Nội dung học được |
| `lesson` | Bài học |
| `important` | Memory quan trọng |
| `person` | Memory về con người |

---

### 2. `metadata.type` — Logic Đặc Biệt (Rất Hạn Chế)

Chỉ dùng khi cần xử lý logic riêng (tổng hợp, track trạng thái).

| Giá trị | Dùng khi | Vì sao cần |
|---|---|---|
| `expense` | Chi tiêu | Có thể tổng hợp số liệu |
| `todo` | Việc cần làm | Có thể track trạng thái |
| `bookmark` | Lưu link chưa đọc | Filter riêng |

> ⚠️ Không dùng `video`, `music`, `repo` ở đây — dùng `tags` thay thế.

---

### 3. `metadata.source`

Nguồn gốc data — thay thế top-level `source_type` column cũ.

| Giá trị | Dùng khi |
|---|---|
| `cli` | Add từ CLI |
| `telegram` | Add từ bot |
| `import` | Import file |
| `api` | Qua API trực tiếp |

---

### 4. `metadata.source_urls`

Array chứa link liên quan đến memory.

```json
{
  "source_urls": [
    "https://youtube.com/watch?v=abc123",
    "https://github.com/user/repo"
  ]
}
```

---

### 5. `metadata.extra.person_name`

Dùng khi memory về người. Chứa **tên chuẩn** để filter.

```json
{
  "extra": {
    "person_name": "Linh"
  }
}
```

> ⚠️ Không thêm `location`, `allergy`, `company` làm field riêng — tất cả nằm trong `raw_text`.

---

## VI. Ví Dụ Thực Tế

### 🎥 Video mẹo vặt

```json
{
  "raw_text": "Video mẹo vặt hay: cách bảo quản rau trong tủ lạnh lâu hơn",
  "content_type": "article",
  "importance_score": 0.4,
  "metadata": {
    "tags": ["life", "video", "practical"],
    "source": "telegram",
    "source_urls": ["https://youtube.com/watch?v=abc123"]
  }
}
```

### 💸 Chi tiêu

```json
{
  "raw_text": "Mua cà phê Highland 45k",
  "content_type": "log",
  "importance_score": 0.3,
  "metadata": {
    "tags": ["finance"],
    "type": "expense",
    "source": "cli",
    "extra": {
      "amount": 45000,
      "currency": "VND"
    }
  }
}
```

### 👩 Memory về người

```json
{
  "raw_text": "Linh dị ứng hải sản, thích ăn bún bò, làm ở FPT",
  "content_type": "note",
  "importance_score": 0.8,
  "metadata": {
    "tags": ["life", "person"],
    "source": "cli",
    "extra": {
      "person_name": "Linh"
    }
  }
}
```

### 🧠 Ý tưởng

```json
{
  "raw_text": "Làm app quản lý chi tiêu bằng voice input, dùng Whisper + GPT phân loại tự động",
  "content_type": "idea",
  "importance_score": 0.9,
  "metadata": {
    "tags": ["startup", "ai", "product"],
    "source": "cli"
  }
}
```

---

## VII. Nguyên Tắc Vàng

1. **Mỗi fact = một memory riêng.** Không nhét nhiều fact khác loại vào 1 record.
2. `person_name` chỉ dùng để filter. Chi tiết về người nằm trong `raw_text`.
3. `tags` chỉ dùng để phân nhóm — không ảnh hưởng logic xử lý.
4. **Không thêm `content_type` mới.** Dùng `tags` hoặc `metadata.extra` để mở rộng.
5. **Không thêm field top-level mới.** Mở rộng qua `metadata.extra`.
6. `metadata.type` chỉ dùng cho logic đặc biệt (expense, todo, bookmark).
7. Giới hạn `metadata` JSON < 4KB.

---

## VIII. Retrieval & Filter

### Filter theo tag

```
POST /api/v1/search
{
  "query": "video hay",
  "metadata_filter": {"tags": ["video"]}
}
```

### Filter theo người

```
POST /api/v1/search
{
  "query": "Linh thích ăn gì",
  "metadata_filter": {"extra": {"person_name": "Linh"}}
}
```

### Filter theo loại đặc biệt

```
POST /api/v1/search
{
  "query": "tháng này tiêu bao nhiêu",
  "metadata_filter": {"type": "expense"}
}
```

> **Lưu ý V1:** Hệ thống chưa tự detect entity từ câu hỏi. Client phải truyền `metadata_filter` thủ công. Entity-aware retrieval là V2 feature.

---

## IX. Tài Liệu Liên Quan

| Tài liệu | Mô tả |
|---|---|
| [DATA_DESIGN.md](DATA_DESIGN.md) | Database schema, indexes, SQL |
| [API_DOCS.md](API_DOCS.md) | API endpoints, request/response |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | Kiến trúc tổng thể |
