variable "region" {
  description = "デプロイ先のAWSリージョン"
  type        = string
  default     = "ap-northeast-1"
}

variable "project" {
  description = "リソース名のプレフィックス。他人と同じAWSアカウントを使う場合は変更する"
  type        = string
  default     = "aws-learning"
}
