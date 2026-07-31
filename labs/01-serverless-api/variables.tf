variable "region" {
  description = "デプロイ先のAWSリージョン"
  type        = string
  default     = "ap-northeast-1"
}

variable "project" {
  description = "リソース名のプレフィックス。他人と同じAWSアカウントを使う場合は変更する"
  type        = string
  default     = "lab01-reviews"
}

variable "log_retention_days" {
  description = "CloudWatch Logs の保持期間。学習用なので短くしてコストを抑える"
  type        = number
  default     = 7
}
