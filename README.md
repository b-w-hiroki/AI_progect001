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

## PRコードレビューと実行範囲

AI レビューは任意です。決定的な検証は `.github/workflows/ci-labs.yml`、`ci-template.yml`、`ci-atlas.yml` で分けています。

- 自動レビューは、リポジトリ所有者が起動した同一リポジトリの非 Draft PR を対象に、PR 作成時・Draft 解除時だけ実行します。毎 push のレビューではありません。
- Draft PR と fork PR は自動レビューの対象外です。手動実行も所有者に限定されています。
- 認証シークレットの有無・有効期限・契約の利用枠はコードからは確認できません。費用や利用条件を確認し、必要なときに [セットアップ資料](docs/pr-code-review.md) を使ってください。資料の料金・サービス条件は再確認が必要です。
- AI レビュー成功は、テスト成功や AWS の動作・削除確認を代替しません。認証情報の登録や実レビュー実行は、この文書の更新には含みません。

各 CI はパスで絞っています。`tools/atlas/` に変更がない head に atlas の run がなくても、それだけで失敗とは言えません。逆に labs / template の成功を atlas の検証成功として数えないでください。

Lab の完了証拠・費用上限・削除確認は [共通チェックリスト](docs/lab-completion.md) を使います。

## 進め方

`IDEAS.md` でアイデアを絞り、`LEARNING_AWS.md` のロードマップに沿って `labs/` を順に手を動かす。
アイデアとハンズオンは対応していて、Lab 01 は `IDEAS.md` #4（ECレビュー対応）のデータ受け口にあたる。

手を動かしたら `atlas check` で採点する。写経で終わらせないため。

```bash
cd tools/atlas && uv sync
uv run atlas check 01-serverless-api
```
