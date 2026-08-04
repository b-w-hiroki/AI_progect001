from __future__ import annotations

from pathlib import Path

import pytest

from atlas.checks import CheckError, run_check
from atlas.models import Check, Status


def make_check(check_type: str, **params: object) -> Check:
    return Check(
        id="c1",
        title="テスト用の検証",
        type=check_type,
        params=params,
        hints=["ヒント"],
    )


def test_file_exists_passes(tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text("", encoding="utf-8")
    result = run_check(make_check("file_exists", path="main.tf"), tmp_path)
    assert result.status is Status.PASSED


def test_file_exists_fails_when_missing(tmp_path: Path) -> None:
    result = run_check(make_check("file_exists", path="main.tf"), tmp_path)
    assert result.status is Status.FAILED
    assert "main.tf" in result.detail


def test_file_matches(tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text('resource "aws_lambda_function" "x" {}', encoding="utf-8")
    check = make_check("file_matches", path="main.tf", pattern=r'resource\s+"aws_lambda_function"')
    assert run_check(check, tmp_path).status is Status.PASSED


def test_file_matches_fails_on_missing_file(tmp_path: Path) -> None:
    check = make_check("file_matches", path="main.tf", pattern="anything")
    assert run_check(check, tmp_path).status is Status.FAILED


def test_file_not_matches_reports_line_number(tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text('ok\nok\nactions = ["*"]\n', encoding="utf-8")
    check = make_check("file_not_matches", path="main.tf", pattern=r'actions\s*=\s*\[\s*"\*"\s*\]')
    result = run_check(check, tmp_path)
    assert result.status is Status.FAILED
    # 学習者が直す場所へ辿り着けるよう、行番号まで示す
    assert "main.tf:3" in result.detail


def test_file_not_matches_passes_when_clean(tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text('actions = ["dynamodb:PutItem"]\n', encoding="utf-8")
    check = make_check("file_not_matches", path="main.tf", pattern=r'actions\s*=\s*\[\s*"\*"\s*\]')
    assert run_check(check, tmp_path).status is Status.PASSED


def test_path_escaping_target_dir_is_rejected(tmp_path: Path) -> None:
    check = make_check("file_exists", path="../outside.tf")
    with pytest.raises(CheckError):
        run_check(check, tmp_path)


def test_command_succeeds(tmp_path: Path) -> None:
    check = make_check("command_succeeds", command=["true"])
    assert run_check(check, tmp_path).status is Status.PASSED


def test_command_failure_includes_output(tmp_path: Path) -> None:
    argv = ["sh", "-c", "echo 何かが壊れています >&2; exit 1"]
    check = make_check("command_succeeds", command=argv)
    result = run_check(check, tmp_path)
    assert result.status is Status.FAILED
    assert "何かが壊れています" in result.detail


def test_missing_binary_is_skipped_not_failed(tmp_path: Path) -> None:
    # ツール未導入は学習者の失敗ではないので、FAILED にしてはいけない
    check = make_check("command_succeeds", command=["atlas-no-such-binary-xyz"])
    assert run_check(check, tmp_path).status is Status.SKIPPED


def test_command_runs_in_target_dir(tmp_path: Path) -> None:
    (tmp_path / "marker").write_text("", encoding="utf-8")
    check = make_check("command_succeeds", command=["test", "-f", "marker"])
    assert run_check(check, tmp_path).status is Status.PASSED


def test_aws_check_skipped_without_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    check = make_check("aws_resource_exists", command=["aws", "sts", "get-caller-identity"])
    result = run_check(check, tmp_path)
    assert result.status is Status.SKIPPED


def test_unknown_check_type_is_a_lesson_error(tmp_path: Path) -> None:
    with pytest.raises(CheckError):
        run_check(make_check("no_such_type"), tmp_path)


def test_missing_required_param_is_a_lesson_error(tmp_path: Path) -> None:
    with pytest.raises(CheckError):
        run_check(make_check("file_exists"), tmp_path)
