terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # bucket / dynamodb_table はここに書けない（backendブロックは変数参照不可）。
  # bootstrap/ の output を `-backend-config` で渡す。手順は README 参照。
  backend "s3" {
    key     = "labs/03-cicd-oidc/terraform.tfstate"
    encrypt = true
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
      Lab       = "03-cicd-oidc"
    }
  }
}
