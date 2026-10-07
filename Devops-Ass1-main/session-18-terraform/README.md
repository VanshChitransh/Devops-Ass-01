# Session 18: Terraform and Infrastructure as Code

**Name:** Vansh Chitransh
**Course:** SST DevOps & Cloud [SWE]
**Session:** 18

Two parts:

| Part | Folder | What is in it |
| --- | --- | --- |
| AWS services notes | [aws-services/](aws-services/) | My notes on IAM, EC2, S3, VPC, and DynamoDB vs RDS, one README each |
| Terraform S3 demo | [terraform-s3-demo/](terraform-s3-demo/) | A bucket built and destroyed with Terraform, with the full init, fmt, validate, plan, apply, show, output, destroy workflow and screenshots |

## Terraform in one minute

Terraform is **declarative** infrastructure as code. I write `.tf` files that describe the end state ("one private bucket with versioning"), and Terraform works out which API calls get there. The core loop:

```
write .tf  ──►  terraform init  ──►  terraform plan  ──►  terraform apply  ──►  terraform destroy
                (download providers)  (preview, no change)   (make it real)        (remove it all)
```

| Concept | Meaning | In the demo |
| --- | --- | --- |
| Provider | Plugin that talks to one platform's API | `hashicorp/aws` 6.x |
| Resource | One real object | `aws_s3_bucket.demo` |
| Variable | Input with a type and default | `bucket_name`, validated with a regex |
| Output | Value printed after apply | `bucket_arn` |
| State | Terraform's record of what it created, `terraform.tfstate` | git-ignored, never edited by hand |
| Dependency | Order derived from references | the public access block refers to the bucket, so the bucket is created first |

## About AWS on my machine

No AWS account is configured on this laptop and I did not want to commit anyone's keys, so both Terraform demos in this repository (Session 18 and 19) run against **LocalStack**, an AWS emulator that listens on `localhost:4566` in Docker. The Terraform code is the real AWS code; a single flag in `localstack.tfvars` redirects the provider's endpoints. Running the same files against a real account only needs AWS credentials in the CLI and dropping the `-var-file=localstack.tfvars` argument. The README in each demo folder explains what LocalStack does and does not emulate.
