output "api_endpoint" {
  description = "APIのベースURL。curlでの動作確認に使う"
  value       = aws_apigatewayv2_api.this.api_endpoint
}

output "table_name" {
  description = "DynamoDBテーブル名"
  value       = aws_dynamodb_table.reviews.name
}

output "queue_url" {
  description = "classify Lambdaへのキュー。DLQと合わせて滞留を確認するときに使う"
  value       = aws_sqs_queue.classify.url
}

output "dlq_url" {
  description = "3回失敗したメッセージが溜まるDLQ。空でないなら分類が失敗し続けている"
  value       = aws_sqs_queue.classify_dlq.url
}

output "api_log_group" {
  description = "API Lambdaのロググループ"
  value       = aws_cloudwatch_log_group.api.name
}

output "classify_log_group" {
  description = "classify Lambdaのロググループ。Bedrock呼び出しのエラーはここに出る"
  value       = aws_cloudwatch_log_group.classify.name
}
