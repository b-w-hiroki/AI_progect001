# Lab 01 — サーバーレスAPI（Terraform）

**所要時間**: 1〜2時間
**費用**: ほぼ$0（DynamoDBオンデマンド + Lambda無料枠 + HTTP API $1/100万リクエスト）
**対応フェーズ**: [LEARNING_AWS.md](../../LEARNING_AWS.md) フェーズ1

レビューを投稿・取得するAPIを、Terraformだけで一式作る。
`IDEAS.md` #4「ECレビュー対応」のデータ受け口にあたる部分。

## 作るもの

```
クライアント
    │  POST /reviews  {product_id, rating, text}
    │  GET  /reviews?product_id=xxx
    ▼
API Gateway (HTTP API)
    │  AWS_PROXY 統合
    ▼
Lambda (Python 3.13)  ──────► CloudWatch Logs
    │  PutItem / Query
    ▼
DynamoDB  (PK: product_id, SK: created_at)
```

## 身につくこと

- **IAM**: 信頼ポリシーと権限ポリシーの違い。最小権限の書き方
- **Lambda**: パッケージング、環境変数、タイムアウトとメモリ
- **API Gateway**: HTTP API とLambda統合、リソースベースポリシー
- **DynamoDB**: 複合キー設計、Query と Scan の違い
- **CloudWatch Logs**: 保持期間の設定＝コスト管理
- **Terraform**: apply / destroy のライフサイクル、`archive_file` でのzip生成

---

## 事前準備

```bash
# 1. Terraform (>= 1.5)
terraform version

# 2. AWS CLI と認証情報
aws sts get-caller-identity   # アカウントIDが返ればOK

# 3. Budgets アラートを設定済みか確認（未設定なら先にやる）
```

> **他人と同じAWSアカウントを使う場合**、リソース名の衝突を避けるため
> `terraform.tfvars` に `project = "lab01-yourname"` を書いておく。

---

## 手順

### 1. デプロイ

```bash
cd labs/01-serverless-api

terraform init
terraform plan     # 何が作られるか必ず目を通す（12リソース程度）
terraform apply
```

`api_endpoint` が出力される。

### 2. 動作確認

```bash
API=$(terraform output -raw api_endpoint)

# レビューを投稿
curl -sS -X POST "$API/reviews" \
  -H 'Content-Type: application/json' \
  -d '{"product_id":"SKU-001","rating":5,"text":"梱包が丁寧で好印象でした"}'

# もう1件
curl -sS -X POST "$API/reviews" \
  -H 'Content-Type: application/json' \
  -d '{"product_id":"SKU-001","rating":2,"text":"到着が遅かった"}'

# 取得（新しい順）
curl -sS "$API/reviews?product_id=SKU-001"

# バリデーションの確認（400が返るはず）
curl -sS -X POST "$API/reviews" \
  -H 'Content-Type: application/json' \
  -d '{"product_id":"SKU-001","rating":99}'
```

### 3. ログを見る

```bash
aws logs tail "$(terraform output -raw log_group)" --follow
```

**動かない時はまずここを見る。** AWSのエラーメッセージには、どのプリンシパルがどのアクションで拒否されたかがほぼ必ず書いてある。

### 4. 壊して直す（ここが本番）

読むだけでは身につかないので、意図的に壊して復旧する。

**演習A: IAM権限を削る**
`main.tf` の `lambda_permissions` から `dynamodb:PutItem` を消して `apply`。
POSTすると500が返るはず。ログには `AccessDeniedException` が出る。
→ **権限ポリシー**が原因だと切り分けられるか？

**演習B: Lambda呼び出し許可を消す**
`aws_lambda_permission.api_gateway` をコメントアウトして `apply`。
今度はログにすら何も出ない。API Gateway側のログに `Internal Server Error` が出る。
→ こちらは**リソースベースポリシー**の問題。演習Aとの違いを説明できるか？

**演習C: Scanの罠を体験する**
`handler.py` の `list_reviews` で `product_id` 必須を外し、`table.scan()` に変える。
データが少ないうちは動く。しかし1万件入れたらどうなるか、なぜ実運用で使わないかを考える。

**演習D: タイムアウトを1秒にする**
`timeout = 1` にして `apply`。まだ動くはず。
フェーズ2でLLMを呼ぶとき、この値が3秒のままだと何が起きるかを想像する。

### 5. 採点する

演習で壊した状態から戻せているか、自分では気づきにくい。採点ツールにかける。

```bash
cd ../../tools/atlas && uv sync
uv run atlas check 01-serverless-api
```

未達成の項目名だけが出る。直し方は出ない。詰まったら1段ずつヒントを開く:

```bash
uv run atlas hint 01-serverless-api <検証項目のid>
```

`terraform` や AWS CLI が無い環境では、それを使う項目は「判定できません」となり
完了扱いにはならない。詳細は [tools/atlas/README.md](../../tools/atlas/README.md)。

### 6. 必ず片付ける

```bash
terraform destroy
```

**その日の作業が終わったら毎回実行する。** 翌日 `terraform apply` すれば2分で戻る。
これができるのがIaCの価値であり、消し忘れによる課金事故の唯一の予防策。

---

## 設計判断のメモ

**なぜ REST API (v1) でなく HTTP API (v2) か**
料金が約1/3、レイテンシも低い。v1にしかない機能（リクエスト検証、WAF直結など）は
個人開発の初期段階では要らない。必要になってから移ればいい。

**なぜ DynamoDB で RDS ではないか**
RDSは起動しているだけで月$15〜かかる。DynamoDBオンデマンドはリクエスト課金なので
使わなければ$0。学習中に消し忘れても事故にならない。
「複雑なJOINが必要」と分かった時点でRDSを検討すればいい。

**なぜ PK=product_id, SK=created_at か**
「ある商品のレビューを新しい順に取る」というアクセスパターンが先にあって、
それに合わせてキーを決めている。DynamoDBはRDBと逆で、**テーブル設計の前に
アクセスパターンを決める**。ここを間違えると後から Scan だらけになる。

**なぜロググループを明示的に作るか**
Lambdaは初回実行時に自動でロググループを作るが、その場合の保持期間は「無期限」。
学習用リソースを消してもログだけ残り、地味に課金され続ける。
明示的に作って `retention_in_days` を設定するのが正しい。

**なぜ `Action: "*"` を使わないか**
ワイルドカードで通してから絞る、は絞らないまま本番に行く。
最初から必要な権限だけ書いて、足りなければエラーを見て足す。
この順番だとIAMが自然に身につくうえ、事故らない。

---

## トラブルシューティング

| 症状 | 原因の見当 |
|---|---|
| `terraform apply` で権限エラー | 実行ユーザーのIAM権限不足。`aws sts get-caller-identity` で誰として実行しているか確認 |
| POST が 500、ログに `AccessDeniedException` | Lambdaロールの権限ポリシー不足 |
| POST が 500、Lambdaログが空 | `aws_lambda_permission` の設定漏れ、または統合設定のミス |
| POST が 404 | ルート定義（`route_key`）とURLパスの不一致 |
| ログが出ない | ロググループ名と関数名の不一致、または `logs:PutLogEvents` 権限なし |
| `ResourceNotFoundException` | 環境変数 `TABLE_NAME` がテーブル名と不一致 |

---

## 次のステップ

Lab 02 では、このLambdaから **Amazon Bedrock 経由で Claude** を呼び、
投稿されたレビューを自動分類する。そこで学ぶのは:

- Bedrockのモデルアクセス有効化とIAM権限（`bedrock:InvokeModel`）
- Lambdaの依存関係管理（`anthropic` SDK を Layer で入れる）
- タイムアウト・メモリの実測と調整
- 30秒を超える処理の非同期化

Bedrockでのモデル指定と呼び出し方は [LEARNING_AWS.md フェーズ2](../../LEARNING_AWS.md#フェーズ2-ai組み込み12週間) に記載済み。
