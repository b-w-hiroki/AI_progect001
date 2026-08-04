"""atlas コマンドの入口。

**答えを出さない**という教育方針を、UIの側で担保している:
  - `check` は「何が未達成か」までしか言わない。直し方は言わない
  - 直し方は `hint` で1段ずつ開く。学習者が要求した分だけ出す
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from atlas.loader import LessonError, load_lessons
from atlas.models import Lesson, LessonReport, Status
from atlas.progress import Progress
from atlas.runner import run_lesson

MARK = {Status.PASSED: "✅", Status.FAILED: "❌", Status.SKIPPED: "⏭️ "}


def find_repo_root(start: Path) -> Path:
    """`.git` を持つ最も近い親をリポジトリルートとする。無ければ start。"""
    for candidate in [start, *start.parents]:
        if (candidate / ".git").exists():
            return candidate
    return start


def default_lessons_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "lessons"


def _load(lessons_dir: Path) -> list[Lesson]:
    return load_lessons(lessons_dir)


def _pick(lessons: list[Lesson], lesson_id: str) -> Lesson:
    lesson = next((x for x in lessons if x.id == lesson_id), None)
    if lesson is None:
        available = ", ".join(x.id for x in lessons)
        raise LessonError(f"レッスン '{lesson_id}' がありません（利用可能: {available}）")
    return lesson


def cmd_list(args: argparse.Namespace) -> int:
    lessons = _load(args.lessons_dir)
    progress = Progress(args.root)

    print("レッスン一覧\n")
    for lesson in lessons:
        entry = progress.for_lesson(lesson.id)
        state = (
            "完了"
            if entry.completed_at
            else (f"{entry.attempts}回挑戦" if entry.attempts else "未着手")
        )
        print(f"  {lesson.id}  {lesson.title}")
        print(f"      {lesson.summary}")
        print(f"      状態: {state} / 検証項目: {len(lesson.checks)}件\n")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    lesson = _pick(_load(args.lessons_dir), args.lesson)

    print(f"{lesson.id}  {lesson.title}\n")
    print(lesson.summary)
    if lesson.objectives:
        print("\n到達目標")
        for item in lesson.objectives:
            print(f"  - {item}")
    print(f"\n対象ディレクトリ: {lesson.target_dir}")
    if lesson.reference:
        print(f"参考: {lesson.reference}")

    print("\n検証される項目")
    for check in lesson.checks:
        aws = "（AWS認証情報が必要）" if check.requires_aws else ""
        print(f"  - {check.title}{aws}")

    print(f"\n採点する: atlas check {lesson.id}")
    return 0


def _print_report(report: LessonReport, progress: Progress) -> None:
    lesson = report.lesson
    print(f"{lesson.id}  {lesson.title}")
    print(f"対象: {report.target_dir}\n")

    for result in report.results:
        print(f"  {MARK[result.status]} {result.check.title}")
        if result.status is not Status.PASSED:
            print(f"      {result.detail}")

    total = len(report.results)
    print(f"\n  {report.passed_count}/{total} 達成")

    if report.skipped:
        print(f"  {len(report.skipped)}件は判定できませんでした（未達成として扱います）")

    if report.complete:
        print("\n🎉 このレッスンは完了です。")
        return

    if report.failed:
        print("\n次に取り組む項目:")
        for result in report.failed:
            check = result.check
            revealed = progress.revealed_count(lesson.id, check.id)
            remaining = check.hint_count() - revealed
            hint_note = f"ヒント残り{remaining}段" if remaining > 0 else "ヒントは開示済み"
            print(f"  - {check.title}")
            print(f"      atlas hint {lesson.id} {check.id}   （{hint_note}）")


def cmd_check(args: argparse.Namespace) -> int:
    lesson = _pick(_load(args.lessons_dir), args.lesson)
    target = Path(args.dir).resolve() if args.dir else (args.root / lesson.target_dir)

    report = run_lesson(lesson, target)

    progress = Progress(args.root)
    progress.record_attempt(lesson.id, complete=report.complete)
    progress.save()

    _print_report(report, progress)
    return 0 if report.complete else 1


def cmd_hint(args: argparse.Namespace) -> int:
    lesson = _pick(_load(args.lessons_dir), args.lesson)
    check = lesson.find_check(args.check)
    if check is None:
        available = ", ".join(c.id for c in lesson.checks)
        print(f"検証項目 '{args.check}' がありません（利用可能: {available}）", file=sys.stderr)
        return 2

    progress = Progress(args.root)
    index = progress.reveal_next_hint(lesson.id, check.id, check.hint_count())

    if index is None:
        print(f"{check.title}\n")
        print("ヒントはすべて開示済みです。これまでのヒント:\n")
        for i, hint in enumerate(check.hints, start=1):
            print(f"  {i}. {hint}")
        print("\n行き詰まったら、対象ディレクトリのREADMEを読み直してみてください。")
        return 0

    progress.save()
    print(f"{check.title}\n")
    print(f"  ヒント {index + 1}/{check.hint_count()}: {check.hints[index]}")
    remaining = check.hint_count() - (index + 1)
    if remaining:
        print(f"\n  さらに必要なら: atlas hint {lesson.id} {check.id} （残り{remaining}段）")
    return 0


def cmd_progress(args: argparse.Namespace) -> int:
    lessons = _load(args.lessons_dir)
    progress = Progress(args.root)

    done = 0
    print("学習の進捗\n")
    for lesson in lessons:
        entry = progress.for_lesson(lesson.id)
        if entry.completed_at:
            done += 1
            print(f"  ✅ {lesson.id}  完了 ({entry.completed_at})")
        elif entry.attempts:
            hints = sum(entry.hints_revealed.values())
            print(f"  ⏳ {lesson.id}  {entry.attempts}回挑戦 / ヒント{hints}段開示")
        else:
            print(f"  ・ {lesson.id}  未着手")

    print(f"\n  {done}/{len(lessons)} レッスン完了")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="atlas",
        description="インフラ学習用のレッスン採点ツール。答えではなく段階的なヒントを返す。",
    )
    parser.add_argument("--lessons-dir", type=Path, default=None, help="レッスン定義のディレクトリ")
    parser.add_argument("--root", type=Path, default=None, help="リポジトリルート（進捗の保存先）")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="レッスン一覧を表示").set_defaults(func=cmd_list)

    show = sub.add_parser("show", help="レッスンの内容を表示")
    show.add_argument("lesson")
    show.set_defaults(func=cmd_show)

    check = sub.add_parser("check", help="達成状況を採点")
    check.add_argument("lesson")
    check.add_argument("--dir", default=None, help="対象ディレクトリを上書きする")
    check.set_defaults(func=cmd_check)

    hint = sub.add_parser("hint", help="ヒントを1段だけ開く")
    hint.add_argument("lesson")
    hint.add_argument("check")
    hint.set_defaults(func=cmd_hint)

    sub.add_parser("progress", help="進捗を表示").set_defaults(func=cmd_progress)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    args.root = (args.root or find_repo_root(Path.cwd())).resolve()
    args.lessons_dir = (args.lessons_dir or default_lessons_dir()).resolve()

    try:
        result: int = args.func(args)
    except LessonError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 2
    return result


if __name__ == "__main__":
    raise SystemExit(main())
