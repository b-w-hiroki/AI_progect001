# CLAUDE.md

> 毎ターン読み込まれる。**短く・事実だけ**を保つこと。

## このリポジトリについて

AI活用プロダクトのアイデア検討、AWS/インフラ学習、開発テンプレートを置く個人リポジトリ。
プロダクトコード本体ではなく、**教材とひな形が主な中身**。

## 構成

```
IDEAS.md                アイデア集（8案）
LEARNING_AWS.md         AWS学習ロードマップ（フェーズ1〜4）
labs/01-serverless-api/ Terraformハンズオン。実際にAWSにデプロイする
templates/ai-monorepo/  新規プロジェクト用の雛形。独自の CLAUDE.md を持つ
REVIEW.md               PRレビューの指示（マネージドCode Review用）
```

## 検証コマンド

リポジトリ全体を通す単一コマンドは無い（成果物の性質が違うため）。対象ごとに実行する。

| 対象 | コマンド |
|---|---|
| `templates/ai-monorepo/` | `cd templates/ai-monorepo && make check` |
| `labs/01-serverless-api/` | `terraform fmt -check && terraform validate` |

**`templates/ai-monorepo/` を変更したら `make check` を通すこと。** 通らない雛形を配布しない。

## 規約

- **ドキュメントに書く数値は実測値にする。** 「約4秒」「テスト18件」のような記述は、
  コードを変えたら必ず測り直す。推定値を書かない
- Terraform は `terraform destroy` で全部消える状態を保つ。学習用リソースの消し忘れは課金事故になる
- IAMポリシーに `"Action": "*"` を書かない。必要な権限だけ列挙する
- 秘密情報・認証情報をコミットしない。`.env.example` にはダミー値のみ
- `templates/ai-monorepo/` 配下は雛形なので、そこだけで完結させる
  （このリポジトリ固有の事情を持ち込まない）

## やらないこと

- `terraform apply` / `destroy` を勝手に実行しない
- AWSリソースを作成する操作を確認なしに行わない
- `templates/ai-monorepo/` のサンプル実装を「本番品質でない」という理由で作り込まない。
  差し替えられる前提の最小構成である
