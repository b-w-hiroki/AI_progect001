"""学習進捗の保存。

**ヒントの開示状況をここで持つのが要点。** 一度に全ヒントを出さず、
学習者が要求するたびに1段ずつ開く。どこまで開いたかを覚えておく必要がある。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROGRESS_DIRNAME = ".atlas"
PROGRESS_FILENAME = "progress.json"


@dataclass
class LessonProgress:
    attempts: int = 0
    completed_at: str | None = None
    # check_id -> 開示済みヒント数
    hints_revealed: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempts": self.attempts,
            "completed_at": self.completed_at,
            "hints_revealed": dict(self.hints_revealed),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LessonProgress:
        raw_hints = data.get("hints_revealed", {})
        hints = {
            str(k): int(v)
            for k, v in (raw_hints.items() if isinstance(raw_hints, dict) else [])
            if isinstance(v, int)
        }
        completed = data.get("completed_at")
        return cls(
            attempts=int(data.get("attempts", 0)),
            completed_at=completed if isinstance(completed, str) else None,
            hints_revealed=hints,
        )


class Progress:
    """進捗ファイルの読み書き。壊れていても学習を止めない。"""

    def __init__(self, root: Path) -> None:
        self.path = root / PROGRESS_DIRNAME / PROGRESS_FILENAME
        self._lessons: dict[str, LessonProgress] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # 進捗が壊れていても採点は続けられる。空から始める
            return
        if not isinstance(data, dict):
            return
        for lesson_id, raw in data.get("lessons", {}).items():
            if isinstance(raw, dict):
                self._lessons[str(lesson_id)] = LessonProgress.from_dict(raw)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"lessons": {k: v.to_dict() for k, v in self._lessons.items()}}
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    def for_lesson(self, lesson_id: str) -> LessonProgress:
        return self._lessons.setdefault(lesson_id, LessonProgress())

    def all_lessons(self) -> dict[str, LessonProgress]:
        return dict(self._lessons)

    def record_attempt(self, lesson_id: str, *, complete: bool) -> None:
        entry = self.for_lesson(lesson_id)
        entry.attempts += 1
        if complete and entry.completed_at is None:
            entry.completed_at = datetime.now(UTC).isoformat(timespec="seconds")

    def reveal_next_hint(self, lesson_id: str, check_id: str, total: int) -> int | None:
        """次のヒントの添字を返す。すべて開示済みなら None。"""
        entry = self.for_lesson(lesson_id)
        revealed = entry.hints_revealed.get(check_id, 0)
        if revealed >= total:
            return None
        entry.hints_revealed[check_id] = revealed + 1
        return revealed

    def revealed_count(self, lesson_id: str, check_id: str) -> int:
        return self.for_lesson(lesson_id).hints_revealed.get(check_id, 0)
