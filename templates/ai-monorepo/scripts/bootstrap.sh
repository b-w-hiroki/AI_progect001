#!/usr/bin/env bash
#
# テンプレートを新規プロジェクトに変換する。
#
#   ./scripts/bootstrap.sh <project-name> [--strip-samples] [--no-install]
#
# やること:
#   1. プロジェクト名の置換（package.json / pyproject.toml / CLAUDE.md）
#   2. --strip-samples ならサンプル実装を削除し、空の骨組みだけ残す
#   3. git hooks を有効化
#   4. .env.example を .env にコピー
#   5. make setup（--no-install で省略）
#
# 冪等ではない（一度実行したら再実行しない前提）。
set -euo pipefail

usage() {
  # 先頭のコメントブロックをそのままヘルプとして出す。
  # 行番号を固定するとファイル編集で壊れるので、コメント行が続く限り読む。
  awk 'NR>1 && /^#/ { sub(/^# ?/, ""); print; next } NR>1 { exit }' "$0"
  exit "${1:-0}"
}

PROJECT_NAME=""
STRIP_SAMPLES=false
RUN_INSTALL=true

while [ $# -gt 0 ]; do
  case "$1" in
    --strip-samples) STRIP_SAMPLES=true ;;
    --no-install)    RUN_INSTALL=false ;;
    -h|--help)       usage 0 ;;
    -*)              echo "unknown option: $1" >&2; usage 1 ;;
    *)
      if [ -n "$PROJECT_NAME" ]; then
        echo "project name given twice: '$PROJECT_NAME' and '$1'" >&2
        usage 1
      fi
      PROJECT_NAME="$1"
      ;;
  esac
  shift
done

if [ -z "$PROJECT_NAME" ]; then
  echo "error: project name is required" >&2
  usage 1
fi

# npm/PyPI のパッケージ名として使えるかを先に弾く
if ! printf '%s' "$PROJECT_NAME" | grep -Eq '^[a-z0-9][a-z0-9-]*$'; then
  echo "error: project name must be lowercase alphanumeric with hyphens (got '$PROJECT_NAME')" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> renaming project to '$PROJECT_NAME'"
# macOS と GNU の sed 差異を避けるため一時ファイル経由で置換する
replace_in_file() {
  local file="$1" from="$2" to="$3"
  [ -f "$file" ] || return 0
  local tmp
  tmp="$(mktemp)"
  sed "s|${from}|${to}|g" "$file" > "$tmp"
  mv "$tmp" "$file"
}

replace_in_file package.json '"name": "monorepo-root"' "\"name\": \"${PROJECT_NAME}\""
replace_in_file pyproject.toml 'name = "monorepo-root"' "name = \"${PROJECT_NAME}-root\""

# CLAUDE.md のプレースホルダを、埋めるべきTODOに差し替える。
# 空欄のまま放置されると、AIが毎ターン無意味な例文を読むことになる。
replace_in_file CLAUDE.md \
  '（例）EC事業者向けのレビュー分析SaaS。レビューを収集・分類し、月次で改善レポートを出す。' \
  "TODO: ${PROJECT_NAME} が何をするものか、誰のためかを1〜2行で書く。"

if [ "$STRIP_SAMPLES" = true ]; then
  echo "==> stripping sample implementation"

  rm -f \
    apps/api/src/api/reviews.py \
    apps/api/tests/test_reviews.py \
    apps/api/tests/test_main.py \
    apps/web/src/reviews.ts \
    apps/web/src/reviews.test.ts \
    apps/web/src/App.test.tsx

  cat > apps/api/src/api/contracts.py <<'PY'
"""APIの入出力型。

**`packages/contracts/src/index.ts` と1対1で対応させること。**
JSON上は camelCase に統一している（alias_generator）。
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _Base(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        frozen=True,
        extra="forbid",
    )
PY

  cat > apps/api/src/api/main.py <<'PY'
"""FastAPI アプリケーション。

起動: make dev
ドキュメント: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
PY

  cat > apps/api/src/api/__init__.py <<'PY'
"""バックエンドAPI。"""

__all__ = ["contracts", "main"]
PY

  cat > apps/api/tests/test_main.py <<'PY'
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    yield TestClient(app)


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
PY

  cat > packages/contracts/src/index.ts <<'TS'
/**
 * フロントエンドとバックエンドが共有するAPIの入出力型。
 *
 * **`apps/api/src/api/contracts.py` と1対1で対応させること。**
 */

export type {};
TS

  cat > apps/web/src/App.tsx <<'TSX'
export function App() {
  return (
    <main>
      <h1>Hello</h1>
    </main>
  );
}
TSX

  cat > apps/web/src/api.ts <<'TS'
/**
 * バックエンドAPIのクライアント。
 *
 * fetch をここに閉じ込め、コンポーネントからは型の付いた関数だけを呼ぶ。
 * パスは相対の /api で書く（vite.config.ts の proxy が転送する）。
 */

const BASE = "/api";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    throw new ApiError(`${init?.method ?? "GET"} ${path} failed`, response.status);
  }

  return (await response.json()) as T;
}
TS
fi

echo "==> enabling git hooks"
if [ -d .git ]; then
  git config core.hooksPath .githooks
else
  echo "    (not a git repository — run 'git init' then 'git config core.hooksPath .githooks')"
fi

if [ ! -f .env ]; then
  echo "==> creating .env from .env.example"
  cp .env.example .env
fi

if [ "$RUN_INSTALL" = true ]; then
  echo "==> installing dependencies"
  make setup
fi

cat <<EOF

✅ '${PROJECT_NAME}' is ready.

次にやること:
  1. CLAUDE.md の「このプロジェクトについて」を1〜2行で書く
  2. make check   # 検証が通ることを確認
  3. make dev     # API :8000 / Web :5173

このスクリプト自身はもう不要なので削除してよい:
  rm scripts/bootstrap.sh
EOF
