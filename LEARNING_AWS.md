# AWS・インフラ 学習ロードマップ

対象: `IDEAS.md` のアイデアを自分で作って動かせるようになること
作成日: 2026-07-31

## この教材の考え方

AWSは資格本を読んでも身につかない。**作りたいものを題材にして、必要になった順に覚える**のが一番速い。

だからこのロードマップは「AWSのサービス一覧」ではなく、**`IDEAS.md` のプロダクトを1つ作るために必要な順番**で並べてある。各フェーズにハンズオン（`labs/`）が対応する。

もう一つの原則: **最初からコードでインフラを作る（IaC）**。マネジメントコンソールでポチポチ作ると、
- 何を作ったか忘れる
- 消し忘れて課金が続く
- 同じ環境を再現できない

の3つが必ず起きる。Terraform でコード化しておけば `terraform destroy` で全部消える。これは学習コストではなく、**学習を安全にするための投資**。

---

## 前提: 課金事故を防ぐ

これを最初にやる。順番を飛ばさない。

- [ ] ルートユーザーにMFAを設定。以降ルートは使わない
- [ ] 作業用IAMユーザー（or IAM Identity Center）を作成、MFA必須
- [ ] **Budgets で月$10のアラートを設定**（メール通知）
- [ ] Cost Explorer を有効化
- [ ] リージョンを1つに決める（東京 `ap-northeast-1`。Bedrockを使うなら `us-east-1` も併用）

> 個人学習で高額請求が出る典型は、**消し忘れたNAT Gateway（月$45〜）とRDS（月$15〜）**。この2つは「起動したまま寝る」を絶対にやらない。Lambda・DynamoDB・S3は使った分だけなので学習中はほぼ無料。

---

## フェーズ1: サーバーレスの土台（1〜2週間）

**ゴール**: HTTPリクエストを受けてデータを保存して返すAPIを、Terraformだけで作れる

| 学ぶこと | なぜ必要か |
|---|---|
| IAM（ロール・ポリシー・信頼関係） | AWSの全機能の土台。ここが曖昧だと後で必ず詰まる |
| Lambda | サーバー管理なしでコードを動かす。AIアプリのバックエンドの標準形 |
| API Gateway (HTTP API) | Lambdaを外部から叩けるようにする |
| DynamoDB | 起動費ゼロのDB。個人開発ではRDSより先にこっち |
| CloudWatch Logs | 動かない時に原因を見る唯一の手段。ログ保持期間の設定＝コスト管理 |
| Terraform | 上記すべてをコード化。`destroy` で確実に消す |

**ハンズオン**: [`labs/01-serverless-api/`](labs/01-serverless-api/) — レビュー投稿API

**この時点で作れるもの**: `IDEAS.md` #4（ECレビュー対応）のデータ受け口

**つまずきポイント**: IAMの「ロールは誰が引き受けるか（信頼ポリシー）」と「何ができるか（権限ポリシー）」が別物だと理解するまで混乱する。Lab 1 のREADMEで詳しく説明する。

---

## フェーズ2: AI組み込み（1〜2週間）

**ゴール**: Lambda から Claude を呼んで、結果を保存できる

| 学ぶこと | なぜ必要か |
|---|---|
| Amazon Bedrock | AWS内でClaudeを呼ぶ。IAMで権限管理でき、データがVPC外に出ない構成も取れる |
| Lambda の依存関係管理（Layer / コンテナイメージ） | SDKを使うと必ず必要になる。最初の壁 |
| Secrets Manager / Parameter Store | APIキーを環境変数にベタ書きしない |
| Lambda のタイムアウト・メモリ設計 | LLM呼び出しは数十秒かかる。デフォルト3秒では必ず落ちる |
| 非同期化（SQS or Step Functions） | 30秒を超える処理をAPI Gatewayの裏でやってはいけない |

**ハンズオン**: `labs/02-bedrock-classify/`（Lab 1 の拡張 — レビューを Claude で分類する）

### Bedrock でのモデル指定（重要）

Bedrock 上のモデルIDには `anthropic.` プレフィックスが付く。第一者APIのIDをそのまま書くと 400 になる。

| 用途 | Bedrock モデルID |
|---|---|
| 高難度・エージェント的な処理 | `anthropic.claude-opus-5` |
| バランス型（多くの用途の既定） | `anthropic.claude-sonnet-5` |
| 分類・要約など軽量・高速な処理 | `anthropic.claude-haiku-4-5` |

呼び出しには **Mantle クライアント**（Messages API 互換）を使う。旧 `bedrock-runtime` の `InvokeModel` 直叩きは非推奨。

```python
# pip install "anthropic[bedrock]"
from anthropic import AnthropicBedrockMantle

client = AnthropicBedrockMantle(aws_region="us-east-1")

message = client.messages.create(
    model="anthropic.claude-haiku-4-5",
    max_tokens=1024,
    system="レビューを positive / negative / neutral のいずれか1語で分類してください。",
    messages=[{"role": "user", "content": review_text}],
)
# content は TextBlock / ThinkingBlock などの配列。type を確認してから .text を読む
for block in message.content:
    if block.type == "text":
        print(block.text)
```

認証はIAMロール経由なのでAPIキー不要 — これがBedrockを使う最大の理由。Lambdaの実行ロールに `bedrock:InvokeModel` を、**特定のモデルARNに限定して**付ける。

> Bedrockは使う前にコンソールでモデルアクセスの有効化が必要。リージョンによって使えるモデルが違うので、`us-east-1` から始めるのが無難。

**この時点で作れるもの**: `IDEAS.md` #4 のプロトタイプが一通り動く

---

## フェーズ3: ちゃんと運用する（2〜3週間）

**ゴール**: 人に使わせても壊れない・気づける状態にする

| 学ぶこと | なぜ必要か |
|---|---|
| S3 + CloudFront | フロントエンドの配信。署名付きURLでファイル受け渡し |
| Cognito or 自前JWT | 認証。B2B SaaSなら避けて通れない |
| CloudWatch Alarms + SNS | エラー率・課金の異常に気づく |
| X-Ray（分散トレーシング） | 「どこで遅いか」を推測でなく事実で見る |
| GitHub Actions + OIDC | CIからAWSへ、**アクセスキーを置かずに**デプロイする |
| Terraform の state 管理（S3 + DynamoDB lock） | 複数人・複数マシンで作業する瞬間に必要になる |

**ハンズオン**: `labs/03-cicd-oidc/`（GitHub ActionsからOIDCでデプロイ）

**つまずきポイント**: OIDCの信頼ポリシーの条件（`sub` のマッチング）が細かい。ここでアクセスキーに逃げると、後で必ず漏洩リスクを抱える。

---

## フェーズ4: コストとスケール（継続）

**ゴール**: 「動く」から「利益が残る」へ

| 学ぶこと | なぜ必要か |
|---|---|
| LLMコストの可視化（トークン数のログ化） | AIプロダクトの原価の大半。測らないと値付けできない |
| プロンプトキャッシュ | 同じシステムプロンプトを繰り返す構成でコストが1/10になる |
| DynamoDB のキャパシティ設計 | オンデマンド→プロビジョンドで大幅に安くなる分岐点がある |
| Lambda の同時実行数制御 | 暴走時の課金ストッパー |
| タグ付け＋Cost Allocation Tags | 顧客ごと・機能ごとの原価が見える |

**この段階の問い**: 「1リクエストあたり何円かかっているか」を即答できるか。できないなら `IDEAS.md` の値付けは全部推測になる。

---

## 資格との対応（取るなら）

資格は目的ではないが、体系的な穴埋めには効く。**手を動かした後に取る**のが正しい順番。

| 資格 | 対応フェーズ | 所感 |
|---|---|---|
| Cloud Practitioner (CLF) | 前提〜フェーズ1 | 用語の地図として。実務価値は低いが最初の1冊としてはあり |
| Solutions Architect Associate (SAA) | フェーズ1〜3 | **最もコスパが良い。** 個人開発でも設計判断に直結する |
| Developer Associate (DVA) | フェーズ2〜3 | Lambda/DynamoDB中心。SAAと範囲が重なるので片方でよい |
| ML Engineer / AI Practitioner | フェーズ2以降 | Bedrock周りが範囲に入る。AI案件の営業材料としては有効 |

推奨: **SAA を1本だけ取る**。複数集めるより、そのぶんプロダクトを1つ完成させたほうが実力もマネタイズも進む。

---

## 進捗チェックリスト

### フェーズ1
- [ ] Budgets アラートを設定した
- [ ] Terraform で Lambda + API Gateway + DynamoDB を作れた
- [ ] `terraform destroy` で全部消えることを確認した
- [ ] IAMロールの信頼ポリシーと権限ポリシーの違いを説明できる
- [ ] CloudWatch Logs でエラーを追跡して自力で直した

### フェーズ2
- [ ] Bedrock のモデルアクセスを有効化した
- [ ] Lambda から Claude を呼べた
- [ ] Lambda の依存関係を Layer かコンテナで解決した
- [ ] タイムアウトとメモリを実測して調整した
- [ ] 30秒超の処理を非同期化した

### フェーズ3
- [ ] Terraform state を S3 に置いた
- [ ] GitHub Actions から OIDC でデプロイできた
- [ ] エラー率のアラートがSlack/メールに飛んだ
- [ ] 認証をかけて、認証なしリクエストが弾かれることを確認した

### フェーズ4
- [ ] 1リクエストあたりのコストを数字で言える
- [ ] プロンプトキャッシュのヒット率を計測した
- [ ] 月次コストを機能別に分解できる

---

## 学習の進め方（実践的な注意）

**1日の終わりに必ず `terraform destroy`。** 学習用リソースを起動したまま寝ない。翌日 `terraform apply` すれば2分で戻る。これができるのがIaCの価値。

**エラーは読む。** AWSのエラーメッセージは長いが、ほぼ必ず原因が書いてある。`AccessDenied` なら、どのプリンシパルがどのアクションを拒否されたかが本文にある。

**最小権限から始める。** `"Action": "*"` で通してから絞る、は絞らないまま本番に行く。最初から必要な権限だけ書いて、足りなければエラーを見て足す。この順番だとIAMが自然に身につく。

**動くまでの時間を短くする。** 完璧な設計より、まず1本通す。通ってから直す。

---

## 参考リンク

- [AWS 公式ドキュメント](https://docs.aws.amazon.com/ja_jp/)
- [Terraform AWS Provider リファレンス](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Amazon Bedrock ユーザーガイド](https://docs.aws.amazon.com/ja_jp/bedrock/)
- [AWS Well-Architected フレームワーク](https://aws.amazon.com/jp/architecture/well-architected/) — フェーズ3以降で読むと刺さる
