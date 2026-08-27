output "state_bucket_name" {
  description = "S3 backend の bucket に指定する値。terraform init -backend-config に使う"
  value       = aws_s3_bucket.tfstate.bucket
}

output "lock_table_name" {
  description = "S3 backend の dynamodb_table に指定する値"
  value       = aws_dynamodb_table.lock.name
}

output "account_id" {
  description = "このAWSアカウントのID。他のLabのIAMポリシーでARNを組み立てる際に使える"
  value       = data.aws_caller_identity.current.account_id
}
