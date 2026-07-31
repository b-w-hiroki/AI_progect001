output "api_endpoint" {
  description = "APIのベースURL。curlでの動作確認に使う"
  value       = aws_apigatewayv2_api.this.api_endpoint
}

output "table_name" {
  description = "DynamoDBテーブル名"
  value       = aws_dynamodb_table.reviews.name
}

output "log_group" {
  description = "Lambdaのロググループ名。aws logs tail で追える"
  value       = aws_cloudwatch_log_group.lambda.name
}
