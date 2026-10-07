# DynamoDB and RDS: the two managed database families

**Name:** Vansh Chitransh
**Session:** 18, AWS services notes

AWS runs the servers, patching, backups and failover for both; I design the data model and the queries. **DynamoDB** is a serverless NoSQL key-value and document store. **RDS** runs classic relational engines.

---

## DynamoDB

### What NoSQL means here

No fixed table schema, no joins. Items in one table may have different attributes; only the key attributes are mandatory. There are no servers to size, responses take single-digit milliseconds, and it scales to almost any size.

| DynamoDB term | SQL equivalent |
| --- | --- |
| Table | Table |
| Item | Row |
| Attribute | Column |

```json
{ "UserId": "vansh", "OrderDate": "2026-10-07", "Total": 499, "Items": ["book", "pen"] }
```

### Partition key

The required main key. DynamoDB hashes it to choose the physical partition that stores the item, so a key with many distinct values (user IDs, order IDs) spreads load evenly. Fetching by partition key is the fast path.

### Sort key

Optional second part of the key. Items that share a partition key are stored in sort-key order, so I can ask for "all orders of user `vansh` in October" with one range query. Partition key plus sort key must be unique together.

```
PartitionKey  SortKey      ...
vansh       2026-10-01   Total 120
vansh       2026-10-07   Total 499
priya         2026-10-03   Total 75
```

### Also worth knowing

On-demand or provisioned capacity; secondary indexes for querying by other attributes; TTL to expire items automatically; replication across three AZs; global tables across regions.

**Good fit:** shopping carts, sessions, profiles, leaderboards, IoT streams: huge scale, simple access patterns.

```bash
aws dynamodb list-tables
aws dynamodb scan --table-name Orders
```

---

## RDS

### What it gives me

A managed relational database: tables, rows, columns, SQL, joins, transactions and a strict schema. RDS does provisioning, OS patching, automated backups, point-in-time restore and failover.

### Engines

MySQL, PostgreSQL, MariaDB, Oracle, SQL Server, Db2, and **Aurora** (AWS-built, MySQL and PostgreSQL compatible, faster and more available). My final project runs PostgreSQL inside Kubernetes for the classroom; on real AWS I would move it to RDS PostgreSQL.

### DB instance

The server: engine and version, an instance class such as `db.t3.micro`, storage type and size, and a **subnet group** naming the private subnets it may use.

### Security

Private subnets only, no public access; a security group allowing the DB port only from the application's security group; encryption at rest with KMS (chosen at creation) and TLS in transit; master password in Secrets Manager, never in code; optionally IAM authentication.

### Backups

Automated daily snapshots plus transaction logs allow point-in-time recovery to any second in the retention window (up to 35 days). Manual snapshots stay until deleted. A restore always creates a new instance.

### Multi-AZ vs read replicas

| | Multi-AZ | Read replica |
| --- | --- | --- |
| Purpose | High availability | Read scaling |
| Replication | Synchronous standby in another AZ | Asynchronous copy, can be in another region |
| Serves reads | No | Yes |
| Failover | Automatic, one to two minutes | Manual promotion |

---

## Choosing between them

| | DynamoDB | RDS |
| --- | --- | --- |
| Model | Key-value and document | Relational with SQL |
| Schema | Flexible per item | Fixed tables |
| Queries | By key and index | Anything SQL can express, with joins |
| Scaling | Automatic | Bigger instance, plus read replicas |
| Servers | None | An instance class I pick |
| Transactions | Limited | Full ACID |
| Best when | Massive scale, simple lookups | Complex relationships and reporting |

## One-paragraph summary

DynamoDB for very large scale and low latency with key-based access; RDS when I need SQL, joins and transactions. On RDS, Multi-AZ keeps the database available and read replicas make it faster for reads.
