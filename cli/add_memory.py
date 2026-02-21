"""
CLI Add Memory — Interactive memory ingestion.

Entry point: `python -m cli.add_memory`
Called via: `.\ai add`

Flow:
  1. Enter raw_text (multiline, end with ::end)
  2. Select content_type
  3. Person flow (optional)
  4. Select tags
  5. metadata.type (if content_type == log)
  6. importance_score
  7. Confirmation summary
  8. MemoryService.save_memory()
  9. Print result

Architecture:
  - ONE session created in run_add(), passed to all helpers
  - Builds MemoryCreateRequest, catches Pydantic validation errors
  - Auto-sets metadata.source = "cli"
"""

import asyncio
import sys
from typing import Any, Optional

from pydantic import ValidationError

from app.db.session import AsyncSessionLocal
from app.memory.repository import MemoryRepository
from app.memory.service import MemoryService
from app.schemas.memory import MemoryCreateRequest
from cli.person_helpers import (
    get_existing_person_names,
    normalize_person_name,
    suggest_person_name,
)
from cli.registry import ALL_TAGS, CONTENT_TYPE_MENU, TAG_GROUPS, TYPE_MENU


# ─── Display Helpers ──────────────────────────────────────────────────────────

def _header(text: str) -> None:
    print(f"\n  {'─' * 50}")
    print(f"  {text}")
    print(f"  {'─' * 50}")


def _menu_select(title: str, options: list[tuple[str, str]], allow_skip: bool = False) -> Optional[str]:
    """Display numbered menu, return selected value or None if skipped."""
    print(f"\n  {title}")
    for i, (value, label) in enumerate(options, 1):
        print(f"    [{i}] {value:15s} — {label}")
    if allow_skip:
        print(f"    [0] Bỏ qua")

    while True:
        choice = input("  → Chọn số: ").strip()
        if allow_skip and choice == "0":
            return None
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx][0]
        except ValueError:
            pass
        print("  ⚠ Chọn không hợp lệ, thử lại.")


def _multi_select_tags() -> list[str]:
    """Multi-select tags from grouped registry. Returns list of selected tag strings."""
    print("\n  🏷 Chọn Tags (nhập số, cách nhau bởi dấu phẩy)")
    print("  Nhấn Enter để bỏ qua.\n")

    flat: list[tuple[int, str, str]] = []
    idx = 1
    for group_name, tags in TAG_GROUPS.items():
        print(f"  [{group_name}]")
        for tag, label in tags:
            print(f"    [{idx:2d}] {tag:12s} — {label}")
            flat.append((idx, tag, label))
            idx += 1
        print()

    raw = input("  → Tags (vd: 1,3,5): ").strip()
    if not raw:
        return []

    selected: list[str] = []
    for part in raw.split(","):
        part = part.strip()
        try:
            num = int(part)
            for i, tag, _ in flat:
                if i == num:
                    selected.append(tag)
                    break
        except ValueError:
            pass

    return list(dict.fromkeys(selected))  # dedupe, preserve order


def _read_multiline() -> str:
    """Read multiline input, terminated by ::end on its own line."""
    print("  Nhập nội dung (gõ ::end để kết thúc):")
    lines: list[str] = []
    while True:
        line = input("  > ")
        if line.strip() == "::end":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _ask_yes_no(question: str, default: bool = False) -> bool:
    """Ask a yes/no question. Returns bool."""
    suffix = "[Y/n]" if default else "[y/N]"
    answer = input(f"  {question} {suffix}: ").strip().lower()
    if not answer:
        return default
    return answer in ("y", "yes", "có", "co")


# ─── Main Flow ────────────────────────────────────────────────────────────────

async def run_add() -> None:
    """Full interactive add memory flow. Single session, single transaction."""
    _header("AI Person — Add Memory")
    print("  Memory Contract V1 • source=cli\n")

    # ── Step 1: raw_text ──
    raw_text = _read_multiline()
    if not raw_text:
        print("\n  ⚠ Nội dung trống. Hủy.")
        return

    # ── Step 2: content_type ──
    content_type = _menu_select("Chọn content_type:", CONTENT_TYPE_MENU)
    if content_type is None:
        print("\n  ⚠ Phải chọn content_type. Hủy.")
        return

    # ── Step 3: Person flow ──
    person_name: Optional[str] = None
    metadata_tags: list[str] = []

    async with AsyncSessionLocal() as session:
        repo = MemoryRepository(session)
        service = MemoryService(session)

        if _ask_yes_no("Memory này về một người cụ thể?"):
            # Get existing names from DB
            existing_names = await get_existing_person_names(repo)

            # Auto-suggest if raw_text contains known name
            suggestions = suggest_person_name(raw_text, existing_names)
            if suggestions:
                print(f"\n  💡 Phát hiện tên trong nội dung: {', '.join(suggestions)}")

            if existing_names:
                print(f"\n  👥 Người đã có trong hệ thống:")
                for i, name in enumerate(existing_names, 1):
                    print(f"    [{i}] {name}")
                print(f"    [0] Nhập tên mới")

                choice = input("  → Chọn: ").strip()
                if choice == "0" or not choice:
                    raw_name = input("  → Nhập tên: ").strip()
                    if raw_name:
                        person_name = normalize_person_name(raw_name)
                else:
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(existing_names):
                            person_name = existing_names[idx]
                    except ValueError:
                        pass
            else:
                raw_name = input("  → Nhập tên người: ").strip()
                if raw_name:
                    person_name = normalize_person_name(raw_name)

            if person_name:
                metadata_tags.append("person")
                print(f"  ✅ person_name = {person_name}")

        # ── Step 4: Tags ──
        selected_tags = _multi_select_tags()
        metadata_tags.extend(t for t in selected_tags if t not in metadata_tags)

        # ── Step 5: metadata.type (log only) ──
        metadata_type: Optional[str] = None
        if content_type == "log":
            metadata_type = _menu_select("Loại log:", TYPE_MENU, allow_skip=True)

        # ── Step 6: importance_score ──
        importance_score: Optional[float] = None
        score_input = input("\n  importance_score (0.0–1.0, Enter=bỏ qua): ").strip()
        if score_input:
            try:
                importance_score = float(score_input)
            except ValueError:
                print("  ⚠ Không hợp lệ, bỏ qua importance_score.")

        # ── Build metadata ──
        metadata: dict[str, Any] = {"source": "cli"}
        if metadata_tags:
            metadata["tags"] = metadata_tags
        if metadata_type:
            metadata["type"] = metadata_type
        if person_name:
            metadata["extra"] = {"person_name": person_name}

        # ── Step 7: Confirmation ──
        _header("Xác nhận trước khi lưu")
        print(f"  content_type:      {content_type}")
        print(f"  importance_score:  {importance_score or '(none)'}")
        print(f"  metadata:          {metadata}")
        print(f"  raw_text:")
        for line in raw_text.split("\n")[:5]:
            print(f"    {line}")
        if raw_text.count("\n") > 4:
            print(f"    ... ({raw_text.count(chr(10)) + 1} dòng)")

        if not _ask_yes_no("Lưu memory này?", default=True):
            print("\n  ❌ Đã hủy.")
            return

        # ── Step 8: Build request + call service ──
        try:
            request = MemoryCreateRequest(
                raw_text=raw_text,
                content_type=content_type,
                importance_score=importance_score,
                metadata=metadata,
            )
        except ValidationError as e:
            print(f"\n  ❌ Validation error:")
            for err in e.errors():
                field = " → ".join(str(loc) for loc in err["loc"])
                print(f"     {field}: {err['msg']}")
            return

        try:
            result = await service.save_memory(request)
        except Exception as e:
            print(f"\n  ❌ Lỗi khi lưu: {e}")
            return

        # ── Step 9: Result ──
        _header("✅ Memory đã lưu!")
        print(f"  ID:        {result.id}")
        print(f"  Checksum:  {result.checksum[:16]}...")
        print(f"  Type:      {result.content_type}")
        print(f"  📦 Embedding job created — worker sẽ xử lý tự động.")
        print()


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        asyncio.run(run_add())
    except KeyboardInterrupt:
        print("\n\n  Đã hủy.")
        sys.exit(0)
