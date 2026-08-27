output "plan_role_arn" {
  description = <<-EOT
    GitHub Actionsが引き受けるIAMロールのARN。
    このリポジトリの Settings → Secrets and variables → Actions → Variables に
    AWS_DEPLOY_ROLE_ARN として登録する（example-workflow.yml が参照する）。
  EOT
  value       = aws_iam_role.plan.arn
}

output "oidc_provider_arn" {
  description = "GitHub Actions用OIDCプロバイダのARN"
  value       = local.github_oidc_provider_arn
}
