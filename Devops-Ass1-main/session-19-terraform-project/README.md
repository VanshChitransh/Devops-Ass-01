# Session 19: Cloud and Terraform in Action

**Name:** Vansh Chitransh
**Course:** SST DevOps & Cloud [SWE]
**Session:** 19

A small AWS environment described entirely in Terraform: a network, a firewall, a web server and a storage bucket. One `terraform apply` builds all eleven resources in the right order; one `terraform destroy` removes them.

## Architecture

```
Internet ──► Internet Gateway ──► Public subnet 10.20.1.0/24 ──► Security group (TCP 80 only) ──► EC2 t3.micro (nginx)
                  ▲                       inside VPC 10.20.0.0/16
                  │
          Public route table (0.0.0.0/0 -> IGW)

          S3 bucket vansh-24bcs10015-session19-artifacts  (private, versioned, holds welcome.txt)
```

## Files

```
session-19-terraform-project/
├── provider.tf          # Terraform and AWS provider versions, region, default tags, LocalStack switch
├── variables.tf         # inputs with types, defaults and a validated bucket name
├── main.tf              # data sources and all 11 resources
├── outputs.tf           # IDs, public IP, website URL, bucket name
├── terraform.tfvars     # my values
├── localstack.tfvars    # use_localstack = true plus a mock AMI id, for runs without an AWS account
├── .terraform.lock.hcl  # pinned provider version (committed)
├── .gitignore           # state and .terraform/ stay out of Git
├── screenshots/
└── README.md
```

## What gets created

| # | Resource | Terraform address | Why |
| --- | --- | --- | --- |
| 1 | VPC `10.20.0.0/16` | `aws_vpc.main` | Private network |
| 2 | Public subnet `10.20.1.0/24` | `aws_subnet.public` | Where the server lives; auto-assigns public IPs |
| 3 | Internet gateway | `aws_internet_gateway.main` | Door to the internet |
| 4 | Route table | `aws_route_table.public` | `0.0.0.0/0` goes to the gateway |
| 5 | Route table association | `aws_route_table_association.public` | Attaches that table to the subnet |
| 6 | Security group | `aws_security_group.web` | Allows only TCP 80 in |
| 7 | EC2 instance | `aws_instance.web` | nginx installed by user data |
| 8 | S3 bucket | `aws_s3_bucket.artifacts` | Private storage |
| 9 | Public access block | `aws_s3_bucket_public_access_block.artifacts` | Keeps it private no matter what |
| 10 | Bucket versioning | `aws_s3_bucket_versioning.artifacts` | Keeps old object versions |
| 11 | S3 object | `aws_s3_object.welcome` | A sample file |

Two **data sources** read without creating anything: the region's Availability Zones, and (on real AWS) the newest Amazon Linux 2023 AMI.

## Terraform ideas used here

- **Provider.** `hashicorp/aws` 6.x, region from a variable, `default_tags` so every resource carries `Project`, `Owner`, `ManagedBy` and `Session` without repeating them.
- **Variables.** Typed inputs with defaults; `bucket_name` has a validation rule, so a bad name fails at plan time.
- **Resources and references.** `aws_subnet.public` uses `aws_vpc.main.id`, so Terraform knows the VPC comes first. That is an implicit dependency.
- **`depends_on`.** The instance never references the internet gateway or the route association, but its startup script needs internet access to install nginx, so I list them explicitly. On destroy the order is reversed.
- **Data sources.** No AMI ID is hard-coded; `data.aws_ami.al2023` finds the newest image. It is wrapped in `count` so it is skipped when `ami_id` is supplied.
- **Outputs.** Printed after apply and available any time with `terraform output`.
- **State.** `terraform.tfstate` maps the code to real IDs. It can contain sensitive values, so it is git-ignored. A team would store it remotely with locking.

## Where it ran

There is no AWS account on this laptop and I did not want to borrow or commit anyone's keys, so I ran the whole workflow against **LocalStack 3.8** (an AWS API emulator in Docker). The code is unchanged real-AWS code: `provider.tf` has a `use_localstack` variable that, when true, points the EC2, S3, STS and IAM endpoints at `localhost:4566` and uses dummy keys. `localstack.tfvars` turns it on and supplies one of LocalStack's mock AMI IDs, since the Amazon Linux lookup only makes sense on real AWS.

What LocalStack does and does not do here:

- VPC, subnet, gateway, route table, security group and S3 behave like AWS, and the CLI can read them all back.
- EC2 is **mocked**: the instance gets an ID, a private IP and a public IP, but no virtual machine boots, so the nginx page cannot be fetched.
- Bucket tags are not stored by the 3.8 community image.

To run on real AWS: `aws configure` with a user that may create VPC, EC2 and S3 resources, `export AWS_DEFAULT_REGION=ap-south-1`, and run the same commands **without** `-var-file=localstack.tfvars`. The EC2 instance and its public IPv4 address cost money per hour, so `terraform destroy` at the end is not optional.

![Prerequisites and LocalStack identity](screenshots/00-prereq.png)

## Workflow

All commands from inside this folder.

### 1. init

```bash
terraform init
```

![terraform init](screenshots/01-init.png)

### 2. fmt and 3. validate

```bash
terraform fmt
terraform validate
```

![terraform fmt](screenshots/02-fmt.png)

![terraform validate](screenshots/03-validate.png)

### 4. plan

```bash
terraform plan -var-file=localstack.tfvars
```

`Plan: 11 to add, 0 to change, 0 to destroy.` The screenshot is filtered to the resource list and the summary; the full plan is several hundred lines of `(known after apply)` attributes.

![terraform plan](screenshots/04-plan.png)

### 5. apply

```bash
terraform apply -var-file=localstack.tfvars
```

The log shows the order Terraform chose on its own: the VPC and the bucket first (they depend on nothing), then the gateway, subnet, security group and bucket settings, then the route table, then the association, and the instance last because of `depends_on`.

![terraform apply](screenshots/05-apply.png)

### 6. Inspect the state

```bash
terraform state list
terraform state show aws_instance.web
```

The instance shows `http_tokens = required` (IMDSv2) and an encrypted gp3 root volume.

![state list and show](screenshots/06-state.png)

### 7. Outputs

```bash
terraform output
terraform output -raw website_url
```

![terraform output](screenshots/07-output.png)

### 8. Verify with the AWS CLI

Independent of Terraform, the CLI confirms the VPC and its CIDR, the running `t3.micro` with its public IP, the single TCP 80 rule, the `0.0.0.0/0 -> igw` route next to the `local` route, and the bucket with `welcome.txt` inside.

![AWS CLI verification](screenshots/08-verify.png)

On real AWS the next step is `curl "$(terraform output -raw website_url)"` after a minute or two; on LocalStack the mocked instance does not serve anything, so that step is documented rather than shown.

### 9. plan -destroy and 10. destroy

```bash
terraform plan -destroy -var-file=localstack.tfvars
terraform destroy -var-file=localstack.tfvars
```

![plan -destroy](screenshots/09-plan-destroy.png)

![terraform destroy](screenshots/10-destroy.png)

Destroy ran in reverse: bucket contents and settings, the instance, then the association and security group, then the route table and subnet, the gateway, and the VPC last. `force_destroy = true` let the bucket go even though it held an object and versions.

### 11. Confirm nothing is left

![State empty and resources gone](screenshots/11-gone.png)

## Security choices in the code

- No SSH rule. Port 22 is closed; the only way in is HTTP on 80.
- IMDSv2 required (`http_tokens = "required"`), which blocks the classic credential-theft trick through the metadata endpoint.
- Encrypted gp3 root volume.
- Private bucket: all four public access blocks on, versioning on.
- No credentials in code or in Git; the state file is ignored.

## Command summary

| Command | Does | Changes infrastructure? |
| --- | --- | --- |
| `terraform init` | Downloads providers | No |
| `terraform fmt` | Formats code | No |
| `terraform validate` | Checks syntax and references | No |
| `terraform plan` | Previews | No |
| `terraform apply` | Creates or updates | Yes |
| `terraform state list` / `state show` | Reads the state | No |
| `terraform output` | Prints outputs | No |
| `terraform plan -destroy` | Previews a destroy | No |
| `terraform destroy` | Deletes everything | Yes |

## What I took away

- One folder of code builds a whole environment and tears it down completely, so nothing is forgotten and billed.
- Terraform orders resources from references; `depends_on` covers the cases it cannot see.
- Data sources keep IDs out of the code.
- Variables make the same code reusable: a different `terraform.tfvars` is a different environment.
- Read the plan before apply and the destroy plan before destroy.
