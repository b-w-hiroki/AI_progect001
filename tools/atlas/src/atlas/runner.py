"""レッスンの採点実行。"""

from __future__ import annotations

from pathlib import Path

from atlas.checks import CheckError, run_check
from atlas.models import CheckResult, Lesson, LessonReport, Status


def run_lesson(lesson: Lesson, target_dir: Path) -> LessonReport:
    """レッスンの全検証を実行する。

    1項目の失敗で打ち切らない。学習者は「どこまでできていて何が残っているか」を
    一度に知りたいため、全項目を最後まで走らせる。
    """
    results: list[CheckResult] = []

    for check in lesson.checks:
        if not target_dir.is_dir():
            results.append(
                CheckResult(
                    check=check,
                    status=Status.SKIPPED,
                    detail=f"対象ディレクトリがありません: {target_dir}",
                )
            )
            continue

        try:
            results.append(run_check(check, target_dir))
        except CheckError as exc:
            # レッスン定義の不備。学習者の失敗と区別できるよう SKIPPED にする
            results.append(
                CheckResult(
                    check=check,
                    status=Status.SKIPPED,
                    detail=f"レッスン定義の不備: {exc}",
                )
            )

    return LessonReport(lesson=lesson, target_dir=target_dir, results=results)
