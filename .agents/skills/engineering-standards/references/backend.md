# Backend Engineering Standards

Load when designing, implementing, reviewing, or refactoring backend APIs, services, auth flows, webhooks, or background workers.

## API Contracts and Evolution

- **Keep live contracts backwards-compatible.** Add new optional fields or endpoints rather than renaming, removing, or narrowing existing fields in place. For breaking changes, version the contract or migrate callers before removal.
- **Bound every list and bulk operation.** Enforce explicit pagination (with a hard maximum page size) and request payload size limits on all collection endpoints and batch inputs. Never return unbounded table scans.
- **Make retryable mutations idempotent.** Payments, order creation, webhook receivers, and job triggers will be retried by clients, proxies, or providers. Require an idempotency key (scoped per actor/operation) or a natural unique key so replays return the original outcome instead of duplicating side effects.

## Trust Boundaries and Authorization

- **Separate authentication from object-level authorization.** Verifying a valid session/JWT only proves *who* is calling—never *whether they own or may act on* the target record. Enforce object- and tenant-level authorization on every read, update, and delete (prevents IDOR and cross-tenant data leaks).
- **Never trust client-supplied authority or derived values.** Compute prices, totals, discounts, timestamps, roles, tenant IDs, and owner IDs on the server from authoritative records.
- **Allowlist mutable fields.** Bind request bodies through explicit schemas/DTOs rather than passing raw JSON straight into ORM updates (prevents mass assignment of `role`, `isAdmin`, `status`, or `accountId`).
- **Validate at every entry boundary.** Treat HTTP bodies, query params, headers, webhooks (verify cryptographic signatures with constant-time comparison), and queue payloads as untrusted input.

## Error Contracts and Observability

- **Return accurate, consistent error envelopes.** Use a stable machine-readable error code plus plain message. Distinguish client errors (`400`/`401`/`403`/`404`/`409`/`422`/`429`) from server/upstream failures (`500`/`502`/`503`/`504`)—never turn validation errors into `500` or database outages into `400`.
- **Never leak internals.** Strip stack traces, raw SQL errors, internal hostnames, and secrets from external responses; log full diagnostics server-side only.
- **Never swallow errors silently.** Empty `catch` blocks or fire-and-forget async tasks hide data loss. Either handle recovery explicitly, propagate the failure, or log with structured context and surface failure metrics.
- **Propagate correlation IDs.** Attach a request/trace ID at the edge, include it in structured logs and error responses, and forward it to downstream services and background jobs.

## Outbound Resilience and Transaction Boundaries

- **Set explicit timeouts everywhere.** Every outbound HTTP client, RPC stub, queue client, and DB query must have explicit connect and read/statement timeouts—library defaults are often infinite.
- **Bound retries safely.** Retry only transient errors (`429`, `502`/`503`/`504`, network resets) with capped attempts and jittered exponential backoff—and **never** auto-retry non-idempotent mutations unless an idempotency key guarantees deduplication.
- **Never hold DB transactions open across network calls.** Calling a third-party API inside an open database transaction exhausts connection pools and holds locks during upstream slowdowns. Commit local state (for example, `pending` status or a transactional outbox row), call the external service outside the transaction, then reconcile the result.

## Concurrency and Async Messaging

- **Eliminate check-then-act races.** Reading a balance, quota, or status in code and then updating it in a separate query fails under concurrent requests. Enforce invariants with atomic conditional updates (`UPDATE ... WHERE balance >= ?` or optimistic version checks), row locks, or unique DB constraints.
- **Design message consumers for at-least-once delivery.** Queues and webhooks deliver duplicates and out-of-order messages. Make handlers idempotent (track processed event IDs or use state-machine transitions), bound retry counts, and route poison messages to a dead-letter queue instead of blocking the partition forever.

## Startup Configuration and Secrets Hygiene

- **Fail fast on bad startup config.** Validate required environment variables, URLs, and secrets at process boot rather than crashing lazily on the first user request.
- **Keep secrets out of code, logs, and URLs.** Never hardcode fallback secrets/keys, never put tokens in query strings (which land in proxy/access logs), and redact `Authorization`, cookies, and PII in structured logs.

## Common Real-World Compromises

Raise these trade-offs explicitly before deciding:
- **Synchronous external call vs. transactional outbox:** A direct external call with timeout + reconciliation job is simpler for low-volume flows, whereas an outbox/worker adds operational pieces; raise the durability vs. complexity trade-off when payments or critical state are involved.
- **Breaking API change for a single internal caller:** If only one controlled frontend/service calls the endpoint and deploys atomically, an in-place change may beat multi-step deprecation—confirm caller ownership first.
- **Coarse in-memory rate limits/caches vs. shared store (Redis):** Acceptable for single-instance services or prototypes, but breaks under horizontal scaling; document the scaling limit explicitly.
