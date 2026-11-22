# Active Security Verification Guide

Load this reference during Active or Full security reviews **only after** passing the Mandatory Authorization & Safety Pre-Flight below.

## Mandatory Authorization & Safety Pre-Flight

1. **Default Allowlist (No Extra Approval Needed):**
   - `localhost`, `127.0.0.1`, `::1`, or a local container network bound strictly to the current machine (for example, `http://127.0.0.1:3000`, `http://localhost:8000`).
2. **Remote Staging / QA Gate (Written Confirmation Required First):**
   Before sending **any** request to a non-local host, obtain explicit written confirmation from the user specifying:
   - Exact base URL (scheme, host, port, path prefix).
   - Dedicated non-production test accounts / API keys (never real customer accounts).
   - Approved scope: **Tier 1 non-destructive checks only** vs. **Tier 2 DAST scanner** (and whether passive spider only or active scan).
   - Data safety expectation (confirm test records can be safely created or left in staging, or restrict strictly to read-only probes).
3. **Absolute Prohibitions:**
   - **Never** probe production domains, live customer tenants, or any third-party host/API.
   - **Never** send destructive payloads (`DROP`, `TRUNCATE`, `DELETE` against non-test records, mass account mutation), credential stuffing/brute-force floods, or Denial-of-Service traffic.
   - **Never** print raw tokens, cookies, or secrets in test logs or findings; redact them before reporting.

## Tier 1 — Safe Targeted Active Verification (Default)

Run focused, low-volume HTTP requests (for example via `curl -sS -i` or a short Python `urllib` check) against the approved target. Record exact request paths, status codes, and redacted headers/bodies as evidence.

### 1. Authentication Enforcement (`A07:2025`)
- Call protected endpoints with: (a) no credentials, (b) an expired token, (c) a malformed token (`Bearer invalid.token`), and (d) a tampered payload/signature (modify a JWT claim without re-signing, or test `alg: none` if JWTs are used).
- **Pass:** Consistently returns `401 Unauthorized` (or redirect to login for browser routes) with no protected data in the body.
- **Fail:** `200 OK`, partial data leakage, or `500 Internal Server Error` on malformed auth headers.

### 2. Object- & Function-Level Authorization (`A01:2025`, `API1`, `API5`)
- **Object-level (BOLA):** Authenticate as `User A` and request/update a known resource ID owned by `User B` (`GET/PATCH/PUT/DELETE /api/items/<userB_id>`).
- **Function-level (BFLA):** Authenticate as a standard user and call privileged/admin endpoints (`/api/admin/...`, user-listing, role updates).
- **Pass:** Returns `403 Forbidden` or `404 Not Found` and leaks zero fields belonging to `User B` or admin state.
- **Fail:** Returns `200`/`204`, mutates `User B`'s object, or leaks sensitive fields in an error body.

### 3. Security Headers & Cookie Attributes (`A02:2025`, `A07:2025`)
- Inspect response headers on HTML and API responses (`curl -sS -I <url>`):
  - `Content-Security-Policy` (or `Content-Security-Policy-Report-Only` during rollout) on HTML responses.
  - `X-Content-Type-Options: nosniff`.
  - `X-Frame-Options: DENY`/`SAMEORIGIN` or CSP `frame-ancestors`.
  - `Referrer-Policy` (for example, `strict-origin-when-cross-origin` or `no-referrer`).
  - `Strict-Transport-Security` (HSTS) on HTTPS endpoints.
- Inspect `Set-Cookie` headers on login/session responses:
  - Session/auth cookies must carry `HttpOnly`, `SameSite=Lax` or `Strict` (or `None; Secure` only when cross-site is required), and `Secure` on HTTPS.

### 4. CORS Policy Check (`A01:2025`, `A02:2025`)
- Send a request with `Origin: https://evil.example` and a second with `Origin: null` (both simple requests and `OPTIONS` preflight).
- **Pass:** `Access-Control-Allow-Origin` does **not** reflect `https://evil.example` or `null`, especially when `Access-Control-Allow-Credentials: true` is present.
- **Fail:** Arbitrary origin or `null` is echoed alongside `Access-Control-Allow-Credentials: true`.

### 5. Error Handling & Info Disclosure (`A10:2025`)
- Send malformed JSON (`{bad`), wrong field types (`{"age": "abc"}`), invalid IDs (`../test`, non-UUID), and an oversized body on a test endpoint.
- **Pass:** Clean `400`/`404`/`413`/`422` response with generic error messages; no stack traces, SQL/ORM error snippets, local file paths, or detailed server/framework version banners (`X-Powered-By`, verbose `Server`).
- **Fail:** `500` with stack trace, database query text, or fail-open behavior bypassing validation/auth.

### 6. Rate Limiting & Payload Bounds (`API4:2023`, `A06:2025`)
- Send a small, bounded burst (for example, 10–15 sequential requests—never a flood) against login, OTP, password-reset, or expensive endpoints, plus one request exceeding the expected body size limit.
- **Pass:** Endpoint throttles (`429 Too Many Requests` with `Retry-After`) or caps payload size (`413 Payload Too Large`) cleanly.
- **Note:** If throttling is absent on `localhost`, check whether rate limiting is configured at an upstream API gateway/WAF before marking it a confirmed defect (record as **unverified at edge** if gateway-managed).

### 7. Benign Injection, XSS & Open-Redirect Markers (`A05:2025`, `A01:2025`)
- Run strictly harmless markers against local test inputs only:
  - **Open redirect:** Test redirect parameters (`?next=//evil.example`, `?redirect=https://evil.example`) and confirm the server rejects external hosts rather than issuing `302 Location: https://evil.example`.
  - **Reflected XSS marker:** Submit a benign marker containing HTML metacharacters (such as `sec_probe_"'><`) and verify output is properly HTML-encoded (`&lt;`, `&gt;`, `&quot;`) or returned as `application/json` with `X-Content-Type-Options: nosniff`.
  - **SQL/template marker:** Submit a single quote `'` or `{{7*7}}` to a search/filter field and verify clean handling (no SQL syntax error, no `49` template evaluation).

### 8. Credential, API Key & Sensitive File Exposure (`A02:2025`, `A04:2025`)
- Probe common accidentally exposed paths on the approved target: `/.env`, `/.git/config`, `/config.json`, `/debug`, `/actuator/env`, `/metrics`, and API docs endpoints.
- Inspect API responses, HTML pages, client JS bundles, error bodies, and redirect `Location` headers for accidentally echoed secrets (provider API keys, DB connection strings, `Authorization`/`x-api-key` headers, or tokens in query strings).
- **Pass:** Sensitive files return `404`/`403`, and zero secrets, connection strings, or auth headers appear in responses, client bundles, or redirect URLs.
- **Fail:** Any exposed secret file, env dump, or echoed credential (always redact the value in the report and flag immediate rotation).

## Tier 2 — Optional DAST Scanners (OWASP ZAP / Nuclei)

Use Tier 2 only when the tool is installed, Tier 1 is complete, and the scope is explicitly authorized (localhost or written staging sign-off).

1. **Prefer passive spidering first:**
   - OWASP ZAP baseline (passive scan only, safe default):
     ```bash
     zap-baseline.py -t http://127.0.0.1:<port> -I
     ```
2. **Active DAST only with explicit authorization (local or approved non-prod):**
   - OWASP ZAP full scan (`zap-full-scan.py -t http://127.0.0.1:<port>`) or `nuclei -u http://127.0.0.1:<port> -severity medium,high,critical -rl 10`.
   - Always cap request rate (`-rl`) and restrict templates to non-destructive checks.
3. **Mandatory source-code triage:**
   - Never copy raw ZAP/Nuclei alerts straight into the report as confirmed vulnerabilities. Verify each alert against application source code or reproduce it with a single targeted request; discard false positives and mark unverified alerts explicitly.

## Common Real-World Compromises

- **Localhost HTTP missing HSTS and `Secure` cookie flags:** Local dev servers typically run on plain `http://127.0.0.1`, where browsers reject `Secure` cookies over non-HTTPS or TLS is terminated at a reverse proxy/ingress in production. Check production deployment/proxy config (Nginx, Cloudflare, ALB, Azure Front Door) before flagging missing HSTS/`Secure` as a high-severity defect; if proxy config is not in the repo, mark TLS/HSTS enforcement as **unverified at edge**.
- **Rate limiting enforced at API gateway or WAF:** Many services delegate throttling and request size caps to an API gateway, CDN, or WAF rather than implementing them inside app code. Confirm infrastructure config when available; if absent from the repo, report missing in-app rate limiting as a trade-off (defense-in-depth vs. keeping app stateless) and note gateway configuration must be verified before production launch.
