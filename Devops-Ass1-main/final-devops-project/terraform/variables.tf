variable "aws_region" {
  description = "Region for the VPC and the EKS cluster"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  type    = string
  default = "tickethub"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "vpc_cidr" {
  description = "VPC range; subnets are carved out of it"
  type        = string
  default     = "10.30.0.0/16"
}

variable "kubernetes_version" {
  type    = string
  default = "1.31"
}

variable "node_instance_type" {
  type    = string
  default = "t3.medium"
}

variable "node_desired_size" {
  type    = number
  default = 2
}

variable "node_min_size" {
  type    = number
  default = 1
}

variable "node_max_size" {
  type    = number
  default = 3
}
