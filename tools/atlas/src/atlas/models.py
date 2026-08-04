"""レッスンと採点結果のデータ構造。

レッスンは**データ**（YAML）として持つ。実装コードを書かずにレッスンを追加できることが、
教材ツールとして最も重要な性質。将来Web UIを被せる場合も、ここが唯一の正になる。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class Status(StrEnum):
    """採点結果の状態。"""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"  # 前提が満たせず判定不能（例: AWS認証情報が無い）


@dataclass(frozen=True)
class Check:
    """1つの検証項目。

    hints は**段階的**に並べる。最初は方向だけ示し、最後でも手順を示すに留めて、
    完成したコードそのものは書かない。答えを写させないため。
    """

    id: str
    title: str
    type: str
    params: dict[str, object] = field(default_factory=dict)
    hints: list[str] = field(default_factory=list)
    requires_aws: bool = False

    def hint_count(self) -> int:
        return len(self.hints)


@dataclass(frozen=True)
class Lesson:
    """1レッスン。"""

    id: str
    title: str
    summary: str
    target_dir: str
    objectives: list[str] = field(default_factory=list)
    checks: list[Check] = field(default_factory=list)
    reference: str | None = None

    def find_check(self, check_id: str) -> Check | None:
        return next((c for c in self.checks if c.id == check_id), None)


@dataclass(frozen=True)
class CheckResult:
    """1項目の採点結果。"""

    check: Check
    status: Status
    detail: str

    @property
    def passed(self) -> bool:
        return self.status is Status.PASSED


@dataclass(frozen=True)
class LessonReport:
    """レッスン全体の採点結果。"""

    lesson: Lesson
    target_dir: Path
    results: list[CheckResult]

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.status is Status.PASSED)

    @property
    def failed(self) -> list[CheckResult]:
        return [r for r in self.results if r.status is Status.FAILED]

    @property
    def skipped(self) -> list[CheckResult]:
        return [r for r in self.results if r.status is Status.SKIPPED]

    @property
    def complete(self) -> bool:
        """スキップは未達成として扱う。判定できていないものを合格にしない。"""
        return bool(self.results) and all(r.passed for r in self.results)
