# Lab 02 — Bedrock でレビューを自動分類する（Terraform）

**所要時間**: 2〜3時間
**費用**: ほぼ$0（Lambda・DynamoDB・SQSは無料枠の範囲）＋ Bedrock呼び出し分（Haikuで1回あたり1円未満〜数円程度）
**対応フェーズ**: [LEARNING_AWS.md](../../LEARNING_AWS.md) フェーズ2
**前提**: [Lab 01](../01-serverless-api/) を一度完了していること（このLabはLab 1の拡張）

Lab 1 のレビュー投稿APIを拡張し、投稿されたレビューを **Amazon Bedrock 経由の Claude** で
positive / negative / neutral に自動分類する。

## 作るもの

```
クライアント
    │  POST /reviews  {product_id, rating, text}
    ▼
API Gateway (HTTP API)
    ▼
Lambda: api (Python 3.13) ─────────► CloudWatch Logs
    │  1. PutItem（sentiment=null で即保存）
    │  2. SQSへメッセージ送信
    ▼
SQS queue ──(3回失敗)──► DLQ
    │
    ▼
Lambda: classify (Python 3.13, Layer: anthropic SDK)
    │  1. Bedrock (Claude) を呼んで分類
    │  2. UpdateItem で sentiment を書き戻す
    ▼
DynamoDB (Lab 1 と同じテーブル設計を拡張)
```

POSTの応答は「保存できたか」だけを返す。分類は裏で非同期に進み、少し待ってから
`GET /reviews` すると `sentiment` が埋まっている。

## 身につくこと

- **Bedrock**: モデルアクセスの有効化、`anthropic.` プレフィックス付きモデルID、IAMでの権限管理
- **IAM**: 用途ごとにロールを分け、`bedrock:InvokeModel` を特定のモデルARNだけに絞る
- **Lambda Layer**: 外部SDK依存を関数コードから切り離す。ビルド時のプラットフォーム指定
- **SQS**: Lambda間の疎結合、可視性タイムアウトとLambdaタイムアウトの関係、DLQでの失敗の可視化
- **タイムアウト・メモリ設計**: LLM呼び出しを含む関数と含まない関数で値を分ける理由

---

## 事前準備

```bash
# Lab 1 の事前準備（Terraform / AWS CLI / Budgets）が済んでいること

# Bedrockのモデルアクセスを有効化する（コンソール操作）
# AWS Console → Bedrock → Model access → 対象モデルを有効化
# リージョンは us-east-1（このLabのデフォルト）で行う

# ビルドにPython 3.13相当のpipが使える環境
python3 --version
```

> **他人と同じAWSアカウントを使う場合**、`terraform.tfvars` に
> `project = "lab02-yourname"` を書いておく。

---

## 手順

### 0. レイヤーの準備

classify Lambda が使う `anthropic[bedrock]` SDKを、Lambdaの実行環境（Linux x86_64）向けに
ビルドする。**手元のOSがLinuxでなくても**、pipのプラットフォーム指定で対応できる。

```bash
cd labs/02-bedrock-classify

pip install \
  --platform manylinux2014_x86_64 \
  --target layer/python \
  --implementation cp \
  --python-version 3.13 \
  --only-binary=:all: \
  -r layer/requirements.txt
```

`layer/python/` にパッケージが展開されていれば成功。このディレクトリは `.gitignore` 済み
（依存関係はコミットしない）。

### 1. デプロイ

```bash
terraform init
terraform plan     # 何が作られるか必ず目を通す（20リソース程度。Lab 1より多い）
terraform apply
```

### 2. 動作確認

```bash
API=$(terraform output -raw api_endpoint)

curl -sS -X POST "$API/reviews" \
  -H 'Content-Type: application/json' \
  -d '{"product_id":"SKU-001","rating":5,"text":"梱包が丁寧で、届くのも早くて大満足でした"}'

# すぐ取得すると sentiment はまだ null
curl -sS "$API/reviews?product_id=SKU-001"

# 数秒待ってから再度取得すると sentiment が埋まっているはず
sleep 5
curl -sS "$API/reviews?product_id=SKU-001"
```

### 3. ログを見る

```bash
# API Lambda（保存とキュー投入）
aws logs tail "$(terraform output -raw api_log_group)" --follow

# classify Lambda（Bedrock呼び出しと書き戻し）— 別ターミナルで
aws logs tail "$(terraform output -raw classify_log_group)" --follow
```

DLQにメッセージが溜まっていないかも確認する。

```bash
aws sqs get-queue-attributes \
  --queue-url "$(terraform output -raw dlq_url)" \
  --attribute-names ApproximateNumberOfMessages
```

### 4. 壊して直す

**演習A: モデルIDを間違える**
`variables.tf` の `bedrock_model_id` を存在しないIDに変えて `apply`。
`classify` のログに `ValidationException` が出て、DLQにメッセージが溜まり始める。
→ Bedrockのエラーは「権限」と「モデル指定」のどちらが原因か切り分けられるか？

**演習B: Bedrock権限を外す**
`classify_permissions` の `InvokeClassifyModel` ステートメントをコメントアウトして `apply`。
`AccessDeniedException` が出る。演習Aとログの違いを比較する。

**演習C: 可視性タイムアウトを短くする**
`visibility_timeout_seconds` を `5` にして `apply`（`classify_timeout` の30秒よりずっと短い）。
処理中のメッセージが「失敗した」とみなされ再配信され、同じレビューが2回classifyされる
（ログのタイムスタンプが近い重複呼び出しとして見える）。
→ なぜ可視性タイムアウトはLambdaのタイムアウトより長くする必要があるか説明できるか？

**演習D: バッチサイズを増やす**
`aws_lambda_event_source_mapping.classify` の `batch_size` を `10` にして `apply`。
1件のレビューでBedrockが失敗すると、同じバッチの他9件も再試行対象になる
（部分バッチ失敗の応答を実装すれば防げる — このLabのスコープ外）。

### 5. 採点する

```bash
cd ../../tools/atlas && uv sync
uv run atlas check 02-bedrock-classify
```

詰まったら `uv run atlas hint 02-bedrock-classify <検証項目のid>`。

### 6. 必ず片付ける

```bash
terraform destroy
```

DLQ・SQS・Layerもすべて `destroy` の対象。取り残しは無い。

---

## 設計判断のメモ

**なぜ同期でBedrockを呼ばないか**
API Gatewayの統合タイムアウトは最大29秒。LLM呼び出しは速いときも遅いときもあり、
混雑時にタイムアウトするとレビューの保存自体が失敗して見える。
「保存は同期・分類は非同期」に分けると、POSTの応答は常に速く、分類の遅延は
ユーザーの操作をブロックしない。

**なぜSQSでDLQを設定するか**
モデルIDの誤りのような「リトライしても直らない失敗」を無限に再試行させないため。
DLQにメッセージが溜まっていること自体が「分類が壊れている」というアラートになる
（本番ならCloudWatch AlarmでDLQのメッセージ数を監視する。フェーズ3で扱う）。

**なぜIAMロールをLambdaごとに分けるか**
`api` はBedrockを呼ぶ必要が無く、`classify` はSQSへの送信権限が要らない。
1つのロールにまとめると「本当は要らない権限」が積み重なっていく。
どちらかが乗っ取られたときの被害範囲がロールを割った分だけ狭くなる。

**なぜモデルIDをARNで絞るか**
`bedrock:InvokeModel` を `Resource: "*"` にすると、Opus のような高価なモデルまで
呼べてしまう。呼び出しコードにHaikuと書いてあっても、IAM側で絞っていなければ
「本来呼べないはずのモデルを呼べる」状態は変わらない。権限は呼び出し側のコードでなく
ポリシー側で制限する。

**なぜLambda Layerに分けるか**
`anthropic[bedrock]` のような外部SDKは、自分のハンドラコードより更新頻度が低い。
zipに混ぜて固めると、ハンドラの1行修正のたびに数十MBの依存関係を含んだzipを
作り直してデプロイすることになる。Layerに分ければ、依存関係の更新と
ハンドラコードの更新を別々にデプロイできる。

**なぜus-east-1をデフォルトにしたか**
Bedrockは新しいモデルがまず `us-east-1` に来ることが多い。Lab 1の `ap-northeast-1`
のままだと、モデルがまだそのリージョンで使えない可能性がある。

---

## トラブルシューティング

| 症状 | 原因の見当 |
|---|---|
| `terraform apply` で Bedrock関連のエラー | モデルアクセスをコンソールで有効化していない |
| classifyログに `AccessDeniedException` | IAMの `InvokeClassifyModel` ステートメント不足、またはモデルARNの不一致 |
| classifyログに `ValidationException` | `bedrock_model_id` の綴りが誤っている、そのリージョンでモデルが未提供 |
| `sentiment` がいつまでもnull | classify Lambdaのログを確認。SQSに届いていなければAPI Lambda側のログも確認 |
| DLQにメッセージが溜まる | 分類が繰り返し失敗している。classifyログの直近のエラーを確認 |
| Layerが反映されない | `layer/python/` が空。手順0を実行したか確認 |
| `terraform apply` は成功するがimportエラー | Layerのビルドが実行環境（Linux x86_64）向けになっていない可能性。手順0のコマンドを再確認 |

---

## 次のステップ

Lab 03 では、ここまで手動で `terraform apply` していたデプロイを
**GitHub Actions から OIDC で** 自動化する。アクセスキーを一切置かずにCIからAWSへ
デプロイする方法と、Terraform stateをS3で共有管理する方法を扱う。

詳細は [LEARNING_AWS.md フェーズ3](../../LEARNING_AWS.md#フェーズ3-ちゃんと運用する23週間) に記載。
