locals {
  aws_regions = [
    "eu-central-1", "eu-west-1", "eu-west-2", "eu-west-3", "eu-north-1",
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "ap-south-1", "ap-southeast-1", "ap-southeast-2", "ap-northeast-1", "ap-northeast-2", "ap-northeast-3", "ap-east-1",
    "ca-central-1", "eu-south-1"
  ]
}

terraform {
  source = "tfr:///terraform-aws-modules/iam/aws//modules/iam-assumable-role?version=5.2.0"
}

inputs = {
  role_name             = "S3Replication-SAM-Role"
  role_description      = "IAM Role for replication of SAM applications source code"
  create_role           = true
  trusted_role_services = ["s3.amazonaws.com"]
  role_requires_mfa     = false
  tags = {
    Provider = "Coralogix"
    Purpose  = "SAM"
  }
}

remote_state {
  backend  = "s3"
  generate = {
    path      = "_backend.tf"
    if_exists = "overwrite"
  }
  config = {
    bucket                = get_env("AWS_SERVERLESS_BUCKET")
    key                   = "infra/terraform.tfstate"
    region                = get_env("AWS_DEFAULT_REGION")
    disable_bucket_update = true
  }
}

generate "provider" {
  path      = "_providers.tf"
  if_exists = "overwrite"
  contents  = <<EOF
provider "aws" {}
%{ for region in local.aws_regions }
provider "aws" {
  region = "${region}"
  alias  = "${region}"
}
%{ endfor }
EOF
}

generate "variables" {
  path      = "_variables.tf"
  if_exists = "overwrite"
  contents  = <<EOF
variable "s3_bucket_name_prefix" {
  description = "The prefix of S3 bucket name"
  type        = string
}
EOF
}

generate "iam" {
  path      = "_iam.tf"
  if_exists = "overwrite"
  contents  = <<EOF
resource "aws_iam_role_policy" "this" {
  name = "S3ReplicationPolicy"
  role = aws_iam_role.this[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = [
          "s3:GetReplicationConfiguration",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:s3:::$${var.s3_bucket_name_prefix}-${get_env("AWS_DEFAULT_REGION")}"
      },
      {
        Action   = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl",
          "s3:GetObjectVersion",
          "s3:GetObjectVersionTagging"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:s3:::$${var.s3_bucket_name_prefix}-${get_env("AWS_DEFAULT_REGION")}/*"
      },
      {
        Action   = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete",
          "s3:ReplicateTags"
        ]
        Effect   = "Allow"
        Resource = [
%{ for region in local.aws_regions ~}
%{ if region != get_env("AWS_DEFAULT_REGION") ~}
          "arn:aws:s3:::$${var.s3_bucket_name_prefix}-${region}/*",
%{ endif ~}
%{ endfor ~}
        ]
      }
    ]
  })
}
EOF
}

generate "buckets" {
  path      = "_buckets.tf"
  if_exists = "overwrite"
  contents  = <<EOF
%{ for region in local.aws_regions }
# Bucket in ${region} AWS region
module "${region}" {
  source    = "terraform-aws-modules/s3-bucket/aws"
  version   = "3.3.0"
  providers = {
    aws = aws.${region}
  }

  bucket    = "$${var.s3_bucket_name_prefix}-${region}"
  acl       = "public-read"

  versioning = {
    enabled = true
  }

  attach_policy = true
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Principal = "*"
        Action = ["s3:GetObject"]
        Effect = "Allow"
        Resource = "arn:aws:s3:::$${var.s3_bucket_name_prefix}-${region}/*"
      }
    ]
  })
%{ if region == get_env("AWS_DEFAULT_REGION") }
  replication_configuration = {
    role = aws_iam_role.this[0].arn
    rules = [
%{ for priority, replication_region in local.aws_regions ~}
%{ if replication_region != get_env("AWS_DEFAULT_REGION") ~}
      {
        id                        = "$${var.s3_bucket_name_prefix}-${replication_region}"
        priority                  = ${priority}
        status                    = "Enabled"
        delete_marker_replication = true
        destination = {
          bucket = "arn:aws:s3:::$${var.s3_bucket_name_prefix}-${replication_region}"
        }
      },
%{ endif ~}
%{ endfor ~}
    ]
  }

  depends_on = [
%{ for replication_region in local.aws_regions ~}
%{ if replication_region != get_env("AWS_DEFAULT_REGION") ~}
    module.${replication_region},
%{ endif ~}
%{ endfor ~}
  ]
%{ endif }
  tags = {
    Provider = "Coralogix"
    Purpose  = "SAM"
  }
}
%{ endfor }
EOF
}

