---
name: security-review
description: "Run passive OWASP security audits (code, config, dependencies, secrets) and authorized active checks on local or approved staging apps, reporting severity-ranked findings and trade-offs."
---

# Security Review

Produces a severity-ranked security review report (`Critical` through `Info`) with stable finding IDs, redacted evidence, actionable fixes, explicit scanner/verification coverage, and plain-English trade-offs for meaningful hardening compromises.

## Hard Safety Guardrail

- **Never** run active probes, fuzzers, or dynamic scanners against production systems, real customer accounts/data, or any third-party or unapproved host.
- **Localhost-only default for active checks:** Active HTTP/API verification is allowed by default **only** against `localhost`, `127.0.0.1`, `::1`, or local container networks. Any remote staging or QA URL requires explicit written user confirmation of (1) the exact base URL, (2) dedicated non-production test accounts, and (3) non-destructive vs. invasive scope **before** sending a single request.
- **Never print raw secret values** in findings, evidence snippets, or command output; always redact matched credentials (for example, `AKIA****...****` or `[REDACTED len=32]`).
- **Treat real leaked keys/credentials as compromised:** Whenever a real (non-placeholder) API key, token, password, or private key is found in code, config, logs, client bundles, responses, or git history, classify it as `Critical` and require **immediate revocation and rotation**—removing it from code alone is never sufficient.

## Mode Routing

| Request scope | Required actions & references |
|---|---|
| **Passive audit** (code, config, dependencies, secrets, OWASP Top 10:2025 & API Top 10:2023) | Run [run_passive_checks.py](scripts/run_passive_checks.py) + read [passive-owasp.md](references/passive-owasp.md). |
| **Active verification** (running local dev/test server or explicitly approved staging URL) | Verify authorization gate, then read [active-checks.md](references/active-checks.md). |
| **Full security review** | Run **Passive** first, then **Active** only when a safe local target is running or a remote staging target is explicitly authorized. |

## Inputs

- Target codebase path (for Passive/Full) and/or target base URL (for Active/Full).
- Threat context / app risk tier: local prototype, internal tool, or public/multi-tenant production app.
- For Active mode on authenticated routes: non-production test credentials or test token minting instructions (at least two users/roles to verify object- and function-level authorization).

## Procedure

1. **Establish mode and threat context.**
   Determine whether the review is Passive, Active, or Full, and note the app's risk tier (local prototype, internal tool, or public/multi-tenant production) so severity and hardening advice stay proportionate.
2. **Execute Passive audit (Passive / Full mode).**
   - Run the bundled passive scanner from the skill directory:
     ```bash
     python3 <skill-dir>/scripts/run_passive_checks.py --target <path>
     ```
     Check `--help` when tuning `--format json`, `--max-findings`, `--max-file-kb`, `--timeout`, or `--skip-external`.
   - Load [passive-owasp.md](references/passive-owasp.md) and perform a manual OWASP Top 10:2025 + API Security Top 10:2023 audit (plus the LLM/AI add-on only when the codebase integrates LLMs).
3. **Execute Active verification (Active / Full mode).**
   - Enforce the Hard Safety Guardrail before sending any request.
   - Load [active-checks.md](references/active-checks.md) and run Tier 1 safe targeted checks (authentication, authorization, headers/cookies, CORS, error handling, rate limiting/payload bounds, benign injection/XSS/open-redirect markers).
   - Run Tier 2 DAST (`zap-baseline.py`, `zap-full-scan.py`, or `nuclei`) only when installed and explicitly appropriate; triage every scanner alert against source code to eliminate false positives.
4. **Triage findings and surface real-world compromises.**
   - Filter false positives and separate **confirmed defects** from **unverified risks** (such as controls enforced outside app code at a gateway/WAF).
   - When a hardening measure carries meaningful trade-offs (complexity, latency, UX friction, or disproportionate effort for the app's risk tier), raise the trade-off to the user with plain-English pros, cons, and a recommended option rather than silently prescribing maximalist controls.
5. **Deliver the report.**
   Compile the severity-ranked report described under Deliverable, preserving redaction and transparent coverage boundaries.

## Failure Handling

- **Missing external scanners:** Report unavailable or skipped tools clearly in the scanner coverage section, rely on the built-in static checks plus manual OWASP audit, and never claim a scanner passed when it did not run.
- **No running server for active checks:** Complete the passive audit and mark active checks **unverified**, listing concrete instructions for starting a local instance to verify runtime controls.
- **Unauthorized or production target:** Refuse active probing immediately without sending requests; offer a passive code/config audit or active testing against a local/approved staging copy instead.
- **Truncated scanner output:** Report the exact total vs. returned finding count from `run_passive_checks.py` and re-run with a higher `--max-findings` limit or `--format json` before drawing conclusions.

## Deliverable

Deliver a structured security review report containing:

1. **Executive Summary & Threat Context:** Mode executed, target risk tier, top risks, and overall posture.
2. **Severity-Ranked Findings (`Critical`, `High`, `Medium`, `Low`, `Info`):**
   - Stable ID (`SEC-01`, `SEC-02`, ...), severity, confidence (`Confirmed` vs. `Unverified risk`), OWASP category, exact file/line or endpoint evidence (secrets strictly redacted), impact, and concrete fix guidance.
3. **Trade-Offs & Compromises:** Plain-English options (pros, cons, recommended choice) for hardening decisions with material UX, cost, or operational impact.
4. **Coverage & Verification Matrix** (three separate sections):
   - **(a) Automated Scanners:** Each scanner's exact status (`ran`, `skipped`, `unavailable`, `timeout`, `error`) and reason.
   - **(b) Passive OWASP Review Scope:** Areas inspected vs. out of scope or skipped (including oversized/binary file counts).
   - **(c) Active Checks Run vs. Unverified:** Target URL, authorization basis, Tier 1 / Tier 2 checks executed, and any runtime checks left unverified.
