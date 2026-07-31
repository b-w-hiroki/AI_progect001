##############################################################################
# DynamoDB — レビューの保存先
#
# PK = product_id, SK = created_at の複合キー。
# 「ある商品のレビューを新しい順に取る」というアクセスパターンに合わせて設計している。
# DynamoDBはRDBと違い、先にアクセスパターンを決めてからキーを決める。
##############################################################################

resource "aws_dynamodb_table" "reviews" {
  name         = "${var.project}-reviews"
  billing_mode = "PAY_PER_REQUEST" # 学習用途では実質無料。事前のキャパシティ見積もり不要
  hash_key     = "product_id"
  range_key    = "created_at"

  attribute {
    name = "product_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }
}

##############################################################################
# IAM — ここがAWSの肝
#
# ロールには2種類のポリシーが必要。混同しやすいので区別すること:
#   1. 信頼ポリシー (assume_role_policy) = 「誰がこのロールを引き受けられるか」
#   2. 権限ポリシー (aws_iam_role_policy) = 「引き受けた者が何をできるか」
#
# 片方だけでは動かない。AccessDenied が出たらまずどちらの話か切り分ける。
##############################################################################

# 1. 信頼ポリシー: Lambdaサービスだけがこのロールを引き受けられる
data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.project}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

# 2. 権限ポリシー: 最小権限。
#    ログ書き込みと、このテーブルへのPut/Queryのみ。ワイルドカードは使わない。
data "aws_iam_policy_document" "lambda_permissions" {
  statement {
    sid    = "WriteLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.lambda.arn}:*"]
  }

  statement {
    sid    = "ReviewTableAccess"
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:Query",
    ]
    resources = [aws_dynamodb_table.reviews.arn]
  }
}

resource "aws_iam_role_policy" "lambda" {
  name   = "${var.project}-lambda-policy"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda_permissions.json
}

##############################################################################
# CloudWatch Logs
#
# Lambdaは初回実行時にロググループを自動作成するが、その場合 retention が
# 「無期限」になり、消し忘れると地味に課金が続く。
# 明示的に作って保持期間を設定するのが正しい作法。
##############################################################################

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project}-api"
  retention_in_days = var.log_retention_days
}

##############################################################################
# Lambda
#
# src/ ディレクトリをTerraformがその場でzipにする。
# 外部依存なし（boto3はLambdaランタイムに同梱）なので pip install 不要。
# 依存関係が必要になるフェーズ2で、Layer / コンテナイメージを学ぶ。
##############################################################################

data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/build/lambda.zip"
}

resource "aws_lambda_function" "api" {
  function_name = "${var.project}-api"
  role          = aws_iam_role.lambda.arn

  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256

  runtime = "python3.13"
  handler = "handler.handler"

  timeout     = 10  # デフォルトは3秒。LLMを呼ぶフェーズ2では60秒以上に上げる
  memory_size = 256 # メモリを上げるとCPUも比例して上がる。速度が要るなら増やす

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.reviews.name
    }
  }

  # ロググループを先に作らせる。これがないと Lambda が勝手に作ってしまう
  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy.lambda,
  ]
}

##############################################################################
# API Gateway (HTTP API)
#
# REST API (v1) ではなく HTTP API (v2) を使う。
# 機能は少ないが、約1/3の料金で、個人開発で必要なものは揃っている。
##############################################################################

resource "aws_apigatewayv2_api" "this" {
  name          = "${var.project}-http-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "post_review" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "POST /reviews"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "get_reviews" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "GET /reviews"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      responseLength = "$context.responseLength"
      errorMessage   = "$context.error.message"
    })
  }
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/apigateway/${var.project}"
  retention_in_days = var.log_retention_days
}

# API Gateway が Lambda を呼ぶ許可。
# 上のIAMロールとは向きが逆（リソースベースポリシー）。これを忘れると 500 が返る。
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowInvokeFromApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}
