variable "region" {
  description = <<-EOT
    デプロイ先のAWSリージョン。
    Lab 1 は ap-northeast-1 固定だったが、このLabは us-east-1 をデフォルトにしている。
    Bedrockはリージョンごとに使えるモデルが違い、新しいモデルはまず us-east-1 に来ることが多いため
    （LEARNING_AWS.md フェーズ2 参照）。
  EOT
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "リソース名のプレフィックス。他人と同じAWSアカウントを使う場合は変更する"
  type        = string
  default     = "lab02-classify"
}

variable "log_retention_days" {
  description = "CloudWatch Logs の保持期間。学習用なので短くしてコストを抑える"
  type        = number
  default     = 7
}

variable "bedrock_model_id" {
  description = <<-EOT
    Bedrock上のモデルID。第一者APIのIDではなく `anthropic.` プレフィックス付きのIDを使う
    （LEARNING_AWS.md フェーズ2 参照）。分類のような軽量タスクなので haiku を既定にしている。
  EOT
  type        = string
  default     = "anthropic.claude-haiku-4-5"
}

variable "classify_timeout" {
  description = "classify Lambda のタイムアウト（秒）。LLM呼び出しは数秒〜十数秒かかるためデフォルト3秒では足りない"
  type        = number
  default     = 30
}
