"""レッスンYAMLの読み込みと検証。

読み込み時に厳しく検証する。レッスンの書き間違いを、学習者の採点結果ではなく
**教材作成者へのエラー**として返すため。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from atlas.models import Check, Lesson

LESSON_SUFFIX = ".yaml"


class LessonError(Exception):
    """レッスン定義が不正なときに送出する。"""


def _require_str(data: dict[str, Any], key: str, where: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LessonError(f"{where}: '{key}' は空でない文字列で指定してください")
    return value


def _optional_str_list(data: dict[str, Any], key: str, where: str) -> list[str]:
    value = data.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise LessonError(f"{where}: '{key}' は文字列のリストで指定してください")
    return [str(v) for v in value]


def _parse_check(raw: Any, where: str) -> Check:
    if not isinstance(raw, dict):
        raise LessonError(f"{where}: checks の各要素はマッピングで指定してください")

    check_id = _require_str(raw, "id", where)
    scope = f"{where} / check '{check_id}'"

    hints = _optional_str_list(raw, "hints", scope)
    if not hints:
        # ヒントの無い検証は、失敗しても学習者に打つ手が無い。教材として成立しない。
        raise LessonError(f"{scope}: 'hints' を1つ以上書いてください")

    requires_aws = raw.get("requires_aws", False)
    if not isinstance(requires_aws, bool):
        raise LessonError(f"{scope}: 'requires_aws' は true/false で指定してください")

    known = {"id", "title", "type", "hints", "requires_aws"}
    params = {k: v for k, v in raw.items() if k not in known}

    return Check(
        id=check_id,
        title=_require_str(raw, "title", scope),
        type=_require_str(raw, "type", scope),
        params=params,
        hints=hints,
        requires_aws=requires_aws,
    )


def parse_lesson(data: Any, source: str) -> Lesson:
    if not isinstance(data, dict):
        raise LessonError(f"{source}: レッスンはマッピングで指定してください")

    lesson_id = _require_str(data, "id", source)
    raw_checks = data.get("checks", [])
    if not isinstance(raw_checks, list) or not raw_checks:
        raise LessonError(f"{source}: 'checks' を1つ以上書いてください")

    checks = [_parse_check(raw, source) for raw in raw_checks]

    duplicates = _duplicates([c.id for c in checks])
    if duplicates:
        raise LessonError(f"{source}: check id が重複しています: {', '.join(duplicates)}")

    reference = data.get("reference")
    if reference is not None and not isinstance(reference, str):
        raise LessonError(f"{source}: 'reference' は文字列で指定してください")

    return Lesson(
        id=lesson_id,
        title=_require_str(data, "title", source),
        summary=_require_str(data, "summary", source),
        target_dir=_require_str(data, "target_dir", source),
        objectives=_optional_str_list(data, "objectives", source),
        checks=checks,
        reference=reference,
    )


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    dupes: set[str] = set()
    for value in values:
        if value in seen:
            dupes.add(value)
        seen.add(value)
    return sorted(dupes)


def load_lesson_file(path: Path) -> Lesson:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise LessonError(f"{path}: YAMLとして読めません: {exc}") from exc

    lesson = parse_lesson(data, str(path))
    if lesson.id != path.stem:
        raise LessonError(f"{path}: id '{lesson.id}' がファイル名 '{path.stem}' と一致しません")
    return lesson


def load_lessons(lessons_dir: Path) -> list[Lesson]:
    """ディレクトリ内の全レッスンをid順で返す。"""
    if not lessons_dir.is_dir():
        raise LessonError(f"レッスンディレクトリがありません: {lessons_dir}")

    lessons = [load_lesson_file(p) for p in sorted(lessons_dir.glob(f"*{LESSON_SUFFIX}"))]
    if not lessons:
        raise LessonError(f"レッスンが1件もありません: {lessons_dir}")
    return lessons
