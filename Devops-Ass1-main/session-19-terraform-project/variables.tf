variable "aws_region" {
  description = "AWS region for every resource"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Prefix used in resource names and tags"
  type        = string
  default     = "session19-vansh"
}

variable "vpc_cidr" {
  description = "Address range of the VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "public_subnet_cidr" {
  description = "Address range of the public subnet (must sit inside vpc_cidr)"
  type        = string
  default     = "10.20.1.0/24"
}

variable "instance_type" {
  description = "EC2 instance type for the web server"
  type        = string
  default     = "t3.micro"
}

variable "ami_id" {
  description = "AMI for the web server. Leave empty to look up the newest Amazon Linux 2023 image."
  type        = string
  default     = ""
}

variable "bucket_name" {
  description = "Globally unique name for the artifacts bucket"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.bucket_name))
    error_message = "Bucket names must be 3 to 63 characters of lowercase letters, digits and hyphens."
  }
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
