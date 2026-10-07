# EC2: virtual servers on demand

**Name:** Vansh Chitransh
**Session:** 18, AWS services notes

EC2 (Elastic Compute Cloud) rents virtual machines, called **instances**, by the second. I pick the operating system image, the size, the disk, the network and the firewall; AWS owns the physical hardware. This is Infrastructure as a Service: I still manage the OS and everything on it.

```
instance = AMI + instance type + key pair + security group + storage + subnet
```

## AMI: the image an instance starts from

An AMI (Amazon Machine Image) is the template: operating system, installed packages, settings. AWS provides images such as Amazon Linux 2023 and Ubuntu, the Marketplace sells images with software pre-installed, and I can bake my own "golden" image from a configured instance so that every new server starts identical. AMIs are regional; the same image has a different ID in each region. In Session 19 my Terraform looks the newest Amazon Linux 2023 AMI up with a data source instead of hard-coding an ID.

## Instance types: how big is the server

```
t3.micro
│ │   └── size: nano, micro, small, medium, large, xlarge ...
│ └───── generation
└─────── family
```

| Family | Tuned for | Typical use |
| --- | --- | --- |
| T | Burstable, cheapest | Small sites, dev and test, my homework |
| M | Balanced CPU and memory | Application servers |
| C | CPU | Batch jobs, build servers |
| R | Memory | Databases, caches |
| G, P | GPU | Machine learning, graphics |
| I, D | Local disk throughput | Big data |

Pricing: **On-Demand** (pay as you go), **Reserved or Savings Plans** (commit for one or three years for a discount), **Spot** (spare capacity at up to 90 percent off, but AWS can take it back with two minutes' notice).

## Key pairs: SSH without passwords

AWS keeps the public key on the instance; I keep the private `.pem` file. If I lose it, AWS cannot give it back, and I lose SSH access to that instance.

```bash
chmod 400 vansh-key.pem
ssh -i vansh-key.pem ec2-user@<public-ip>
```

The private key never goes into Git.

## Security groups: the instance firewall

A security group is a stateful allow-list attached to an instance. If a request is allowed in, its reply is allowed out automatically. There are no deny rules; anything not listed is blocked.

| Port | For | Allow from |
| --- | --- | --- |
| 22 | SSH | Only my own IP, never `0.0.0.0/0` |
| 80 | HTTP | Anywhere |
| 443 | HTTPS | Anywhere |

My Session 19 server has only port 80 open and no SSH rule at all.

## EBS: the disks

EBS (Elastic Block Store) volumes are network disks attached to an instance. They live in one Availability Zone, survive a stop and start, and can be snapshotted to S3 as backups. `gp3` is the general-purpose SSD I default to; `io2` is for heavy databases; `st1` and `sc1` are cheap spinning disks. Instance-store disks, by contrast, are wiped whenever the instance stops.

## Addresses

| | Private IP | Public IP |
| --- | --- | --- |
| Reachable from | Inside the VPC | The internet |
| Assigned | Always | Only if the subnet or launch asks for one |
| After stop and start | Same | **Changes** |

An **Elastic IP** is a public address I keep until I release it. Unattached Elastic IPs are billed, so I release them when done.

## Lifecycle

```
pending ──► running ──► stopping ──► stopped ──► (start) pending ...
                │
                └──► shutting-down ──► terminated
```

- **Stop** pauses compute billing; EBS storage is still billed and data stays.
- **Terminate** deletes the instance and, by default, its root volume.
- **Hibernate** writes memory to disk so the instance resumes where it was.

## What EC2 is good for

Web and API servers, databases that need full OS control, build agents, batch jobs, dev and test boxes that start and stop on demand, GPU jobs for machine learning.

## CLI I use

```bash
aws ec2 describe-instances --query 'Reservations[].Instances[].{Id:InstanceId,State:State.Name,IP:PublicIpAddress}' --output table
aws ec2 describe-instance-types --instance-types t3.micro
aws ec2 describe-security-groups
aws ec2 stop-instances --instance-ids <id>
aws ec2 terminate-instances --instance-ids <id>
```

## One-paragraph summary

An instance is an AMI running on an instance type, protected by a security group, reachable with a key pair and backed by EBS disks. Stop it to pause billing, terminate it to delete it, and use an Elastic IP if the address must not change.
