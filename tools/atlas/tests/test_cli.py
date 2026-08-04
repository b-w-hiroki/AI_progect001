from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from atlas.cli import main

HINT_1 = "まず main.tf という名前のファイルを置きます"
HINT_2 = "内容は空でも構いません。存在だけを見ています"

LESSON = {
    "id": "demo",
    "title": "デモレッスン",
    "summary": "動作確認用のレッスン",
    "objectives": ["ファイルを作れる"],
    "target_dir": "work",
    "checks": [
        {
            "id": "has-main",
            "title": "main.tf がある",
            "type": "file_exists",
            "path": "main.tf",
            "hints": [HINT_1, HINT_2],
        }
    ],
}


@pytest.fixture
def env(tmp_path: Path) -> tuple[Path, Path]:
    """レッスン定義ディレクトリと、リポジトリルートを用意する。"""
    lessons_dir = tmp_path / "lessons"
    lessons_dir.mkdir()
    (lessons_dir / "demo.yaml").write_text(
        yaml.safe_dump(LESSON, allow_unicode=True), encoding="utf-8"
    )

    root = tmp_path / "repo"
    (root / "work").mkdir(parents=True)
    return lessons_dir, root


def run(env: tuple[Path, Path], *argv: str) -> int:
    lessons_dir, root = env
    return main(["--lessons-dir", str(lessons_dir), "--root", str(root), *argv])


def test_list(env: tuple[Path, Path], capsys: pytest.CaptureFixture[str]) -> None:
    assert run(env, "list") == 0
    out = capsys.readouterr().out
    assert "demo" in out
    assert "未着手" in out


def test_show(env: tuple[Path, Path], capsys: pytest.CaptureFixture[str]) -> None:
    assert run(env, "show", "demo") == 0
    out = capsys.readouterr().out
    assert "デモレッスン" in out
    assert "main.tf がある" in out


def test_check_fails_and_exits_nonzero(
    env: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(env, "check", "demo") == 1
    out = capsys.readouterr().out
    assert "0/1 達成" in out


def test_check_does_not_leak_hints(
    env: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    """教材の中核: check は「何が未達成か」までしか言わない。直し方は言わない。"""
    run(env, "check", "demo")
    out = capsys.readouterr().out
    assert HINT_1 not in out
    assert HINT_2 not in out
    # 代わりに、ヒントの開き方だけを案内する
    assert "atlas hint demo has-main" in out


def test_check_passes_when_done(env: tuple[Path, Path], capsys: pytest.CaptureFixture[str]) -> None:
    _, root = env
    (root / "work" / "main.tf").write_text("", encoding="utf-8")
    assert run(env, "check", "demo") == 0
    assert "1/1 達成" in capsys.readouterr().out


def test_check_dir_override(env: tuple[Path, Path], tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "main.tf").write_text("", encoding="utf-8")
    assert run(env, "check", "demo", "--dir", str(elsewhere)) == 0


def test_hint_reveals_one_step_at_a_time(
    env: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(env, "hint", "demo", "has-main") == 0
    first = capsys.readouterr().out
    assert HINT_1 in first
    assert HINT_2 not in first

    assert run(env, "hint", "demo", "has-main") == 0
    second = capsys.readouterr().out
    assert HINT_2 in second


def test_hint_after_exhaustion_replays_all(
    env: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    for _ in range(2):
        run(env, "hint", "demo", "has-main")
    capsys.readouterr()

    assert run(env, "hint", "demo", "has-main") == 0
    out = capsys.readouterr().out
    assert "すべて開示済み" in out
    assert HINT_1 in out and HINT_2 in out


def test_unknown_check_id(env: tuple[Path, Path], capsys: pytest.CaptureFixture[str]) -> None:
    assert run(env, "hint", "demo", "nope") == 2
    assert "has-main" in capsys.readouterr().err


def test_unknown_lesson_id(env: tuple[Path, Path], capsys: pytest.CaptureFixture[str]) -> None:
    assert run(env, "show", "nope") == 2
    assert "demo" in capsys.readouterr().err


def test_progress_reflects_attempts_and_hints(
    env: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    run(env, "check", "demo")
    run(env, "hint", "demo", "has-main")
    capsys.readouterr()

    assert run(env, "progress") == 0
    out = capsys.readouterr().out
    assert "1回挑戦" in out
    assert "ヒント1段開示" in out
    assert "0/1 レッスン完了" in out


def test_progress_marks_completion(
    env: tuple[Path, Path], capsys: pytest.CaptureFixture[str]
) -> None:
    _, root = env
    (root / "work" / "main.tf").write_text("", encoding="utf-8")
    run(env, "check", "demo")
    capsys.readouterr()

    assert run(env, "progress") == 0
    out = capsys.readouterr().out
    assert "完了" in out
    assert "1/1 レッスン完了" in out


def test_broken_lesson_exits_two(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lessons_dir = tmp_path / "lessons"
    lessons_dir.mkdir()
    (lessons_dir / "bad.yaml").write_text("id: bad\n", encoding="utf-8")

    code = main(["--lessons-dir", str(lessons_dir), "--root", str(tmp_path), "list"])
    assert code == 2
    assert "エラー" in capsys.readouterr().err
