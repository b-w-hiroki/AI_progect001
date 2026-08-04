# atlas — インフラ学習用のレッスン採点ツール

`labs/` のハンズオンを**採点する**CLI。「できたつもり」を潰すために作った。

チュートリアルは手順を写すだけで終わってしまう。写経しても、
IAMの権限を絞れているか、ログ保持期間を設定したか、消し忘れが無いかは分からない。
atlas は成果物を実際に検査して、**何が未達成かだけを**返す。直し方は返さない。

## 教育方針

| 方針 | 実装 |
|---|---|
| 答えを写させない | `check` は未達成項目のタイトルしか出さない。修正方法は出さない |
| 詰まったら助ける | `hint` で1段ずつ開示。学習者が要求した分だけ出る |
| 判定できないものを合格にしない | AWS未接続の項目は SKIPPED。完了扱いにはならない |
| 無料・オフラインで大半を回せる | 静的検査（ファイル内容・`terraform validate`）が中心 |

## 使い方

```bash
cd tools/atlas
uv sync

uv run atlas list                       # レッスン一覧
uv run atlas show 01-serverless-api     # 到達目標と検証項目
uv run atlas check 01-serverless-api    # 採点（未達成なら終了コード1）
uv run atlas hint 01-serverless-api log-retention-set   # ヒントを1段開く
uv run atlas progress                   # 進捗
```

`atlas check` はレッスンの `target_dir`（例: `labs/01-serverless-api`）を検査する。
別の場所で作業しているなら `--dir` で上書きする。

進捗はリポジトリルートの `.atlas/progress.json` に保存される。gitignore 済み。

### 出力の例

IAMをワイルドカードに戻し、ログ保持期間を消した状態を採点した実際の出力
（terraform / AWS CLI が入っていない環境で実行したもの）:

```
01-serverless-api  サーバーレスAPIをTerraformで構築する
対象: /path/to/labs/01-serverless-api

  ⏭️  Terraformが整形されている
      terraform がインストールされていません
  ✅ Lambda関数が定義されている
  ✅ DynamoDBテーブルが定義されている
  ❌ ロググループに保持期間が設定されている
      main.tf に想定の記述が見つかりません
  ❌ IAMポリシーにワイルドカードが無い
      main.tf:40 に禁止パターンがあります
  ❌ IAMポリシーのResourceが限定されている
      main.tf:64 に禁止パターンがあります
  ⏭️  Terraformの構成が妥当である
      terraform がインストールされていません
  ⏭️  DynamoDBテーブルが実際に作成されている
      AWS CLI がインストールされていません

  2/8 達成
  3件は判定できませんでした（未達成として扱います）

次に取り組む項目:
  - ロググループに保持期間が設定されている
      atlas hint 01-serverless-api log-retention-set   （ヒント残り3段）
  - IAMポリシーにワイルドカードが無い
      atlas hint 01-serverless-api no-wildcard-action   （ヒント残り3段）
  - IAMポリシーのResourceが限定されている
      atlas hint 01-serverless-api no-wildcard-resource   （ヒント残り3段）
```

未達成があれば終了コードは1。何が悪いかは出ても、どう直すかは出ないことに注目。

## レッスンを追加する

レッスンは `lessons/*.yaml` の**データ**。コードは書かなくてよい。
ファイル名の拡張子を除いた部分が `id` と一致している必要がある。

```yaml
id: 02-example
title: レッスン名
summary: 1〜2行の説明
target_dir: labs/02-example     # リポジトリルートからの相対パス
reference: labs/02-example/README.md

objectives:
  - 到達目標

checks:
  - id: has-log-retention
    title: ロググループに保持期間が設定されている
    type: file_matches
    path: main.tf
    pattern: 'retention_in_days'
    hints:
      - 方向だけ示す
      - 仕組みを説明する
      - 具体的な手順を示す（完成コードは書かない）
```

### 検証の種類

| type | パラメータ | 用途 |
|---|---|---|
| `file_exists` | `path` | ファイルの存在 |
| `file_matches` | `path`, `pattern` | 必要な記述があるか（正規表現） |
| `file_not_matches` | `path`, `pattern` | 禁止事項が無いか。失敗時は行番号を出す |
| `command_succeeds` | `command`（文字列の配列） | 終了コード0を合格とする |
| `aws_resource_exists` | `command`, `requires_aws: true` | 実リソースの存在。認証情報が無ければ SKIPPED |

`path` は `target_dir` の外を指せない。`command` は配列で渡す（シェルを介さない）。

### レッスン定義の検証

読み込み時に厳しく検証している。教材の書き間違いを、学習者の採点結果ではなく
**教材作成者へのエラー**として返すため。

- `id` がファイル名と一致すること
- `checks` が1つ以上あること、`id` が重複しないこと
- **すべての check に `hints` が1つ以上あること**
  （ヒントの無い検証は、失敗した学習者に打つ手が残らない）

`type` の誤りなど実行時にしか分からない不備は、その項目を SKIPPED にして
「レッスン定義の不備」と表示する。学習者の失敗と混ざらないようにするため。

## 開発

```bash
cd tools/atlas
uv run pytest        # テスト47件
uv run ruff check .
uv run mypy          # strict
```

## 制約

- `terraform` / `aws` が無い環境では、それらを使う項目は SKIPPED になり、
  レッスンは完了にならない。判定できないものを合格にしない方針のため
- `aws_resource_exists` はリソースの存在しか見ない。設定内容までは検証していない
- 検査は正規表現ベース。HCLとして構文解析はしていないので、
  コメントアウトされた記述にもマッチする
