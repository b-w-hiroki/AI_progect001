# ハーネス仕様書

> ハーネス = **人が毎回言わなくても、機械が守らせてくれる常設の仕組み**。
> このリポジトリに何が設置されていて、何がまだ口約束のままかを記録する。
> ハーネスを足す・消す・変えるPRでは、この文書も更新すること。

## 強度の分類

| 強度 | 意味 | 例 |
|---|---|---|
| 🔒 物理ブロック | そもそも実行・コミットできない | permissionsのdeny、pre-commit |
| 🚨 自動検出 | やれてしまうが、機械が失敗として検出する | make check、pytest、CI |
| 📥 自動注入 | ルールが毎回自動で読み込まれる（強制はしない） | CLAUDE.md、REVIEW.md |

上ほど強い。📥は「AIが忘れない」ことしか保証しないので、重要なルールは🚨以上へ昇格させていく。

---

## 設置済みハーネス一覧

### リポジトリ本体

| # | 守らせるルール | 強度 | 装置 | 動作確認 |
|---|---|---|---|---|
| H1 | リポジトリの規約・やらないこと | 📥 | `CLAUDE.md`（毎ターン自動読込） | ファイルが存在し、構成表が実態と一致していること（目視） |
| H2 | PRは必ずAIレビューを受ける | 🚨 | `.github/workflows/code-review.yml`（PR作成・ドラフト解除で起動） | PRのChecksに `Code Review` が出る |
| H3 | レビューの基準・指摘しないもの | 📥 | `REVIEW.md`（レビュー時に読込） | ファイルが存在すること |
| H4 | labs の成果物が要件を満たす | 🚨 | `tools/atlas`（採点CLI） | `cd tools/atlas && uv run atlas check 01-serverless-api` → 8項目の判定が出る（全達成なら exit 0） |
| H5 | レッスン定義の品質（全checkにヒント必須など） | 🚨 | `tools/atlas/src/atlas/loader.py`（読込時に厳格検証） | `cd tools/atlas && uv run pytest -k hints` → 4件通過 |
| H6 | atlas 自体の品質 | 🚨 | pytest 47件 / ruff / mypy strict | `cd tools/atlas && uv run pytest && uv run ruff check . && uv run mypy` |
| H7 | 進捗ファイル等をコミットしない | 🔒 | `.gitignore`（`.atlas/`、`__pycache__/`） | `git check-ignore .atlas/progress.json` → 0 |
| H8 | レビュー環境の不備を自分で説明させる | 🚨 | `code-review.yml` / `claude.yml` の事前チェック。認証シークレット未登録なら数秒で明確なエラーにし、PRへ手順コメントを1回だけ自動投稿 | run部分をローカル抽出し、未登録/登録済み/コメント重複の3ケースで検証済み |
| H9 | 本体リポジトリで `terraform apply/destroy` を勝手に実行しない | 🔒 | 本体ルートの `.claude/settings.json`（deny） | ファイルの deny リストを目視 |
| H10 | 本体のPRで atlas/labs/雛形の検証が強制される | 🚨 | `ci-atlas.yml` / `ci-labs.yml` / `ci-template.yml`（変更されたパスだけ起動） | ci-atlas・ci-templateはローカルで同一コマンドを実行し通過を確認。ci-labsはこの環境に`terraform`が無く未検証（Actions上のみ確認可） |

### templates/ai-monorepo 雛形（この雛形から作る新プロジェクトに継承される）

| # | 守らせるルール | 強度 | 装置 | 動作確認 |
|---|---|---|---|---|
| T1 | lint・型・テストが全部通ること | 🚨 | `Makefile`（`make check` 1コマンド、約6秒） | `cd templates/ai-monorepo && make check` |
| T2 | 型エラーをコミットさせない | 🔒 | `.githooks/pre-commit` | 型エラーを仕込んで `git commit` → 拒否される |
| T3 | 秘密情報を読ませない | 🔒 | `.claude/settings.json` の deny（`.env`、`*.pem`、`credentials`） | settings.json の deny リストを目視 |
| T4 | `terraform apply/destroy` を勝手に実行させない | 🔒 | 同上の deny | 同上 |
| T5 | PRごとにCIでチェック | 🚨 | `.github/workflows/ci.yml` | PRのChecksに CI が出る |
| T6 | API境界のJSONは camelCase | 🚨 | `test_serializes_to_camel_case`（契約ピンテスト） | `cd templates/ai-monorepo && uv run pytest -k camel` |
| T7 | 環境の初期化漏れを防ぐ | 📥 | `.claude/hooks/session-start.sh`（セッション開始時に自動実行） | スクリプトが存在すること |
| T8 | レビュー環境の不備を自分で説明させる | 🚨 | H8と同じ事前チェック（案内文は雛形のREADMEを指す） | H8と同一ロジック |

---

## まだ口約束のもの（ギャップ）

棚卸しで見つかった、ルールはあるのに装置がないもの。**上から優先度順。**

| # | 口約束のルール | いまの状態 | 昇格の候補 |
|---|---|---|---|
| G3 | ドキュメントの数値は実測値にする | CLAUDE.md の📥のみ | 検出は難しい。PRレビュー(REVIEW.md)の観点に明記するのが現実解 |
| G4 | 大きい作業は「作る前に質問」から始める | 毎回口で言う運用（docs/ai-dev-flow.html 参照） | `.claude/skills/` にスラッシュコマンド化 |

### 塞いだギャップ（履歴）

| # | 内容 | 対応 |
|---|---|---|
| G1 | `terraform apply/destroy` のdeny設定が雛形にしかなく、実物の labs/ がある本体に無かった | 本体ルートに `.claude/settings.json` を追加(H9) |
| G2 | 本体のPRに決定的CIが無く、AIレビューの「意見」だけでマージできた | `tools/atlas` / `labs/` / `templates/ai-monorepo` を対象にした変更検知CIを追加(H10) |

---

## この仕様書自体の完成条件

- [x] 一覧の「動作確認」コマンドが実際に通る（H4〜H7、T1、T6 は実行で確認済み。H9/H10 は2026-08-12に追加、ci-labsのみ terraform CLI が手元に無く未実行確認）
- [ ] ハーネスの追加・削除PRで、この文書が同時に更新されている
