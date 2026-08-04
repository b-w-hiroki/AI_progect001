"""検証項目の実装。

新しい検証の種類を足すときは、ここに関数を書いて `CHECKS` に登録するだけでよい。
レッスン側（YAML）はコードを変えずに書ける。

**設計の要点**: AWSに繋がなくても判定できる検証を優先して用意している。
静的検査（ファイル内容・Terraformの構文）だけでも学習の大半は採点でき、
実リソースの検査は認証情報がある場合のみ追加で走らせればよい。
これにより、教材を無料・オフラインで回せる範囲が最大化される。
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from atlas.models import Check, CheckResult, Status

COMMAND_TIMEOUT_SECONDS = 120

CheckFn = Callable[[Check, Path], CheckResult]


class CheckError(Exception):
    """レッスン定義そのものが不正なときに送出する（学習者の誤りではない）。"""


def _result(check: Check, status: Status, detail: str) -> CheckResult:
    return CheckResult(check=check, status=status, detail=detail)


def _require(check: Check, key: str) -> str:
    value = check.params.get(key)
    if not isinstance(value, str) or not value:
        raise CheckError(f"check '{check.id}': パラメータ '{key}' が必要です")
    return value


def _resolve(target_dir: Path, relative: str) -> Path:
    """レッスンの対象ディレクトリ内に収まるパスへ解決する。

    レッスンYAMLは信頼された内容だが、`../` で外へ出る定義は設定ミスの可能性が高いので
    ここで弾いておく。
    """
    resolved = (target_dir / relative).resolve()
    root = target_dir.resolve()
    if not resolved.is_relative_to(root):
        raise CheckError(f"path '{relative}' が対象ディレクトリの外を指しています")
    return resolved


def check_file_exists(check: Check, target_dir: Path) -> CheckResult:
    relative = _require(check, "path")
    path = _resolve(target_dir, relative)
    if path.exists():
        return _result(check, Status.PASSED, f"{relative} があります")
    return _result(check, Status.FAILED, f"{relative} が見つかりません")


def check_file_matches(check: Check, target_dir: Path) -> CheckResult:
    relative = _require(check, "path")
    pattern = _require(check, "pattern")
    path = _resolve(target_dir, relative)

    if not path.exists():
        return _result(check, Status.FAILED, f"{relative} が見つかりません")

    text = path.read_text(encoding="utf-8")
    if re.search(pattern, text):
        return _result(check, Status.PASSED, f"{relative} に想定の記述があります")
    return _result(check, Status.FAILED, f"{relative} に想定の記述が見つかりません")


def check_file_not_matches(check: Check, target_dir: Path) -> CheckResult:
    """禁止事項の検出に使う（例: IAMポリシーのワイルドカード）。"""
    relative = _require(check, "path")
    pattern = _require(check, "pattern")
    path = _resolve(target_dir, relative)

    if not path.exists():
        return _result(check, Status.FAILED, f"{relative} が見つかりません")

    text = path.read_text(encoding="utf-8")
    match = re.search(pattern, text)
    if match is None:
        return _result(check, Status.PASSED, f"{relative} に禁止パターンはありません")

    line = text[: match.start()].count("\n") + 1
    return _result(check, Status.FAILED, f"{relative}:{line} に禁止パターンがあります")


def check_command_succeeds(check: Check, target_dir: Path) -> CheckResult:
    """コマンドを実行し、終了コード0を合格とする。

    `terraform fmt -check` や `terraform validate` のように、
    既存のツールが持つ判定をそのまま採点に使えるようにするための汎用検証。
    """
    command = check.params.get("command")
    if not isinstance(command, list) or not all(isinstance(c, str) for c in command):
        raise CheckError(f"check '{check.id}': 'command' は文字列のリストで指定してください")

    argv = [str(c) for c in command]
    if shutil.which(argv[0]) is None:
        return _result(check, Status.SKIPPED, f"{argv[0]} がインストールされていません")

    try:
        completed = subprocess.run(  # noqa: S603 - レッスン定義は信頼された内容
            argv,
            cwd=target_dir,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _result(
            check,
            Status.FAILED,
            f"{' '.join(argv)} が{COMMAND_TIMEOUT_SECONDS}秒で終わりませんでした",
        )

    if completed.returncode == 0:
        return _result(check, Status.PASSED, f"{' '.join(argv)} が成功しました")

    detail = (completed.stderr or completed.stdout or "").strip().splitlines()
    tail = detail[-1] if detail else f"終了コード {completed.returncode}"
    return _result(check, Status.FAILED, f"{' '.join(argv)} が失敗しました: {tail}")


def check_aws_resource_exists(check: Check, target_dir: Path) -> CheckResult:
    """AWS CLIで実リソースの存在を確認する。

    認証情報が無い環境では SKIPPED を返す（失敗にはしない）。
    「まだデプロイしていない」と「認証情報が無い」を区別するため。
    """
    command = check.params.get("command")
    if not isinstance(command, list) or not all(isinstance(c, str) for c in command):
        raise CheckError(f"check '{check.id}': 'command' は文字列のリストで指定してください")

    if shutil.which("aws") is None:
        return _result(check, Status.SKIPPED, "AWS CLI がインストールされていません")
    if not _aws_credentials_present():
        return _result(check, Status.SKIPPED, "AWS認証情報が設定されていません")

    return check_command_succeeds(check, target_dir)


def _aws_credentials_present() -> bool:
    if os.environ.get("AWS_ACCESS_KEY_ID") or os.environ.get("AWS_PROFILE"):
        return True
    return (Path.home() / ".aws" / "credentials").exists()


CHECKS: dict[str, CheckFn] = {
    "file_exists": check_file_exists,
    "file_matches": check_file_matches,
    "file_not_matches": check_file_not_matches,
    "command_succeeds": check_command_succeeds,
    "aws_resource_exists": check_aws_resource_exists,
}


def run_check(check: Check, target_dir: Path) -> CheckResult:
    fn = CHECKS.get(check.type)
    if fn is None:
        known = ", ".join(sorted(CHECKS))
        raise CheckError(f"check '{check.id}': 未知の type '{check.type}'（利用可能: {known}）")
    return fn(check, target_dir)
