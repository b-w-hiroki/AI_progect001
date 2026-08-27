terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # ここだけは意図的にlocal state（backendブロックを書かない）。
  # このディレクトリの役目は「S3 backendの置き場所そのものを作る」ことなので、
  # このディレクトリ自身をS3 backendにはできない（鶏と卵）。
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
      Lab       = "03-cicd-oidc/bootstrap"
    }
  }
}
