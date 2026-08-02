#!/bin/bash
#
# SessionStart フック。
#
# Claude Code on the web はセッションごとに新しいコンテナで起動するため、
# 依存関係が入っていないと lint / 型チェック / テストが動かない。
# ここで入れておくことで、AIが最初のターンから検証ループを回せる。
#
# ローカル実行時は何もしない（$CLAUDE_CODE_REMOTE で判定）。
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"

echo "[session-start] installing Python dependencies..."
if command -v uv >/dev/null 2>&1; then
  uv sync
else
  echo "[session-start] uv not found; skipping Python setup" >&2
fi

echo "[session-start] installing Node dependencies..."
if command -v pnpm >/dev/null 2>&1; then
  pnpm install --frozen-lockfile 2>/dev/null || pnpm install
else
  echo "[session-start] pnpm not found; skipping Node setup" >&2
fi

# 以降のコマンドで src がインポートできるようにする
echo 'export PYTHONPATH="apps/api/src:${PYTHONPATH:-}"' >> "${CLAUDE_ENV_FILE:-/dev/null}"

echo "[session-start] done"
