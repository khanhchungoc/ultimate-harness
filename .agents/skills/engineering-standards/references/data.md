# Data and Storage Engineering Standards

Load when designing, implementing, reviewing, or refactoring database schemas, migrations, SQL/NoSQL queries, transactions, or ETL/batch data pipelines.

## Zero-Downtime Schema Migrations (Expand and Contract)

- **Never pair destructive DDL with live traffic in one deploy.** Dropping columns/tables, renaming columns, narrowing types, or adding `NOT NULL` without a safe default breaks running app instances during rolling deploys. Use expand-and-contract:
  1. **Expand:** Add the new nullable column/table/index (using non-blocking index creation such as `CREATE INDEX CONCURRENTLY` where supported).
  2. **Backfill and dual-write:** Populate existing rows in bounded batches (throttled to avoid lock contention and replication lag) while application code writes both old and new shapes.
  3. **Switch reads:** Move application reads to the new schema and verify data parity.
  4. **Contract:** Remove dual-writes, then drop the obsolete column/table in a later release.
- **Avoid long table-locking operations.** Adding a volatile default, rewriting a large table, or running an unbounded single-transaction `UPDATE` across millions of rows can block reads/writes and bloat WAL/undo logs.
- **Define the recovery path first.** Every migration needs a clear rollback or forward-fix plan before running in production (especially once data is transformed or dropped).

## Database-Enforced Integrity and Transactions

- **Enforce invariants in the database, not only in app code.** Application-level "check if exists, then insert" races under concurrent workers. Back business invariants with `UNIQUE`, `FOREIGN KEY`, `NOT NULL`, and `CHECK` constraints in the schema.
- **Keep transaction boundaries explicit and tight.** Group multi-step writes that must succeed or fail atomically into a single transaction; keep network calls, file I/O, and slow computations outside the transaction.
- **Choose concurrency control intentionally.** Default `READ COMMITTED` does not stop lost updates or check-then-act races across rows. Use atomic conditional updates, optimistic locking (`version` column), or scoped row locking (`SELECT ... FOR UPDATE`) with consistent lock ordering to avoid deadlocks.

## Query Safety and Scalability

- **Parameterize all query values.** Never string-interpolate user input into SQL, JSONPath, or NoSQL query operators. When column names or sort directions must be dynamic, map them through a strict server-side allowlist.
- **Eliminate N+1 queries.** Loading a list of parents and issuing one query per child inside a loop degrades latency linearly with row count. Use `JOIN`s, batched `WHERE parent_id IN (...)` queries, or a dataloader.
- **Paginate stably and bound scans.** Offset pagination (`OFFSET 50000`) slows down at depth and skips/duplicates rows when live data changes. For large or changing feeds, use cursor/keyset pagination with a deterministic unique tie-breaker (`ORDER BY created_at DESC, id DESC`).
- **Index real access patterns, not every column.** Match composite index column order to equality predicates first, then range/sort columns. Remember every extra index slows writes and increases storage/vacuum cost on write-heavy tables.

## Modeling Precision and Data Lifecycle

- **Store timestamps in UTC with explicit timezone semantics.** Use timezone-aware types (`TIMESTAMPTZ` / ISO-8601 with offset) for historical instants. For future local wall-clock schedules (for example, "9:00 AM every day in Asia/Ho_Chi_Minh"), store the local wall time plus the IANA timezone identifier separately because DST rules can change.
- **Never store money as floating-point numbers.** Use exact fixed-point `DECIMAL`/`NUMERIC` or integer minor units (for example, cents) paired with an explicit ISO-4217 currency code. Document rounding rules explicitly.
- **Make soft deletes and PII lifecycle explicit.** If using `deleted_at`, ensure unique constraints use partial unique indexes (`WHERE deleted_at IS NULL`) so deleted records do not permanently block reuse, and ensure default queries cannot accidentally surface soft-deleted rows. Tag PII fields for retention, export, and hard-deletion/anonymization requirements.

## Batch and Data Pipeline Hygiene

- **Make pipelines idempotent and rerunnable.** Rerunning a job for the same date/partition must produce the same result without duplicating rows (use upserts, staging-table swaps, or partition overwrite).
- **Detect schema drift and silent emptiness.** Validate expected columns, types, null rates, and minimum/sanity row counts before promoting staging outputs to production tables.
- **Quarantine malformed records.** Route unparseable or invalid rows to a dead-letter/quarantine table with error reason and source offset rather than silently dropping data or aborting an entire multi-million-row load without checkpoints.

## Common Real-World Compromises

Raise these trade-offs explicitly before deciding:
- **Short maintenance window vs. multi-deploy expand-and-contract:** For an internal tool or low-traffic database where a brief scheduled maintenance window is acceptable, a single direct migration can be far simpler and lower-risk than multi-release dual-writing.
- **Offset pagination on small admin tables:** Acceptable when total rows stay small (hundreds to a few thousand) and users need arbitrary page jumps; switch to keyset pagination once depth or write churn causes lag or duplicates.
- **Denormalized counters or cached aggregates:** Acceptable when live `COUNT(*)`/`SUM()` queries cannot meet latency targets, provided a clear reconciliation job or trigger keeps drift bounded.
