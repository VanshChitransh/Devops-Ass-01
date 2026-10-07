variable "aws_region" {
  description = "Region the bucket is created in"
  type        = string
  default     = "ap-south-1"
}

variable "bucket_name" {
  description = "Globally unique S3 bucket name (lowercase letters, digits and hyphens)"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.bucket_name))
    error_message = "Bucket names must be 3 to 63 characters of lowercase letters, digits and hyphens."
  }
}

variable "environment" {
  description = "Environment label added to the bucket tags"
  type        = string
  default     = "dev"
}

variable "use_localstack" {
  description = "Point the AWS provider at LocalStack instead of real AWS"
  type        = bool
  default     = false
}

variable "localstack_endpoint" {
  description = "LocalStack edge endpoint"
  type        = string
  default     = "http://localhost:4566"
}
