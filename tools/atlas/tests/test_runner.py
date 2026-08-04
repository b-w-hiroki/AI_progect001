from __future__ import annotations

from pathlib import Path

from atlas.models import Check, Lesson, Status
from atlas.runner import run_lesson


def check(check_id: str, check_type: str, **params: object) -> Check:
    return Check(id=check_id, title=check_id, type=check_type, params=params, hints=["ヒント"])


def lesson(*checks: Check) -> Lesson:
    return Lesson(
        id="demo",
        title="デモ",
        summary="説明",
        target_dir="labs/demo",
        checks=list(checks),
    )


def test_runs_every_check_even_after_a_failure(tmp_path: Path) -> None:
    """1件失敗しても打ち切らない。残り全部の状況を一度に見せるため。"""
    (tmp_path / "b.txt").write_text("", encoding="utf-8")
    report = run_lesson(
        lesson(check("a", "file_exists", path="a.txt"), check("b", "file_exists", path="b.txt")),
        tmp_path,
    )
    assert [r.status for r in report.results] == [Status.FAILED, Status.PASSED]
    assert report.passed_count == 1


def test_complete_when_all_pass(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("", encoding="utf-8")
    report = run_lesson(lesson(check("a", "file_exists", path="a.txt")), tmp_path)
    assert report.complete


def test_skipped_check_blocks_completion(tmp_path: Path) -> None:
    """判定できていない項目を合格扱いにしない。"""
    (tmp_path / "a.txt").write_text("", encoding="utf-8")
    report = run_lesson(
        lesson(
            check("a", "file_exists", path="a.txt"),
            check("s", "command_succeeds", command=["atlas-no-such-binary-xyz"]),
        ),
        tmp_path,
    )
    assert report.passed_count == 1
    assert len(report.skipped) == 1
    assert not report.complete


def test_bad_lesson_definition_becomes_skipped_not_failed(tmp_path: Path) -> None:
    """レッスン側の不備を、学習者の失敗として記録しない。"""
    report = run_lesson(lesson(check("x", "no_such_type")), tmp_path)
    assert report.results[0].status is Status.SKIPPED
    assert "レッスン定義の不備" in report.results[0].detail


def test_missing_target_dir_skips_everything(tmp_path: Path) -> None:
    report = run_lesson(lesson(check("a", "file_exists", path="a.txt")), tmp_path / "nope")
    assert report.results[0].status is Status.SKIPPED
    assert not report.complete
