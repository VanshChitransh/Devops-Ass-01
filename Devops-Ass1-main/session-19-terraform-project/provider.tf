terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# No credentials in code: the provider reads them from the AWS CLI config or
# environment. With use_localstack = true (localstack.tfvars) every API call
# goes to a LocalStack container instead; all of those arguments are off for real AWS.
provider "aws" {
  region = var.aws_region

  access_key                  = var.use_localstack ? "test" : null
  secret_key                  = var.use_localstack ? "test" : null
  skip_credentials_validation = var.use_localstack
  skip_requesting_account_id  = var.use_localstack
  skip_metadata_api_check     = var.use_localstack
  s3_use_path_style           = var.use_localstack

  endpoints {
    ec2 = var.use_localstack ? var.localstack_endpoint : null
    s3  = var.use_localstack ? var.localstack_endpoint : null
    sts = var.use_localstack ? var.localstack_endpoint : null
    iam = var.use_localstack ? var.localstack_endpoint : null
  }

  default_tags {
    tags = {
      Project   = var.project_name
      Owner     = "Vansh"
      ManagedBy = "Terraform"
      Session   = "19"
    }
  }
}
