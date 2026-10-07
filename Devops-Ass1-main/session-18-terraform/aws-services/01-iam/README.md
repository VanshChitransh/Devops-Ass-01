# IAM: who can do what in an AWS account

**Name:** Vansh Chitransh
**Session:** 18, AWS services notes

IAM (Identity and Access Management) is the AWS service that checks every API call twice: first *who is calling* (authentication), then *is this caller allowed to do this to this resource* (authorization). It is global, not tied to a region, and it costs nothing.

```
request ──► who are you?  (user, role, access key, MFA)
        └─► may you?      (policies attached to that identity and to the resource)
```

The most important rule: **everything is denied until a policy allows it, and an explicit Deny beats every Allow.**

## The building blocks

| Piece | What it is | How I think of it |
| --- | --- | --- |
| Root user | The identity created with the account. Cannot be restricted. | The master key. Lock it in a drawer with MFA and never use it day to day. |
| User | One person or one application, with long-term credentials (password, access keys). | An employee badge. |
| Group | A set of users that share policies. Groups cannot nest and cannot log in. | A department: put the policy on the department, not on each person. |
| Role | An identity with no permanent credentials. Something *assumes* it and gets temporary keys from STS. | A visitor badge that expires. EC2, Lambda, CI pipelines and other accounts use these. |
| Policy | A JSON document that lists allowed or denied actions on resources. | The actual rules. |

A role has two policies: a **trust policy** (who may assume it) and **permission policies** (what it may do once assumed).

## Reading a policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": ["arn:aws:s3:::vansh-bucket", "arn:aws:s3:::vansh-bucket/*"],
      "Condition": {"Bool": {"aws:MultiFactorAuthPresent": "true"}}
    }
  ]
}
```

- `Effect`: Allow or Deny.
- `Action`: API calls, written as `service:Operation`. Wildcards are allowed but dangerous.
- `Resource`: ARNs the statement applies to. Note the bucket and the objects inside it are different ARNs.
- `Condition`: optional extra checks such as source IP, time, or MFA.

Policy flavours: **AWS managed** (maintained by AWS, for example `ReadOnlyAccess`), **customer managed** (written by me, reusable), **inline** (glued to one identity), and **resource-based** (attached to the resource itself, like an S3 bucket policy).

## How a decision is made

1. Start from deny.
2. Look for any matching Allow in identity policies, resource policies, permission boundaries and SCPs.
3. If any matching explicit Deny exists anywhere, the answer is deny, full stop.

## Least privilege

Give an identity only the actions it needs, on only the resources it needs, for only as long as it needs them. In practice:

- Start with nothing and add permissions when something fails.
- Name actions and resources; avoid `"Action": "*"` and `"Resource": "*"`.
- Prefer a role for one job over a shared admin user.
- Use IAM Access Analyzer and the "last accessed" data to prune unused permissions.

| Too broad | Better |
| --- | --- |
| `s3:*` on `*` | `s3:GetObject` on one bucket's objects |
| Everyone in `AdministratorAccess` | A `Developers` group with just the services they touch |
| Access keys on an EC2 server | An instance profile role |

## Practices I will follow

1. MFA on the root user and on every human user.
2. Never use root for daily work and never create root access keys.
3. Roles with temporary credentials for applications, pipelines and cross-account access.
4. Rotate any access key that must exist, and delete unused ones.
5. Permissions through groups, not per user.
6. Never commit keys to Git (Session 17's secret scan is there to catch exactly this).
7. CloudTrail on, so every call is recorded.
8. For people, IAM Identity Center (single sign-on) instead of many IAM users.

## Scenarios

| Need | IAM answer |
| --- | --- |
| New developer joins | User in the Developers group, MFA required |
| App on EC2 reads one bucket | Instance profile role allowing `s3:GetObject` on that bucket only |
| GitHub Actions deploys to AWS | A role the workflow assumes through OIDC, scoped to deployment actions, no stored keys |
| Access to another account | Cross-account role with a trust policy naming the other account |
| Contractor for two weeks | Role with a short session duration, removed afterwards |
| Nobody may delete production data | Explicit Deny on delete actions |

## CLI I use to look around

```bash
aws sts get-caller-identity           # which identity am I right now
aws iam list-users
aws iam list-groups
aws iam list-roles
aws iam list-attached-user-policies --user-name vansh
```

## One-paragraph summary

IAM answers "who are you" with users and roles, organises people with groups, and answers "what may you do" with policies. Everything is denied by default, an explicit deny always wins, and least privilege plus MFA plus roles is what keeps an account safe.
