##############################################################################
# OIDC — GitHub ActionsがAWSの長期アクセスキーを持たずに認証する仕組み
#
# 仕組み: GitHub Actionsの実行中に、GitHub自身が署名した短命なIDトークンが
# 発行される。AWS側はそのトークンを「信頼するIDプロバイダ（OIDC）」として
# 登録しておいたGitHubの公開鍵で検証し、正しければ一時的な認証情報を渡す。
# アクセスキーをGitHub Secretsに置く必要が無くなる ＝ 漏洩リスクの高い
# 長期クレデンシャルが1つ減る。
##############################################################################

data "aws_caller_identity" "current" {}

# AWSアカウントに同じURLのOIDCプロバイダは1つしか作れない。
# 他のプロジェクトで既に作成済みの場合は var.create_oidc_provider = false にし、
# 既存のものをdata sourceで参照する。
resource "aws_iam_openid_connect_provider" "github" {
  count = var.create_oidc_provider ? 1 : 0

  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]

  # GitHubのOIDC証明書チェーンのthumbprint。GitHub公式ドキュメントに記載の値。
  # AWS側は現在この値によらずルートCAでの検証を行うが、リソース作成時の
  # 必須引数のため慣例的にこの値を設定する。
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

data "aws_iam_openid_connect_provider" "github" {
  count = var.create_oidc_provider ? 0 : 1
  url   = "https://token.actions.githubusercontent.com"
}

locals {
  github_oidc_provider_arn = var.create_oidc_provider ? (
    aws_iam_openid_connect_provider.github[0].arn
    ) : (
    data.aws_iam_openid_connect_provider.github[0].arn
  )

  # このリポジトリの pull_request イベントでだけ AssumeRole できるよう絞る。
  # "repo:${var.github_repo}:*" にすると同じリポジトリの push・release等
  # あらゆるイベントから引き受けられてしまう。plan専用ロールなので
  # 最も範囲の狭い pull_request に絞っている（README「設計判断のメモ」参照）。
  github_sub_condition = "repo:${var.github_repo}:pull_request"
}

##############################################################################
# IAM — GitHub Actionsが引き受けるロール（plan専用、apply権限は持たせない）
##############################################################################

data "aws_iam_policy_document" "github_actions_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [local.github_oidc_provider_arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = [local.github_sub_condition]
    }
  }
}

resource "aws_iam_role" "plan" {
  name                 = "${var.project}-plan-role"
  assume_role_policy   = data.aws_iam_policy_document.github_actions_assume_role.json
  max_session_duration = 3600
}

# 権限は「読む」ことと「stateのlockを取る」ことだけに絞る。
# terraform apply に要る書き込み権限は一切含めない —
# CIができるのは差分を見せることまでで、実際にAWSを変更する操作は
# 学習者が手元で terraform apply するときだけ、という設計（README参照）。
data "aws_iam_policy_document" "plan_permissions" {
  statement {
    sid    = "ReadOnlyDescribeAcrossLabs"
    effect = "Allow"
    actions = [
      "dynamodb:DescribeTable",
      "lambda:GetFunction",
      "lambda:GetFunctionCodeSigningConfig",
      "lambda:GetLayerVersion",
      "lambda:ListLayerVersions",
      "lambda:GetEventSourceMapping",
      "lambda:ListEventSourceMappings",
      "apigateway:GET",
      "logs:DescribeLogGroups",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:ListRolePolicies",
      "iam:ListAttachedRolePolicies",
    ]
    # これらのDescribe/Get/List系アクションの大半はIAM側でリソース単位の
    # 権限指定に対応していない（AWSの仕様）。書き込み系アクションは
    # 1つも含めていないので、Resourceを絞れなくても実害は無い。
    resources = ["*"]
  }

  statement {
    sid    = "StateBucketRead"
    effect = "Allow"
    actions = [
      "s3:GetObject",
    ]
    resources = ["arn:aws:s3:::${var.state_bucket_name}/*"]
  }

  statement {
    sid    = "StateLockTable"
    effect = "Allow"
    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:DeleteItem",
    ]
    # ロックテーブルへの書き込みだけは許可する。plan中もロックの取得・解放で
    # PutItem/DeleteItemが必要になる。「実インフラは変更できないが、
    # ロックテーブルは書ける」という非対称さがこのロールの肝。
    resources = ["arn:aws:dynamodb:${var.region}:${data.aws_caller_identity.current.account_id}:table/${var.state_lock_table_name}"]
  }
}

resource "aws_iam_role_policy" "plan" {
  name   = "${var.project}-plan-policy"
  role   = aws_iam_role.plan.id
  policy = data.aws_iam_policy_document.plan_permissions.json
}
