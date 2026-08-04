from __future__ import annotations

from pathlib import Path

from atlas.progress import Progress


def test_hints_are_revealed_one_at_a_time(tmp_path: Path) -> None:
    progress = Progress(tmp_path)
    assert progress.reveal_next_hint("l1", "c1", total=3) == 0
    assert progress.reveal_next_hint("l1", "c1", total=3) == 1
    assert progress.reveal_next_hint("l1", "c1", total=3) == 2
    # 開示し尽くしたら None
    assert progress.reveal_next_hint("l1", "c1", total=3) is None


def test_hint_state_survives_a_reload(tmp_path: Path) -> None:
    first = Progress(tmp_path)
    first.reveal_next_hint("l1", "c1", total=3)
    first.save()

    second = Progress(tmp_path)
    assert second.revealed_count("l1", "c1") == 1
    assert second.reveal_next_hint("l1", "c1", total=3) == 1


def test_hint_counts_are_independent_per_check(tmp_path: Path) -> None:
    progress = Progress(tmp_path)
    progress.reveal_next_hint("l1", "c1", total=2)
    assert progress.revealed_count("l1", "c2") == 0


def test_completion_timestamp_is_kept_from_the_first_success(tmp_path: Path) -> None:
    progress = Progress(tmp_path)
    progress.record_attempt("l1", complete=False)
    progress.record_attempt("l1", complete=True)
    first_completed = progress.for_lesson("l1").completed_at
    progress.record_attempt("l1", complete=True)

    entry = progress.for_lesson("l1")
    assert entry.attempts == 3
    assert entry.completed_at == first_completed


def test_corrupt_progress_file_does_not_block_grading(tmp_path: Path) -> None:
    """進捗が壊れていても採点は続けられるべき。空から始める。"""
    path = tmp_path / ".atlas" / "progress.json"
    path.parent.mkdir(parents=True)
    path.write_text("{ これはJSONではない", encoding="utf-8")

    progress = Progress(tmp_path)
    assert progress.for_lesson("l1").attempts == 0

    progress.record_attempt("l1", complete=False)
    progress.save()
    assert Progress(tmp_path).for_lesson("l1").attempts == 1
