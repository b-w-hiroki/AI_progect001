# AI_progect001

AI活用プロダクトのアイデア検討と、それを自力で作るためのAWS/インフラ学習を進めるリポジトリ。

## 目次

| ファイル | 内容 |
|---|---|
| [IDEAS.md](IDEAS.md) | AI活用 × マネタイズのアイデア集。8案＋比較表＋次アクション |
| [LEARNING_AWS.md](LEARNING_AWS.md) | AWS/インフラ学習ロードマップ。フェーズ1〜4＋資格の位置づけ |
| [labs/01-serverless-api/](labs/01-serverless-api/) | ハンズオン: Terraformでサーバーレスapiを構築（フェーズ1） |
| [tools/atlas/](tools/atlas/) | ハンズオンの採点CLI。「できたつもり」を潰す。答えは出さず段階ヒントを返す |
| [templates/ai-monorepo/](templates/ai-monorepo/) | AI開発向けモノレポ雛形（Python + TypeScript）。新規プロジェクトの起点 |
| [docs/pr-code-review.md](docs/pr-code-review.md) | PRのAIコードレビュー導入手順。方式の比較・費用抑制・調整方法 |

## PRコードレビュー

ClaudeによるPRレビューを GitHub Actions で設定済み。ただし**ファイルを置いただけでは動かない**。

PCから10〜15分の初期設定が必要:
[docs/pr-code-review.md のセットアップ手順](docs/pr-code-review.md#bgithub-actionsのセットアップ手順)（Step 0〜5、ブラウザのみで完結）

概略: PR #4 のマージ → GitHub App インストール → APIキー発行と上限設定 → シークレット登録 → 動作確認。

## 進め方

`IDEAS.md` でアイデアを絞り、`LEARNING_AWS.md` のロードマップに沿って `labs/` を順に手を動かす。
アイデアとハンズオンは対応していて、Lab 01 は `IDEAS.md` #4（ECレビュー対応）のデータ受け口にあたる。

手を動かしたら `atlas check` で採点する。写経で終わらせないため。

```bash
cd tools/atlas && uv sync
uv run atlas check 01-serverless-api
```
