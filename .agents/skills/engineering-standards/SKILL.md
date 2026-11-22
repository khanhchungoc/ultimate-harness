---
name: engineering-standards
description: "Apply domain engineering standards when building or reviewing backend APIs, web frontends, databases/pipelines, mobile apps, or tests. Covers reliability, security, state, and test pitfalls (not visual UI)."
---

# Engineering Standards

Prevent non-obvious correctness, reliability, security, data-integrity, and test-quality defects across backend, web frontend, data, mobile, and test code without over-engineering.

## Domain Routing

Load **only** the reference file(s) matching the code being designed, changed, or reviewed. Also load `references/testing.md` whenever adding or updating tests or changing non-trivial behavior.

| Touched domain | Load reference |
|---|---|
| Automated tests, test fixtures, mocks, or any non-trivial behavior change | [Testing standards](references/testing.md) |
| Backend services, REST/gRPC/GraphQL APIs, auth, queues, webhooks, background workers | [Backend standards](references/backend.md) |
| Web frontend logic, client state, async data fetching, DOM accessibility semantics, browser security | [Web frontend standards](references/web-frontend.md) |
| Schemas, migrations, SQL/NoSQL queries, transactions, ETL/batch data pipelines | [Data standards](references/data.md) |
| iOS, Android, React Native, or Flutter mobile apps | [Mobile standards](references/mobile.md) |

## Procedure

1. **Select matching references.** Identify which domain(s) the task touches from the routing table and read only those `references/*.md` files. Skip unrelated domains.
2. **Audit before finalizing.** Check the design, implementation, or review findings against the non-obvious pitfalls in the loaded reference(s) before writing final code or finishing a review.
3. **Surface real-world compromises explicitly.** Guidelines in the references are strong defaults, not rigid laws. When a real constraint (legacy architecture, backwards compatibility, latency, schedule, or operational complexity) conflicts with a guideline, do **not** apply the guideline blindly and do **not** silently skip it. Present the trade-off to the user with plain-English pros, cons, and a recommended option before proceeding.
4. **Verify with real runs.** Execute the relevant automated tests or checks for the changed domain(s), confirm new or updated tests actually exercise the changed behavior, and report exactly what ran versus what was skipped.

## Boundaries

- **Visual design, styling, tokens, and motion are out of scope.** Defer visual hierarchy, component styling, design tokens, CSS architecture, and UI animations to `ui-ux-pro-max`, `ui-styling`, `design-system`, `design`, and `motion`. Only frontend *engineering* concerns (state ownership, async races, semantic accessibility, browser security, lifecycle/performance hygiene) belong in `references/web-frontend.md`.
- **Do not duplicate repository or global rules.** Treat repo-specific conventions and contracts as authoritative where they narrow or override a general default.

## Failure Handling

- **Unavailable test runner or environment:** If required tests cannot run locally (missing DB, mobile simulator, or credentials), do not fabricate pass results. State the exact blocker, run whatever deterministic checks are possible (static checks, unit tests, schema/contract validation), and mark the rest as unverified.
- **Unresolved architectural trade-off:** If a compromise materially changes security, data durability, or public API compatibility, pause and confirm the chosen trade-off with the user rather than guessing.

## Deliverable

Produce audited code, design feedback, or review findings backed by:
- The specific reference domain(s) checked.
- Any real-world compromise raised or accepted, with rationale.
- Concrete verification evidence: commands/tests executed, outcomes, and any checks skipped or unverified.
