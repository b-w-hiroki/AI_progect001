from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from atlas.loader import LessonError, load_lesson_file, load_lessons, parse_lesson


def a_check(**overrides: Any) -> dict[str, Any]:
    return {
        "id": "c1",
        "title": "ファイルがある",
        "type": "file_exists",
        "path": "main.tf",
        "hints": ["まず main.tf を作ります"],
        **overrides,
    }


def a_lesson(**overrides: Any) -> dict[str, Any]:
    return {
        "id": "demo",
        "title": "デモ",
        "summary": "説明",
        "target_dir": "labs/demo",
        "checks": [a_check()],
        **overrides,
    }


MINIMAL = a_lesson()


def write_lesson(directory: Path, name: str, data: object) -> Path:
    path = directory / f"{name}.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def test_parses_minimal_lesson() -> None:
    lesson = parse_lesson(MINIMAL, "test")
    assert lesson.id == "demo"
    assert len(lesson.checks) == 1
    # type に無い余りのキーは params に入る
    assert lesson.checks[0].params["path"] == "main.tf"


def test_check_without_hints_is_rejected() -> None:
    with pytest.raises(LessonError, match="hints"):
        parse_lesson(a_lesson(checks=[a_check(hints=[])]), "test")


def test_lesson_without_checks_is_rejected() -> None:
    with pytest.raises(LessonError, match="checks"):
        parse_lesson(a_lesson(checks=[]), "test")


def test_duplicate_check_ids_are_rejected() -> None:
    with pytest.raises(LessonError, match="重複"):
        parse_lesson(a_lesson(checks=[a_check(), a_check()]), "test")


def test_missing_title_is_rejected() -> None:
    data = {k: v for k, v in a_lesson().items() if k != "title"}
    with pytest.raises(LessonError, match="title"):
        parse_lesson(data, "test")


def test_id_must_match_filename(tmp_path: Path) -> None:
    path = write_lesson(tmp_path, "other-name", MINIMAL)
    with pytest.raises(LessonError, match="一致しません"):
        load_lesson_file(path)


def test_load_lessons_sorted_by_filename(tmp_path: Path) -> None:
    write_lesson(tmp_path, "02-second", a_lesson(id="02-second"))
    write_lesson(tmp_path, "01-first", a_lesson(id="01-first"))
    lessons = load_lessons(tmp_path)
    assert [x.id for x in lessons] == ["01-first", "02-second"]


def test_empty_lessons_dir_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(LessonError):
        load_lessons(tmp_path)


def test_broken_yaml_is_reported_as_lesson_error(tmp_path: Path) -> None:
    path = tmp_path / "demo.yaml"
    path.write_text("id: [unclosed\n", encoding="utf-8")
    with pytest.raises(LessonError, match="YAML"):
        load_lesson_file(path)


def test_shipped_lessons_are_valid() -> None:
    """同梱のレッスンが常に読み込めることを保証する。"""
    lessons_dir = Path(__file__).resolve().parent.parent / "lessons"
    lessons = load_lessons(lessons_dir)
    assert lessons
    for lesson in lessons:
        assert lesson.checks
        for check in lesson.checks:
            assert check.hints
