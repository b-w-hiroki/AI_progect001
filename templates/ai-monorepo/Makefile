##############################################################################
# 検証ループと開発サーバーの入口。
#
# AIは「コマンドを実行 → エラー出力を読む → 直す」を回して精度を上げる。
# そのため入口は集約し、速く・決定的にすることが重要。
##############################################################################

.DEFAULT_GOAL := help
.PHONY: help setup dev dev-api dev-web fmt lint types test watch \
        check check-py check-ts check-fast clean

help: ## コマンド一覧を表示
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-11s\033[0m %s\n", $$1, $$2}'

##############################################################################
# セットアップ
##############################################################################

setup: ## 依存関係をインストール（初回のみ）
	uv sync
	pnpm install
	@echo ""
	@echo "✅ setup complete —  make dev で起動、make check で検証"

##############################################################################
# 開発
##############################################################################

dev: ## APIとフロントを同時起動（API :8000 / Web :5173）
	@echo "API  → http://localhost:8000/docs"
	@echo "Web  → http://localhost:5173"
	@trap 'kill 0' EXIT INT TERM; \
	$(MAKE) --no-print-directory dev-api & \
	$(MAKE) --no-print-directory dev-web & \
	wait

dev-api: ## APIのみ起動
	uv run uvicorn api.main:app --reload --port 8000 --app-dir apps/api/src

dev-web: ## フロントのみ起動
	pnpm --filter @repo/web dev

watch: ## テストを監視実行（変更のたびに該当分だけ再実行）
	pnpm run test:watch

##############################################################################
# 検証
##############################################################################

fmt: ## フォーマットと自動修正
	uv run ruff format .
	uv run ruff check --fix .
	pnpm run fmt

check: ## lint + 型 + テスト。コミット前に必ず通す
	@$(MAKE) --no-print-directory --jobs=2 --output-sync=target check-py check-ts
	@echo ""
	@echo "✅ all checks passed"

# Python と TypeScript は互いに独立しているので並列に回せる。
# このテンプレートでの実測は 7.4s -> 6.2s（約17%短縮）。
# TS側（jsdom環境の起動）が支配的なので、劇的には縮まない。
# 作業中の反復には lint を飛ばす check-fast のほうが効く。
check-py: ## Python側だけ検証
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy
	uv run pytest

check-ts: ## TypeScript側だけ検証
	pnpm run lint
	pnpm run types
	pnpm run test

check-fast: ## 型チェックとテストのみ（lintを飛ばす。作業中の反復用）
	@$(MAKE) --no-print-directory --jobs=2 --output-sync=target types test

lint: ## 静的解析のみ
	uv run ruff check .
	pnpm run lint

types: ## 型チェックのみ
	uv run mypy
	pnpm run types

test: ## テストのみ
	uv run pytest
	pnpm run test

##############################################################################
# 片付け
##############################################################################

clean: ## 生成物を削除
	rm -rf .venv node_modules .pytest_cache .mypy_cache .ruff_cache dist
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
