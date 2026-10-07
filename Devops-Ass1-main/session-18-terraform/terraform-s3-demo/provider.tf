terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# Credentials are never written here. Terraform reads them from the AWS CLI
# configuration or environment variables, exactly like the aws command does.
#
# use_localstack = true points the provider at a LocalStack container instead
# of AWS (see localstack.tfvars). Every argument below is null/false for real AWS.
provider "aws" {
  region = var.aws_region

  access_key                  = var.use_localstack ? "test" : null
  secret_key                  = var.use_localstack ? "test" : null
  skip_credentials_validation = var.use_localstack
  skip_requesting_account_id  = var.use_localstack
  skip_metadata_api_check     = var.use_localstack
  s3_use_path_style           = var.use_localstack

  endpoints {
    s3  = var.use_localstack ? var.localstack_endpoint : null
    sts = var.use_localstack ? var.localstack_endpoint : null
  }

  default_tags {
    tags = {
      Project   = "session18-terraform"
      Owner     = "Vansh"
      ManagedBy = "Terraform"
    }
  }
}
