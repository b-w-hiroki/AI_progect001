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
| [docs/ai-dev-flow.html](docs/ai-dev-flow.html) | AI開発の進め方フロー図。依頼サイズ(小/中/大)の判定 → 実装 → 機械検証。ブラウザで開く |
| [docs/harness.md](docs/harness.md) | ハーネス仕様書。機械に守らせている規約の一覧・強度・動作確認コマンド・未整備の穴 |

## PRコードレビュー

ClaudeによるPRレビューを GitHub Actions で設定済み。ただし**ファイルを置いただけでは動かない**。

PCから10〜15分の初期設定が必要:
[docs/pr-code-review.md のセットアップ手順](docs/pr-code-review.md#bgithub-actionsのセットアップ手順)（Step 0〜5。Step 2 のみターミナルを使う）

概略: GitHub App インストール → PCで `claude setup-token` → シークレット `CLAUDE_CODE_OAUTH_TOKEN` の登録 → 動作確認。
サブスクリプション方式なので、APIキーの発行と上限設定は不要。

## 進め方

`IDEAS.md` でアイデアを絞り、`LEARNING_AWS.md` のロードマップに沿って `labs/` を順に手を動かす。
アイデアとハンズオンは対応していて、Lab 01 は `IDEAS.md` #4（ECレビュー対応）のデータ受け口にあたる。

手を動かしたら `atlas check` で採点する。写経で終わらせないため。

```bash
cd tools/atlas && uv sync
uv run atlas check 01-serverless-api
```
