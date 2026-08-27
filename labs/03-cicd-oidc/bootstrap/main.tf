##############################################################################
# Terraform state の置き場所
#
# Lab 1・Lab 2 はここまでlocal state（tfstateが自分のPCにしかない）だった。
# 複数人・複数マシンで作業する瞬間に、S3 + DynamoDB lock が必要になる
# （LEARNING_AWS.md フェーズ3参照）。このディレクトリはそれ自体を作るための、
# 一度だけ apply する「土台」。ここだけはlocal stateのまま（versions.tf参照）。
##############################################################################

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "tfstate" {
  # バケット名はグローバルに一意でなければならない。アカウントIDを含めることで
  # 他のAWSアカウントを使っている誰かの命名と衝突する可能性を消している。
  bucket = "${var.project}-tfstate-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
  # tfstateは「壊れたら最悪リソースの管理を見失う」ファイル。
  # バージョニングがあれば、誤ったapplyで壊れても1つ前の版に戻せる。
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
  # tfstateにはリソースIDやARN、場合によっては認証情報の一部が平文で入る。
  # 公開設定は全部塞ぐ。ここを外す理由は無い。
}

resource "aws_dynamodb_table" "lock" {
  name         = "${var.project}-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
  # 属性名 "LockID" は固定。Terraform の S3 backend がロック取得時に
  # このキー名でアイテムを読み書きする仕様になっている。変更不可。
}
