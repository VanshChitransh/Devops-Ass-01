# VPC: my own network inside AWS

**Name:** Vansh Chitransh
**Session:** 18, AWS services notes

A VPC (Virtual Private Cloud) is an isolated network with an IP range I choose. Everything that needs an IP address, such as EC2 instances and RDS databases, is launched inside one. A VPC belongs to one region and spans all of its Availability Zones; each account gets a default VPC per region so things work out of the box.

## CIDR: the address range

```
10.20.0.0/16
          └── first 16 bits fixed, 65,536 addresses
```

| Prefix | Addresses |
| --- | --- |
| /16 | 65,536 |
| /24 | 256 |
| /28 | 16 |

Use private ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), keep the VPC between /16 and /28, and pick ranges that will not overlap with networks I may connect later.

## Subnets

A subnet is a slice of the VPC range inside **one** Availability Zone. AWS reserves five addresses in every subnet, so a /24 has 251 usable. Spreading subnets over two AZs keeps an application alive if one AZ fails.

```
VPC 10.20.0.0/16
├── 10.20.1.0/24   AZ a   public    (my Session 19 subnet)
├── 10.20.2.0/24   AZ b   public
├── 10.20.11.0/24  AZ a   private
└── 10.20.12.0/24  AZ b   private
```

## Route tables

Every subnet uses one route table, which decides where packets go.

| Destination | Target | Meaning |
| --- | --- | --- |
| 10.20.0.0/16 | local | Stays inside the VPC (always present) |
| 0.0.0.0/0 | igw-… | Everything else goes to the internet |

The route table, not the name, is what makes a subnet public or private.

## Internet Gateway

The IGW connects the VPC to the internet. It is free, redundant and scales on its own. For an instance to be reachable from the internet it needs all four: an IGW attached to the VPC, a `0.0.0.0/0` route to it in the subnet's route table, a public IP, and a security group that allows the traffic. Session 19 wires exactly that.

## NAT Gateway

Instances in a private subnet often still need to download updates. A NAT Gateway sits in a public subnet with an Elastic IP, and the private route table sends `0.0.0.0/0` to it. Connections can only start from inside. It is billed per hour and per GB, which makes it one of the larger VPC costs; the final project's Terraform uses a single NAT Gateway for that reason.

## Two firewalls

| | Security group | Network ACL |
| --- | --- | --- |
| Applies to | Instance | Subnet |
| Rules | Allow only | Allow and deny |
| State | Stateful: replies allowed automatically | Stateless: both directions must be allowed |
| Evaluation | All rules together | In number order, first match wins |
| Default | Deny everything in | Allow everything |

Security groups can reference each other: "allow 5432 from the app's security group" is cleaner than listing IPs.

## Public vs private subnet

| | Public | Private |
| --- | --- | --- |
| Route to internet | `0.0.0.0/0 -> IGW` | None, or `0.0.0.0/0 -> NAT` |
| Public IPs | Usually | No |
| Reachable from outside | If allowed | Never |
| Contents | Load balancers, bastions, NAT | App servers, databases |

## The usual shape

```
                 Internet
                    │
               ┌────▼────┐
               │   IGW   │
               └────┬────┘
 ┌──────────────────▼──────────────────────┐
 │ VPC 10.20.0.0/16                        │
 │  ┌───────────────┐   ┌───────────────┐  │
 │  │ public subnet │   │ private subnet│  │
 │  │ LB, NAT GW    │──►│ app, database │  │
 │  └───────────────┘   └───────────────┘  │
 └─────────────────────────────────────────┘
```

## CLI I use

```bash
aws ec2 describe-vpcs
aws ec2 describe-subnets
aws ec2 describe-route-tables
aws ec2 describe-internet-gateways
aws ec2 describe-security-groups
```

## One-paragraph summary

A VPC is a private network with a CIDR range, cut into per-AZ subnets. Route tables decide where traffic goes, an Internet Gateway gives public subnets a way out and in, a NAT Gateway gives private subnets a way out only, security groups guard instances and network ACLs guard subnets.
