# Passive Security Audit Guide (OWASP Top 10:2025 & API Top 10:2023)

Load this reference during Passive or Full security reviews after running [run_passive_checks.py](../scripts/run_passive_checks.py). Keep findings grounded in exact file/line evidence and redact all matched secret values.

## OWASP Top 10:2025 Checklist

| Category | What to inspect in code & config | High-signal red flags |
|---|---|---|
| **A01:2025 Broken Access Control** *(includes SSRF)* | Route/middleware authz guards, object ownership checks, role/tenant scoping in DB queries, outbound HTTP fetchers/webhooks. | Missing authz decorator/middleware on mutating endpoints; fetching records by client ID without tenant/user filter; server-side URL fetch (`fetch`, `requests.get`, `http.Get`) on user-supplied URLs without host allowlist and private-IP blocking (`169.254.169.254`, `127.0.0.0/8`, `10.0.0.0/8`, `::1`); CORS `Access-Control-Allow-Origin` reflecting arbitrary origins with credentials. |
| **A02:2025 Security Misconfiguration** | Env/framework settings, headers, cookies, storage buckets, container/Dockerfiles, CI workflows. | `DEBUG=True` or stack traces enabled in prod config; wildcard CORS with credentials; missing security headers (`CSP`, `X-Content-Type-Options`, `X-Frame-Options`/`frame-ancestors`, `Referrer-Policy`); default credentials; containers running as `root`; overly broad IAM/DB grants; exposed `.env` or admin/debug endpoints. |
| **A03:2025 Software Supply Chain Failures** | Lockfiles, dependency manifests, GitHub Actions/CI scripts, third-party CDN scripts, build provenance. | Unpinned or floating dependencies/actions (`@main`, unpinned curl-to-bash); known CVEs in runtime dependencies; missing lockfile integrity checks; untrusted third-party scripts loaded without Subresource Integrity (`integrity=`) or strict CSP; excessive CI token permissions (`permissions: write-all`). |
| **A04:2025 Cryptographic Failures** | Secret storage, password hashing, TLS config, JWT/session signing, encryption at rest/in transit. | Hardcoded API keys, tokens, or private keys; TLS verification disabled (`verify=False`, `rejectUnauthorized: false`, `InsecureSkipVerify: true`); weak password hashing (MD5, SHA-1, unsalted SHA-256 instead of Argon2id/bcrypt/scrypt); insecure RNG (`Math.random()`, Python `random`) for tokens/OTPs; weak or hardcoded JWT secrets or `alg: none`. |
| **A05:2025 Injection** | SQL/NoSQL queries, shell commands, template engines, HTML sinks, LDAP/XPath/GraphQL resolvers. | String concatenation/interpolation into SQL (`f"SELECT ... {user}"`), raw `$where`/unsanitized Mongo operators, `subprocess(..., shell=True)` or `child_process.exec` with user input, `dangerouslySetInnerHTML`/`innerHTML`/`v-html` with unsanitized input, unescaped server-side templates (SSTI). |
| **A06:2025 Insecure Design** | Business workflow invariants, multi-step state machines, trust boundaries, abuse-case controls. | Price/discount/role/quota trusted from client request body; missing replay/idempotency checks on payments or redemptions; missing rate limits or account-enumeration protections on login, password reset, and OTP flows; missing concurrency locks on balance/inventory decrements. |
| **A07:2025 Authentication Failures** | Login, session lifecycle, token validation, MFA/password reset, OAuth/OIDC callbacks. | Missing JWT signature/issuer/audience/expiry validation; long-lived non-rotating sessions with no server-side revocation on logout/password change; weak password/lockout policy; auth cookies missing `HttpOnly`, `Secure`, or `SameSite`; missing OAuth `state`/PKCE or open redirect on login callback. |
| **A08:2025 Software or Data Integrity Failures** | Deserialization, webhook verification, CI/CD artifact signing, auto-updaters, client-controlled state. | Unsafe deserialization (`pickle.load`/`loads`, `yaml.load` without `SafeLoader`, Java `ObjectInputStream`, PHP `unserialize`); webhooks processed without HMAC signature & timestamp verification; unsigned/unverified client cookies or serialized workflow state; `pull_request_target` checking out untrusted PR code. |
| **A09:2025 Security Logging & Alerting Failures** | Audit logs, auth event logging, structured error logs, PII/secret redaction. | Missing audit logs for login failures, privilege changes, and sensitive data exports; logging passwords, session tokens, Authorization headers, or PII in plaintext; unescaped user input written to log lines (log forging); no alerting or correlation IDs for repeated auth/access failures. |
| **A10:2025 Mishandling of Exceptional Conditions** | Global error handlers, `try/catch` blocks, fail-open fallbacks, resource cleanup, timeout handling. | Fail-open auth/permission checks (`except Exception: return True` or default allow on cache/auth-service timeout); returning raw stack traces, SQL errors, or internal paths in HTTP responses; swallowed errors leaving partial/inconsistent state; missing upstream timeouts or unbounded retries causing cascading failures. |

## OWASP API Security Top 10:2023 Deltas

Check these API-specific failure modes whenever the repo exposes REST, GraphQL, or gRPC endpoints:

- **API1:2023 Broken Object Level Authorization (BOLA):** Every endpoint accepting an object ID (`/orders/{id}`, GraphQL `node(id:)`) must enforce ownership/tenant authorization at the data access layer—not just authentication.
- **API3:2023 Broken Object Property Level Authorization (BOPLA):**
  - *Excessive data exposure:* Avoid returning raw ORM models/DB rows; use explicit response allowlists/DTOs so internal fields (`passwordHash`, `isAdmin`, `internalNotes`) cannot leak.
  - *Mass assignment:* Bind request bodies through explicit input schemas; reject or strip privileged fields (`role`, `plan`, `verified`, `ownerId`).
- **API4:2023 Unrestricted Resource Consumption:** Enforce request body size limits, pagination caps (`limit <= max`), GraphQL depth/complexity limits, upstream timeouts, and rate limits on expensive/billable operations (exports, search, PDF/AI calls).
- **API5:2023 Broken Function Level Authorization (BFLA):** Separate admin/staff/internal routes from regular user routes and verify explicit role/permission checks on every HTTP method (including `PUT`, `PATCH`, `DELETE`).
- **API6:2023 Unrestricted Access to Sensitive Business Flows:** Protect high-value automated-abuse targets (signups, coupon redemption, checkout, invites, scraping) with velocity limits, quotas, or step-up verification.
- **API9:2023 Improper Inventory Management:** Flag undocumented shadow endpoints, deprecated `/v1` routes still mounted with weaker auth, or forgotten debug/GraphiQL/Swagger routes exposed outside local dev.
- **API10:2023 Unsafe Consumption of Third-Party APIs:** Validate and size-bound responses from third-party APIs/webhooks (treat them as untrusted input), enforce TLS and timeouts, and never blindly follow redirects from external responses.

## LLM / AI Feature Add-On *(Only When Codebase Integrates LLMs)*

Skip this section if the project does not call LLM APIs or run agent/RAG workflows.

- **Prompt injection (direct & indirect):** Untrusted user text, web pages, emails, or retrieved RAG chunks concatenated directly into system/developer prompts without clear separation or output validation.
- **Untrusted tool invocation / excessive agency:** Model output allowed to trigger state-changing tools (DB writes, SQL execution, file writes, outbound HTTP, email/payments) without strict parameter validation, allowlists, least-privilege credentials, or human confirmation for high-impact actions.
- **System-prompt & secret/PII leakage:** API keys, internal credentials, or cross-tenant RAG documents injected into prompt context without tenant filtering, or model outputs rendered as raw HTML/Markdown without sanitization.

## Scanner Reference Table

`scripts/run_passive_checks.py` always runs built-in static checks and auto-detects the optional external scanners below (reporting `ran`, `skipped`, `unavailable`, `timeout`, or `error`):

| Tool | Scope | Auto-detected by script | Deeper manual command (when installed) |
|---|---|---|---|
| **Built-in static** | High-confidence secrets (redacted) & risky config/code patterns | Always runs | `python3 <skill-dir>/scripts/run_passive_checks.py --target <path> --format json --max-findings 200` |
| **gitleaks** | Secret scanning across files and git history | `--no-git` working tree scan | `gitleaks detect --source <path> --redact` (includes full git commit history) |
| **osv-scanner** | Multi-ecosystem lockfile CVE scanning | Lockfile scan (`--format json`) | `osv-scanner scan -r <path>` (recursive lockfile + SBOM scan) |
| **npm audit** | Node.js dependency CVEs (`package-lock.json`) | Root `package-lock.json` | `npm audit --omit=dev` (separate production vs. dev-only advisories) |
| **pip-audit** | Python dependency CVEs (`requirements.txt` / `pyproject.toml`) | Root manifest scan | `pip-audit -r requirements.txt --desc` |
| **semgrep** | Multi-language SAST (`p/owasp-top-ten`) | `p/owasp-top-ten` scan | `semgrep scan --config p/default --config p/secrets <path>` |

## Common Real-World Compromises

When reporting findings, surface practical trade-offs in plain English so the user can make informed risk decisions:

- **Local prototype / internal tool vs. public multi-tenant app:** A local prototype does not need enterprise WAFs or hardware-backed KMS immediately, whereas a public multi-tenant app cannot compromise on tenant isolation (A01/API1), secret hygiene (A04), or injection prevention (A05). Flag what must be fixed *now* vs. what can wait until pre-launch.
- **Strict CSP rollout via `Report-Only` first:** Enforcing a tight `Content-Security-Policy` immediately can break inline scripts, analytics, or third-party widgets. Recommend deploying `Content-Security-Policy-Report-Only` first to catch breakages, then switching to enforcing mode once clean.
- **Dev-only transitive dependency CVEs:** A high-severity CVE inside a build-time or test-only package (such as a linter or test runner) rarely exposes production users directly. Distinguish runtime vs. dev-only exposure (for example via `npm audit --omit=dev`), and recommend upgrading on normal maintenance cadence when production is unaffected rather than blocking urgent releases.
