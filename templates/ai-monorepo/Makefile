##############################################################################
# 検証ループの入口。
#
# AIは「コマンドを実行 → エラー出力を読む → 直す」を回して精度を上げる。
# そのため入口は1つ（make check）に集約し、速く・決定的にすることが重要。
##############################################################################

.DEFAULT_GOAL := help
.PHONY: help setup fmt lint types test check clean

help: ## コマンド一覧を表示
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-8s\033[0m %s\n", $$1, $$2}'

setup: ## 依存関係をインストール（初回のみ）
	uv sync
	pnpm install

fmt: ## フォーマットと自動修正
	uv run ruff format .
	uv run ruff check --fix .
	pnpm run fmt

lint: ## 静的解析
	uv run ruff format --check .
	uv run ruff check .
	pnpm run lint

types: ## 型チェック（mypy strict / tsc strict）
	uv run mypy
	pnpm run types

test: ## テスト
	uv run pytest
	pnpm run test

check: lint types test ## lint + 型 + テスト。コミット前に必ず通す
	@echo ""
	@echo "✅ all checks passed"

clean: ## 生成物を削除
	rm -rf .venv node_modules .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
