# AI_progect001

AI活用プロダクトのアイデア検討と、それを自力で作るためのAWS/インフラ学習を進めるリポジトリ。

## 目次

| ファイル | 内容 |
|---|---|
| [IDEAS.md](IDEAS.md) | AI活用 × マネタイズのアイデア集。8案＋比較表＋次アクション |
| [LEARNING_AWS.md](LEARNING_AWS.md) | AWS/インフラ学習ロードマップ。フェーズ1〜4＋資格の位置づけ |
| [labs/01-serverless-api/](labs/01-serverless-api/) | ハンズオン: Terraformでサーバーレスapiを構築（フェーズ1） |
| [templates/ai-monorepo/](templates/ai-monorepo/) | AI開発向けモノレポ雛形（Python + TypeScript）。新規プロジェクトの起点 |
| [docs/pr-code-review.md](docs/pr-code-review.md) | PRのAIコードレビュー導入手順。方式の比較・費用抑制・調整方法 |

## PRコードレビュー

ClaudeによるPRレビューを GitHub Actions で設定済み。**動かすには2つの初期設定が必要**:

1. [Claude GitHub App](https://github.com/apps/claude) をこのリポジトリにインストール
2. リポジトリシークレットに `ANTHROPIC_API_KEY` を登録

詳細と費用の抑え方は [docs/pr-code-review.md](docs/pr-code-review.md)。

## 進め方

`IDEAS.md` でアイデアを絞り、`LEARNING_AWS.md` のロードマップに沿って `labs/` を順に手を動かす。
アイデアとハンズオンは対応していて、Lab 01 は `IDEAS.md` #4（ECレビュー対応）のデータ受け口にあたる。
