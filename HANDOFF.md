# AI Household Ledger Agent - Production Handoff

> Date: 2026-08-14
> Branch: `main`
> Status: Task 6.4 production hardening verified; production deployment pending this release

## Product Contract

The product is a privacy-first AI household-ledger agent. The default experience manages the user's ledger and goals; the optional `욕쟁이 할머니 모드` changes only the wording of the same financial judgment.

- Users register assets, monthly cash flow, a discretionary budget, and one savings goal.
- Manual transaction entry is the supported MVP source.
- Deterministic signals are computed before the structured AI judgment.
- Uncertain spending asks exactly one transaction-bound reason question.
- The MVP reads, asks, judges, and advises. It cannot block payments, transfer money, save automatically, invest, or recommend financial products.
- Account linkage remains disabled until a read-only provider and compliance scope are separately approved.

`TECHSPEC.md` is the immutable product/backend contract. `DESIGN.md` owns the approved UI/UX rules, and `PLAN.md` owns active work.

## Production Topology

- Vercel serves `https://jangbu-ai.vercel.app`.
- Supabase project `ijdodqldneduqeblkivo` provides email/password sessions.
- Render serves the Flask API at `https://jangbu-api.onrender.com`.
- Upstash Redis over TLS stores encrypted projections, events, idempotency records, direct indexes, and quota state.
- OpenAI Responses API is called only from Render with strict schema output, `store=false`, explicit timeout/retry/output bounds, and deterministic fallback.

Secrets remain only in provider dashboards. No OpenAI, Redis, Supabase privileged, encryption, or HMAC secret belongs in Git, Vercel public variables, browser code, screenshots, logs, or chat.

## Task 6.4 Hardening

- Browser financial drafts are scoped to a one-way hash of the authenticated user ID and cleared on sign-out or full deletion.
- Transaction retries reuse one operation ID, preventing duplicate transactions or judgments after ambiguous network failures.
- Profile/API load failures show a retryable error instead of masquerading as an unconfigured account.
- Per-user daily and short-window Redis quotas bound OpenAI usage and return safe `429` errors without leaking identifiers or quota keys.
- A quota rejection occurs before a new immediately judged transaction or reason is persisted.
- OpenAI timeout, attempts, and output token limits are explicit; fallback diagnostics are redacted.
- Redis judgment lookup uses a direct transaction index with legacy backfill; transaction lists are newest-first.
- Corrected judgments drive detail, share preview, and share-success telemetry consistently.
- Share views, clicks, and completed native shares/image downloads are separate metrics.
- Non-functional calendar, filter, search, edit, revocation, and local-only persistence claims were removed or marked unavailable.
- The service worker now caches only same-origin static assets and uses network-first navigation.
- A repeatable evaluator measures agreement against the versioned labeled fixture without claiming deterministic fallback as live-AI quality.

## Verification Evidence

- Backend: 101 discovered tests passed; four Redis-only tests were skipped in the default run and passed separately against an isolated Redis instance.
- Frontend: 32 tests passed; ESLint and the TypeScript/Vite production build passed.
- Production dependency audit: zero reported vulnerabilities.
- Python compilation and `git diff --check` passed.
- Redis integration covers app/worker projections, encrypted storage, idempotency, direct/legacy judgment indexes, TTL behavior, serialized pending-question mutation, and user deletion.
- Credential-pattern scanning found no committed secret value in the intended release files.

## Remaining External Verification

- Run an owner-controlled authenticated production flow: signup/login, profile write/read, transaction, optional reason, judgment, correction, sign-out, sign-in, and persistence check.
- Run the labeled evaluator with the live configured OpenAI judge before claiming the product's judgment-agreement target.
- Product outcomes such as four-week discretionary-spend reduction and intentional sharing require pilot evidence and are not code-test claims.
- Render Free may cold-start after inactivity; `/health` and `/ready` must be rechecked after each release.
- Financial-provider linkage, Kakao production transport, and every money-movement capability remain outside the verified MVP.

## Next Task

No task is active after 6.4. A new product or UI/UX change requires a dedicated approved task in `PLAN.md`. Do not weaken the trusted auth, privacy allowlist, idempotency, quota, or no-money-movement boundaries for convenience.
