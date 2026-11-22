# Testing Standards

Load when writing, updating, or reviewing automated tests, or when implementing any non-trivial behavior change. Focus on tests that catch real regressions and survive safe refactoring.

## Test Behavior, Not Private Implementation

- **Assert observable contracts.** Test public inputs, return values, persisted state, HTTP/event responses, and user-visible outcomes rather than internal helper call order or private state.
- **Avoid brittle spy assertions.** Checking exact internal method call counts or private SQL/DOM structure breaks during harmless refactors while missing real behavior bugs. Spy on an interaction only when that side effect *is* the contract (for example, sending an email, emitting a domain event, or charging a payment gateway).
- **Prefer real collaborators inside the unit boundary.** Use real value objects, serializers, validators, and pure domain modules instead of mocking them.

## Mock Only External Boundaries

- **Keep mocks at the edge.** Mock external HTTP APIs, third-party SDKs, system clocks, randomness, and out-of-process queues/mailers—not your own internal services or repositories when an in-memory or local test store works.
- **Watch for the "testing the mock" trap.** If a test stubs the dependency's return value and only asserts that the function returned the stubbed value or called the stub, it proves nothing about real integration, query syntax, or error handling.
- **Keep fakes faithful to real contracts.** When using stubs or fakes for external APIs or stores, mirror real error shapes, status codes, nullability, and pagination limits so tests do not pass against impossible mock data.

## Cover Edge, Failure, and Regression Cases

Do not stop at one happy-path test. Cover the failure modes that actually break production:
- **Boundary and malformed inputs:** empty collections, zero/negative numbers, max lengths, missing optional fields, Unicode/special characters, timezone/DST boundaries.
- **Authorization and trust boundaries:** unauthenticated (401) vs unauthorized/cross-tenant access (403/404), privilege escalation attempts, tampered client-supplied fields.
- **Failure and recovery paths:** upstream timeouts, HTTP 5xx/429 responses, partial batch failures, duplicate/replayed requests (idempotency), and rollback on mid-transaction errors.
- **Concurrency and ordering:** duplicate submission races, out-of-order events, or stale-response races where the code owns concurrency control.

## Determinism and Isolation

- **Eliminate time and randomness flakiness.** Inject clocks, ID generators, and RNGs (or freeze time cleanly inside the test scope) instead of depending on `Date.now()`, local timezone, or `Math.random()`.
- **Isolate mutable state.** Every test must create its own fixtures/records and clean up or run inside an isolated transaction/temp directory so test order and parallel execution never affect outcomes.
- **Zero live network dependencies.** Never hit live third-party endpoints in unit or CI integration suites; external outages must not fail local builds.
- **Never synchronize with blind sleeps.** Replace fixed `sleep(500)` waits with explicit condition polling, fake timers, or event/promise hooks.

## Strong Assertions and Bug-Fix Verification

- **Assert concrete outcomes.** Avoid weak assertions like `toBeDefined()`, `not.toThrow()`, or checking only HTTP `200` without verifying the resulting state or response contract.
- **Prove regression tests catch the bug.** When fixing a defect, write the regression test so it fails against the broken behavior (or directly exercises the broken invariant) and passes once fixed.
- **Keep test setup readable.** Inline minimal, self-explanatory fixtures near the test rather than hiding critical preconditions in giant shared fixture files whose edits silently weaken unrelated tests.

## Pragmatic Test-Level Selection

Pick the lowest test level that gives real confidence:
- **Unit tests:** pure business rules, parsers, formatters, state reducers, edge-case math.
- **Integration tests:** database queries, migrations, transactions, auth middleware, API routes, serialization, and queue handlers against a real local DB/store when available.
- **Contract tests:** API schemas, event payloads, or disk formats shared across services or versions.
- **End-to-end (E2E) tests:** a small set of critical user journeys; do not duplicate every combinatorial edge case in slow browser/device E2E suites.

## Common Real-World Compromises

Raise these trade-offs explicitly when encountered instead of silently weakening coverage:
- **Tightly coupled legacy code with no seams:** Prefer a boundary characterization test (HTTP/CLI/DB level) before refactoring, rather than rewriting the whole module just to add unit tests.
- **Slow local database or E2E setup:** Run focused unit/integration checks during iteration and run the heavier integration/E2E suite before completion—or explicitly report what was skipped if the environment lacks the runtime.
- **Third-party APIs without local emulators:** Use recorded contract fixtures or a thin adapter boundary test, and explicitly note live-sandbox behavior as unverified.
