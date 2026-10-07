# S3: object storage

**Name:** Vansh Chitransh
**Session:** 18, AWS services notes

S3 (Simple Storage Service) stores **objects**: files of any type, up to 5 TB each, in unlimited quantity, addressed by name over HTTPS. It is not a disk: I cannot mount it as a filesystem for an operating system or edit part of an object in place. I upload, download, list and delete.

- **Durability** of eleven nines: data is copied across several facilities in the region.
- **Scale** with no servers to manage and no capacity to plan.
- **Pay** for storage, requests and data transferred out.

## Buckets and objects

A **bucket** is the container. Its name is globally unique across all of AWS (lowercase letters, digits, hyphens), it lives in one region, and it is private by default. Inside, the namespace is flat: a key such as `reports/2026/october.csv` only looks like folders.

An **object** is a key plus the data plus metadata (content type, custom tags, a version ID when versioning is on). Above about 100 MB uploads should use multipart upload; above 5 GB they must.

```bash
aws s3 cp notes.pdf s3://vansh-bucket/docs/notes.pdf
aws s3 ls s3://vansh-bucket/docs/
aws s3 sync ./site s3://vansh-bucket/
```

## Storage classes

| Class | For | Retrieval |
| --- | --- | --- |
| Standard | Data read often | Immediate |
| Intelligent-Tiering | Unknown or changing access patterns | Immediate, moves data automatically |
| Standard-IA | Read rarely but needed fast | Immediate, with a per-GB retrieval fee |
| One Zone-IA | Rarely read and easy to recreate | Immediate, one AZ only |
| Glacier Instant Retrieval | Archives read a few times a year | Milliseconds |
| Glacier Flexible Retrieval | Archives | Minutes to hours |
| Glacier Deep Archive | Compliance archives | Hours, cheapest of all |

## Versioning

With versioning on, every overwrite keeps the old copy and every delete only adds a *delete marker*. I can restore any earlier version, which is the cheapest protection against a wrong `rm` or a bad deploy. It can only be suspended, never fully removed, and old versions keep costing storage, so pair it with a lifecycle rule. Both of my Terraform demos (Sessions 18 and 19) turn it on.

## Lifecycle rules

Automatic housekeeping by age: move objects to Standard-IA after 30 days, to Glacier after 90, delete after a year, expire old versions, abort incomplete multipart uploads.

## Encryption

| Mode | Keys managed by |
| --- | --- |
| SSE-S3 | S3, on by default for every new object |
| SSE-KMS | AWS KMS, with audit trail and fine-grained key policies |
| SSE-C | Me, supplied with every request |
| Client-side | Me, before upload |

Transport is HTTPS; a bucket policy can deny any request that is not.

## Access control

A **bucket policy** is a resource-based policy attached to the bucket:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "AppRoleReadOnly",
    "Effect": "Allow",
    "Principal": {"AWS": "arn:aws:iam::123456789012:role/app-role"},
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::vansh-bucket/*"
  }]
}
```

**Block Public Access** is the safety switch above all policies; keep it on unless the bucket really is a public website. ACLs are the old mechanism and are disabled by default. A request is allowed if an IAM policy or the bucket policy allows it, and an explicit deny always wins.

## What I use S3 for

User uploads and media, static website hosting (a React build), backups, logs, data lakes for analytics, build artifacts, and remote Terraform state.

## One-paragraph summary

S3 stores objects in globally named, regional, private-by-default buckets. Pick a storage class for cost, turn on versioning for safety, add lifecycle rules so old data ages out, keep Block Public Access on, and grant access with IAM and bucket policies. Encryption at rest is on by default.
