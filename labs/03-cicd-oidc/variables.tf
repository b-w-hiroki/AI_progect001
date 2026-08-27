variable "region" {
  description = "デプロイ先のAWSリージョン"
  type        = string
  default     = "ap-northeast-1"
}

variable "project" {
  description = "リソース名のプレフィックス。他人と同じAWSアカウントを使う場合は変更する"
  type        = string
  default     = "lab03-cicd"
}

variable "github_repo" {
  description = "GitHub Actions からのAssumeRoleを許可するリポジトリ（\"owner/repo\"形式）"
  type        = string
  default     = "b-w-hiroki/AI_progect001"
}

variable "create_oidc_provider" {
  description = <<-EOT
    GitHub Actions用のOIDCプロバイダ（token.actions.githubusercontent.com）を
    このTerraformで新規作成するか。
    **AWSアカウントには同じURLのOIDCプロバイダを1つしか作れない。**
    すでに他のプロジェクトで作成済みなら false にして、既存のものを参照する。
  EOT
  type        = bool
  default     = true
}

variable "state_bucket_name" {
  description = "bootstrap/ の output state_bucket_name の値。plan roleに読み取り権限を与える対象"
  type        = string
}

variable "state_lock_table_name" {
  description = "bootstrap/ の output lock_table_name の値。plan roleにロック用の書き込み権限を与える対象"
  type        = string
}
