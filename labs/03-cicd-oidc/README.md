# Lab 03 — GitHub Actionsから OIDC でAWSへ（Terraform）

**所要時間**: 2〜3時間
**費用**: ほぼ$0（S3・DynamoDB・IAMは学習規模の使用量なら実質無料）
**対応フェーズ**: [LEARNING_AWS.md](../../LEARNING_AWS.md) フェーズ3
**前提**: [Lab 01](../01-serverless-api/) と [Lab 02](../02-bedrock-classify/) を完了していること

ここまでのLabは、学習者が自分のPCから `terraform apply` していた。
このLabでは、**アクセスキーを一切GitHubに置かずに**、GitHub ActionsからAWSの
状態を読める仕組み（OIDC）と、複数人・複数マシンでも安全に使えるTerraform
state管理（S3 + DynamoDBロック）を作る。

## 作るもの

```
bootstrap/ （最初に1回だけ apply。ここだけlocal state）
    S3バケット（tfstate置き場、バージョニング＋暗号化＋非公開）
    DynamoDBテーブル（stateロック）

labs/03-cicd-oidc/ （bootstrapの出力をbackendに使う）
    IAM OIDCプロバイダ（token.actions.githubusercontent.com）
    IAMロール "plan"（GitHub ActionsのPRからだけAssume可能、読み取り専用）

GitHub Actions（example-workflow.yml、手動でコピーして有効化）
    PR作成時に Lab 1 / Lab 2 の `terraform plan` を実行
    アクセスキー無し。id-token: write → role-to-assume でAWSの一時認証情報を取得
```

**このLabは `terraform apply` をCIに乗せない。** CIができるのは差分を見せる
`plan` まで。実際にAWSを変更する `apply` は、これまで通り学習者が手元で行う。
理由は「設計判断のメモ」に書く。

## 身につくこと

- **OIDC**: 長期アクセスキーを置かずにCIからAWSを認証する仕組みと、その裏側
- **IAM信頼ポリシーの条件**: `sub` claimでリポジトリ・イベント種別を絞り込む
- **Terraform state管理**: S3 backend + DynamoDBロック、`-backend-config` によるpartial configuration
- **段階的なブートストラップ**: 「state置き場を作るための構成」自体はどう管理するか
- **最小権限の設計**: 「読める」ロールと「変更できる」ロールを分離する

---

## 事前準備

```bash
# Lab 1 / Lab 2 の事前準備が済んでいること
terraform version
aws sts get-caller-identity
```

---

## 手順

### 0. state置き場をbootstrapする

```bash
cd labs/03-cicd-oidc/bootstrap

terraform init
terraform plan
terraform apply

terraform output
# state_bucket_name = "aws-learning-tfstate-123456789012"
# lock_table_name    = "aws-learning-locks"
```

この2つの値は後の手順で繰り返し使うので控えておく。

### 1. OIDCプロバイダとIAMロールを作る

```bash
cd ..   # labs/03-cicd-oidc/

cat > backend.hcl <<EOF
bucket         = "<bootstrapのstate_bucket_name>"
dynamodb_table = "<bootstrapのlock_table_name>"
region         = "ap-northeast-1"
EOF

terraform init -backend-config=backend.hcl

cat > terraform.tfvars <<EOF
state_bucket_name     = "<bootstrapのstate_bucket_name>"
state_lock_table_name = "<bootstrapのlock_table_name>"
EOF

terraform plan
terraform apply
```

`backend.hcl` と `terraform.tfvars` は別の目的のファイル。前者は
「このTerraform自身のstateをどこに置くか」、後者は「IAMロールにどのバケット・
テーブルへの読み取り権限を与えるか」。値は同じでも意味が違う。

```bash
terraform output -raw plan_role_arn
```

### 2. GitHubリポジトリ変数を設定する

出力された `plan_role_arn` を、GitHubリポジトリの
**Settings → Secrets and variables → Actions → Variables タブ**に
`AWS_DEPLOY_ROLE_ARN` として登録する（Secretsではなく**Variables**でよい —
ロールARN自体は秘匿情報ではない。信頼ポリシーの条件が実際の防御線）。

### 3. サンプルワークフローを試す

`example-workflow.yml` は `.github/workflows/` に自動配置されない
（未設定のまま有効化すると全PRでjobが失敗するため）。試す場合は:

```bash
cp labs/03-cicd-oidc/example-workflow.yml .github/workflows/terraform-plan.yml
```

コピーしてPRを作ると、Lab 1・Lab 2それぞれで `terraform plan` が走る。
ログの最初の方に、OIDCトークンを使って一時認証情報を取得したことを示す
出力が出る（アクセスキーがどこにも登場しないことを確認する）。

### 4. 壊して直す

**演習A: sub条件を緩める**
`main.tf` の `github_sub_condition` を `"repo:${var.github_repo}:*"` に変えて
`apply`。他のイベント（push等）からもAssumeできるようになる。
→ 元の `pull_request` 限定と何が違うか、影響範囲を説明できるか？

**演習B: 別リポジトリのふりをする**
（実際には試せないが）もし `github_repo` が別リポジトリを指していたら、
このリポジトリのGitHub Actionsは `AccessDenied` になる。信頼ポリシーの
`sub` 条件がどこで効いているか、`aws_iam_policy_document` を読んで説明する。

**演習C: OIDCプロバイダを重複作成してみる**
`create_oidc_provider = true` のまま、別のprojectで同じ内容を再度applyしようと
すると `EntityAlreadyExists` になる（1アカウントにつき1プロバイダ）。
2つ目からは `create_oidc_provider = false` にする必要がある理由を確認する。

**演習D: plan roleでapplyを試す**
（本番ではやらない）plan roleの権限には書き込み系アクションが無いことを
`main.tf` を読んで確認する。もし `dynamodb:PutItem` のようなアクションを
一時的に足して `apply` したら、このロールが実インフラを変更できてしまう
ことを理解する。演習後は必ず元に戻す。

### 5. 採点する

```bash
cd ../../tools/atlas && uv sync
uv run atlas check 03-cicd-oidc
```

### 6. 必ず片付ける

```bash
cd labs/03-cicd-oidc
terraform destroy -var-file=terraform.tfvars

cd bootstrap
terraform destroy
```

**bootstrapは最後に消す。** 順番を逆にすると、`labs/03-cicd-oidc` のstateが
置かれているバケット自体を先に消すことになり、destroy自体が失敗する。

---

## 設計判断のメモ

**なぜCIに `apply` を乗せないか**
このリポジトリの規約として「AWSリソースを作成する操作を確認なしに行わない」
がある（`CLAUDE.md`）。CIが自動でapplyできる構成にすると、PRを1つマージする
たびに無人でAWSへ変更が入ることになり、この規約と矛盾する。
「planで差分を人間が確認し、applyは手元で明示的に行う」を保ったまま、
アクセスキーを置かない恩恵（OIDC）だけを先に取り入れる、という順番にしている。
CI経由のapplyは、承認フロー（環境保護ルール等）まで含めて別途学ぶ話。

**なぜOIDCプロバイダを条件分岐で作るか**
AWSアカウントには同じURLのOIDCプロバイダを1つしか作れない。複数の学習用
プロジェクトで同じパターンを使うと2つ目以降で必ず衝突する。
`create_oidc_provider` で「新規作成」と「既存を参照」を切り替えられるように
しておくと、この教材をベースに次のプロジェクトを作るときにそのまま使える。

**なぜ `sub` 条件を `pull_request` に絞るか**
このロールはplan専用で、実際に何かを変更する力を持たない。それでも
「誰が・どのイベントでAssumeできるか」は狭いほど安全性の説明がしやすい。
push等の他イベントも含めたい場合は `local.github_sub_condition` の1行を
変えるだけで済むようにしてある。

**なぜ `state_bucket_name` / `state_lock_table_name` を変数にし、backendブロックには書かないか**
Terraformの `backend` ブロックは変数を参照できない（初期化より前に必要な情報の
ため）。だから接続先は `-backend-config` で外部から渡す。一方、IAMポリシーで
「このバケットだけ読める」と絞るには、Terraformの構成側で値を知っている必要が
あるので変数にする。同じ値を2箇所に書く不便さより、権限を絞れる安全性を取った。

**なぜ読み取り系のIAMポリシーで `Resource: "*"` を許しているか**
`logs:DescribeLogGroups` や `apigateway:GET` のような多くのDescribe/Get/List系
アクションは、AWS側がそもそもリソース単位の権限指定に対応していない。
書き込み系アクションを1つも含めていないので、Resourceを絞れなくても実害は
無い。**「Resourceを絞れない」と「絞る意味が無い」は違う** — このポリシーは
後者に該当することを自分で確認してから書く。

---

## トラブルシューティング

| 症状 | 原因の見当 |
|---|---|
| `EntityAlreadyExists`（OIDCプロバイダ） | 既に他のプロジェクトで作成済み。`create_oidc_provider = false` にする |
| GitHub ActionsのAssumeRoleが `AccessDenied` | `sub` 条件と実際のイベント種別（pull_request等）が一致していない |
| `terraform init` で `Backend configuration changed` | `-backend-config` の値がbootstrapの出力と一致しているか確認 |
| `terraform destroy` でS3バケットが消せない | バケットが空でない可能性。バージョニングで残った旧バージョンも含めて空にする必要がある |
| plan roleでの `terraform plan` が権限エラー | Lab 1/2で新しいリソース種別を足した場合、このLabのIAMポリシーにDescribe系アクションが無い可能性 |

---

## 次のステップ

これでフェーズ1〜3のハンズオンが揃った。次はフェーズ4「コストとスケール」——
LLM呼び出しのコストを可視化し、「1リクエストあたり何円か」を即答できる状態を
目指す。専用のLabは無く、Lab 1・Lab 2で作ったものに計測を足していく形になる。
詳細は [LEARNING_AWS.md フェーズ4](../../LEARNING_AWS.md#フェーズ4-コストとスケール継続) を参照。
