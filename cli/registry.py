"""
CLI Registry — Single source of truth for interactive menu choices.

All registries mirror MEMORY_CONTRACT.md. If the contract changes, update here.
CLI modules import from this file — never hardcode values elsewhere.
"""

from app.schemas.memory import VALID_CONTENT_TYPES

# ─── Content Type Menu ────────────────────────────────────────────────────────
# Ordered for UX: most common first.

CONTENT_TYPE_MENU: list[tuple[str, str]] = [
    ("note",         "Ghi chú chung"),
    ("conversation", "Chat, bình luận, đối thoại"),
    ("reflection",   "Quan điểm cá nhân, suy ngẫm"),
    ("idea",         "Ý tưởng có thể phát triển"),
    ("article",      "Kiến thức, link, repo, video, nhạc"),
    ("log",          "Dữ kiện: chi tiêu, todo, tracking"),
]

# Validate registry matches schema
assert {ct for ct, _ in CONTENT_TYPE_MENU} == VALID_CONTENT_TYPES, \
    "CONTENT_TYPE_MENU out of sync with VALID_CONTENT_TYPES"


# ─── Tag Registry ────────────────────────────────────────────────────────────
# Grouped by category for display. Flat list for storage.

TAG_GROUPS: dict[str, list[tuple[str, str]]] = {
    "Domain": [
        ("ai",         "AI / Machine Learning"),
        ("code",       "Lập trình"),
        ("life",       "Đời sống"),
        ("finance",    "Tài chính"),
        ("health",     "Sức khỏe"),
        ("startup",    "Khởi nghiệp"),
        ("product",    "Sản phẩm"),
        ("psychology", "Tâm lý"),
    ],
    "Format": [
        ("video",   "Video"),
        ("music",   "Nhạc"),
        ("repo",    "GitHub repo"),
        ("file",    "Import file"),
        ("article", "Bài viết"),
    ],
    "Style": [
        ("funny",     "Hài hước"),
        ("deep",      "Sâu sắc"),
        ("technical", "Kỹ thuật"),
        ("practical", "Ứng dụng thực tế"),
        ("random",    "Không rõ nhóm"),
    ],
    "System": [
        ("knowledge", "Kiến thức học được"),
        ("lesson",    "Bài học rút ra"),
        ("important", "Quan trọng"),
        ("person",    "Memory về con người"),
    ],
}

# Flat list of all valid tags
ALL_TAGS: list[str] = [tag for group in TAG_GROUPS.values() for tag, _ in group]


# ─── Metadata Type (special logic) ───────────────────────────────────────────
# Only used when content_type == "log"

TYPE_MENU: list[tuple[str, str]] = [
    ("expense",  "Chi tiêu"),
    ("todo",     "Việc cần làm"),
    ("bookmark", "Lưu link chưa đọc"),
]
