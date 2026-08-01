# PostgreSQL Scaling and Migrations

This learning note explains how companies handle high transaction volume with PostgreSQL and how they perform database migrations without downtime.

## How Companies Handle Millions of Transactions With PostgreSQL

PostgreSQL can handle very large transaction volumes when the database, schema, queries, and application access patterns are designed carefully. 
The secret is not one trick. It is a combination of indexing, connection management, query tuning, partitioning, caching, and operational discipline.

### Efficient Schema and Index Design

High-throughput systems start with good schema design. Tables should model the access patterns the application actually needs. Frequently queried columns should have the right indexes, but indexes should not be added blindly because every index also slows down writes.

Common techniques include:

- Primary keys and foreign keys for integrity.
- B-tree indexes for common equality and range queries.
- Partial indexes for frequently filtered subsets.
- Composite indexes that match real query patterns.
- Covering indexes when queries can be answered from the index alone.
- Avoiding unnecessary indexes on high-write tables.

### Query Optimization

Companies monitor slow queries and inspect query plans with `EXPLAIN` and `EXPLAIN ANALYZE`. 
The goal is to avoid full table scans, bad joins, excessive sorting, and queries that lock too much data.

Important practices include:

- Keep transactions short.
- Select only needed columns.
- Paginate large result sets.
- Avoid unbounded queries.
- Use batch writes when appropriate.
- Watch for N+1 query patterns.
- Use `EXPLAIN ANALYZE` before assuming the database is the bottleneck.

### Connection Pooling

Opening too many database connections can overload PostgreSQL. 
Each connection consumes memory and scheduler resources. Production systems usually use connection pooling through PgBouncer, 
application-level pools, or managed database poolers.

Connection pooling helps by:

- Reusing database connections.
- Protecting PostgreSQL from connection storms.
- Smoothing traffic spikes.
- Keeping application instances from exhausting database limits.

### Read Replicas

Read-heavy systems often use replicas. Writes go to the primary database, 
while read queries can be routed to replicas. This increases read capacity and isolates analytical or reporting workloads from the write path.

Replicas are useful for:

- Dashboards.
- Reporting.
- Search indexing jobs.
- Read-heavy API endpoints.
- Backups without loading the primary.

The tradeoff is replication lag. Applications must understand that replica reads can be slightly stale.

### Partitioning

Large tables are often partitioned by time, tenant, region, or another natural key. Partitioning lets PostgreSQL scan only relevant partitions instead of huge tables.

Common examples include:

- Transactions partitioned by month.
- Events partitioned by date.
- Customer data partitioned by tenant.
- Logs partitioned by time range.

Partitioning also makes retention easier because old partitions can be archived or dropped without rewriting the entire table.

### Caching and Async Processing

Not every request should hit PostgreSQL. Companies cache hot data in Redis, CDN layers, application memory, or materialized views. Expensive work is often moved to background jobs or queues.

Common strategies include:

- Cache frequently read objects.
- Precompute aggregates.
- Use materialized views for reporting.
- Move slow side effects to queues.
- Use idempotent background jobs for retries.

### Operational Discipline

Large PostgreSQL systems need constant monitoring and maintenance.

Important metrics include:

- Query latency.
- Transaction rate.
- Lock waits.
- Deadlocks.
- Connection count.
- Replication lag.
- CPU, memory, disk I/O, and disk space.
- Autovacuum health and table bloat.

At scale, PostgreSQL performance is usually about reducing unnecessary work, keeping hot paths indexed, controlling concurrency, and monitoring the database continuously.

## The Secret to Zero-Downtime Database Migrations

Zero-downtime migrations are achieved by making database changes backward-compatible with the currently running application. 
The core rule is: never deploy a schema change that immediately breaks the old version of the app.

Production migrations are usually done in multiple safe steps.

### Expand and Contract Pattern

The most common approach is the expand and contract pattern.

1. **Expand:** add the new schema while keeping the old schema working.
2. **Dual-write or backfill:** write or copy data into the new structure.
3. **Read switch:** deploy application code that reads from the new structure.
4. **Verify:** confirm the new path is correct and stable.
5. **Contract:** remove the old column, table, or code path later.

This avoids breaking running application instances during rolling deploys.

### Examples

Adding a nullable column is usually safe:

```sql
ALTER TABLE users ADD COLUMN display_name text;
```

Adding a required column should be split into steps:

1. Add the column as nullable.
2. Backfill existing rows.
3. Deploy code that writes the column.
4. Add the `NOT NULL` constraint later.

Renaming a column should also be split:

1. Add the new column.
2. Write to both old and new columns.
3. Backfill old data into the new column.
4. Read from the new column.
5. Drop the old column in a later deploy.

### Avoid Long Locks

Some migrations lock tables and can block reads or writes. Companies avoid this by using online-safe operations, small batches, and concurrent index creation.

Important practices include:

- Use `CREATE INDEX CONCURRENTLY` for large indexes.
- Backfill data in small batches.
- Keep transactions short.
- Avoid rewriting huge tables during peak traffic.
- Set lock timeouts for migrations.
- Test migration duration on production-like data.

### Separate Schema Deploys From App Deploys

Database changes and application changes should be staged carefully. A common safe sequence is:

1. Deploy backward-compatible schema expansion.
2. Deploy application code that supports both old and new schema.
3. Backfill data.
4. Switch reads to the new schema.
5. Remove old schema only after all old application versions are gone.

### Test Migrations Like Production Code

Migrations should be tested with realistic data size, not just empty development databases. A migration that works on 100 rows can fail badly on 100 million rows.

Migration testing should check:

- Runtime on realistic data volume.
- Locks held during the migration.
- Rollback or recovery plan.
- Compatibility with old and new application versions.
- Effect on replication lag.
- Effect on indexes, constraints, and query plans.

## Practical Rule of Thumb

For PostgreSQL scale, optimize the access pattern before adding hardware. For migrations, make every schema change backward-compatible first, then remove old structures only after the new application path is fully deployed and verified.
