##############################################################################
# DynamoDB — レビューの保存先
#
# Lab 1 と同じキー設計（PK=product_id, SK=created_at）。
# sentiment はスキーマに含めない — DynamoDBはキー以外の属性を宣言不要で持てる
# （スキーマレス）ので、classify Lambda が後から UpdateItem で足すだけでよい。
##############################################################################

resource "aws_dynamodb_table" "reviews" {
  name         = "${var.project}-reviews"
  billing_mode = "PAY_PER_REQUEST"
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
# SQS — API Lambda と classify Lambda を疎結合にする
#
# なぜ同期呼び出しにしないか: API Gatewayの統合タイムアウトは最大29秒、
# LLM呼び出しは数秒〜十数秒かかりぶれもある。POSTの応答をLLMの完了待ちにすると、
# 混雑時にタイムアウトしてレビュー自体の保存まで失敗して見える。
# 「保存は同期・分類は非同期」に分けると、POSTは常に速く返る。
##############################################################################

resource "aws_sqs_queue" "classify_dlq" {
  name = "${var.project}-dlq"
  # DLQ自体にも保持期間はあるが、ここでは既定値（4日）のままにしている。
  # 「分類が失敗し続けているメッセージが溜まっている」ことに気づくのが目的で、
  # 溜めっぱなしにするための仕組みではない。
}

resource "aws_sqs_queue" "classify" {
  name = "${var.project}-queue"

  # 可視性タイムアウトは classify Lambda のタイムアウトより長く取る。
  # 短いと、Lambdaがまだ処理中なのに「失敗した」とみなされて別ワーカーに
  # 再配信され、同じレビューを二重にBedrockへ投げる（コストが倍になる）。
  visibility_timeout_seconds = var.classify_timeout + 10

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.classify_dlq.arn
    # 3回失敗したメッセージはDLQへ。モデルIDの誤りなど「リトライしても直らない」
    # 失敗を無限リトライさせないための上限。
    maxReceiveCount = 3
  })
}

##############################################################################
# IAM — API Lambda（レビュー保存 + キュー投入）
##############################################################################

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

resource "aws_iam_role" "api" {
  name               = "${var.project}-api-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "api_permissions" {
  statement {
    sid    = "WriteLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.api.arn}:*"]
  }

  statement {
    sid    = "ReviewTableWrite"
    effect = "Allow"
    actions = [
      "dynamodb:PutItem",
      "dynamodb:Query",
    ]
    resources = [aws_dynamodb_table.reviews.arn]
  }

  statement {
    sid    = "EnqueueClassifyJob"
    effect = "Allow"
    actions = [
      "sqs:SendMessage",
    ]
    resources = [aws_sqs_queue.classify.arn]
  }
}

resource "aws_iam_role_policy" "api" {
  name   = "${var.project}-api-policy"
  role   = aws_iam_role.api.id
  policy = data.aws_iam_policy_document.api_permissions.json
}

##############################################################################
# IAM — classify Lambda（Bedrock呼び出し + 結果の書き戻し）
#
# API Lambda とロールを分けている。classify だけが bedrock:InvokeModel を持ち、
# API Lambda は持たない。どちらか一方が乗っ取られても被害範囲が広がらない。
##############################################################################

resource "aws_iam_role" "classify" {
  name               = "${var.project}-classify-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

data "aws_iam_policy_document" "classify_permissions" {
  statement {
    sid    = "WriteLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.classify.arn}:*"]
  }

  statement {
    sid    = "UpdateReviewSentiment"
    effect = "Allow"
    actions = [
      "dynamodb:UpdateItem",
    ]
    resources = [aws_dynamodb_table.reviews.arn]
  }

  statement {
    sid    = "ConsumeClassifyQueue"
    effect = "Allow"
    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
    ]
    resources = [aws_sqs_queue.classify.arn]
  }

  statement {
    sid    = "InvokeClassifyModel"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
    ]
    # モデルARNを特定の1モデルに限定する。"*" にすると、他の高価なモデルや
    # 将来追加されるモデルまで呼べてしまい、コストの上限が読めなくなる。
    resources = ["arn:aws:bedrock:${var.region}::foundation-model/${var.bedrock_model_id}"]
  }
}

resource "aws_iam_role_policy" "classify" {
  name   = "${var.project}-classify-policy"
  role   = aws_iam_role.classify.id
  policy = data.aws_iam_policy_document.classify_permissions.json
}

##############################################################################
# CloudWatch Logs
##############################################################################

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${var.project}-api"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "classify" {
  name              = "/aws/lambda/${var.project}-classify"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "apigateway" {
  name              = "/aws/apigateway/${var.project}"
  retention_in_days = var.log_retention_days
}

##############################################################################
# Lambda Layer — anthropic SDK
#
# Lab 1 は外部依存が無かった（boto3はランタイム同梱）ので直接zip化していた。
# ここでは anthropic[bedrock] という外部SDKが要る。関数コードと分けてLayerに
# 入れておくと、依存関係の更新と自分のコードの更新を別々にデプロイできる。
#
# layer/python/ は学習者が手元でビルドする（READMEの「0. レイヤーの準備」参照）。
# Lambdaが読める配置にするには zip 直下に python/ ディレクトリが必要 —
# これはPythonランタイムがLayerを /opt に展開したとき、/opt/python が
# 自動的にimportパスに乗るという仕様に合わせるため。
##############################################################################

data "archive_file" "layer" {
  type        = "zip"
  source_dir  = "${path.module}/layer"
  output_path = "${path.module}/build/layer.zip"
  excludes    = ["requirements.txt"]
}

resource "aws_lambda_layer_version" "anthropic_sdk" {
  layer_name          = "${var.project}-anthropic-sdk"
  filename            = data.archive_file.layer.output_path
  source_code_hash    = data.archive_file.layer.output_base64sha256
  compatible_runtimes = ["python3.13"]
}

##############################################################################
# Lambda — API（レビューの保存 + キュー投入）
#
# Lab 1 のhandlerを拡張している。LLM呼び出しをしないのでタイムアウトはLab 1と同じ
# 10秒のまま — 「LLMを呼ぶ処理」と「呼ばない処理」でタイムアウトを分けるのが、
# このLabのSQS分離の一番の効能。
##############################################################################

data "archive_file" "api" {
  type        = "zip"
  source_dir  = "${path.module}/src/api"
  output_path = "${path.module}/build/api.zip"
}

resource "aws_lambda_function" "api" {
  function_name = "${var.project}-api"
  role          = aws_iam_role.api.arn

  filename         = data.archive_file.api.output_path
  source_code_hash = data.archive_file.api.output_base64sha256

  runtime = "python3.13"
  handler = "handler.handler"

  timeout     = 10
  memory_size = 256

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.reviews.name
      QUEUE_URL  = aws_sqs_queue.classify.url
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.api,
    aws_iam_role_policy.api,
  ]
}

##############################################################################
# Lambda — classify（Bedrockでレビューを分類し、結果を書き戻す）
#
# タイムアウトとメモリはLab 1より大きい。LLM呼び出しは数秒〜十数秒かかり、
# SDKの初期化やレスポンス処理にもLab 1のCRUDよりメモリを使う。
# 「動かしてみて実測して調整する」がフェーズ2の目標のひとつなので、
# この値は出発点として決め打ちしている — READMEの演習で実測して調整する。
##############################################################################

data "archive_file" "classify" {
  type        = "zip"
  source_dir  = "${path.module}/src/classify"
  output_path = "${path.module}/build/classify.zip"
}

resource "aws_lambda_function" "classify" {
  function_name = "${var.project}-classify"
  role          = aws_iam_role.classify.arn

  filename         = data.archive_file.classify.output_path
  source_code_hash = data.archive_file.classify.output_base64sha256

  runtime = "python3.13"
  handler = "handler.handler"
  layers  = [aws_lambda_layer_version.anthropic_sdk.arn]

  timeout     = var.classify_timeout
  memory_size = 512

  environment {
    variables = {
      TABLE_NAME       = aws_dynamodb_table.reviews.name
      BEDROCK_MODEL_ID = var.bedrock_model_id
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.classify,
    aws_iam_role_policy.classify,
  ]
}

# SQS → classify Lambda のトリガー設定。
# batch_size は 1 に固定。バッチを大きくすると、1件のLLM失敗が他の正常な
# メッセージまで巻き込んで再試行させてしまう（部分バッチ失敗の応答を実装すれば
# 回避できるが、このLabのスコープ外 — READMEの「次のステップ」に書く）。
resource "aws_lambda_event_source_mapping" "classify" {
  event_source_arn = aws_sqs_queue.classify.arn
  function_name    = aws_lambda_function.classify.arn
  batch_size       = 1
}

##############################################################################
# API Gateway (HTTP API) — Lab 1 と同じ構成
##############################################################################

resource "aws_apigatewayv2_api" "this" {
  name          = "${var.project}-http-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "api" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "post_review" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "POST /reviews"
  target    = "integrations/${aws_apigatewayv2_integration.api.id}"
}

resource "aws_apigatewayv2_route" "get_reviews" {
  api_id    = aws_apigatewayv2_api.this.id
  route_key = "GET /reviews"
  target    = "integrations/${aws_apigatewayv2_integration.api.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "$default"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.apigateway.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      responseLength = "$context.responseLength"
      errorMessage   = "$context.error.message"
    })
  }
}

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowInvokeFromApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}
