# AI Household Ledger Agent - Production Handoff

> Date: 2026-09-13
> Branch: `main`
> Status: Task 8.0 spending-plan coach implemented, verified, and committed locally

## Product Contract

The product is a privacy-first AI household-ledger agent. The default experience manages the user's ledger and goals; the optional `욕쟁이 할머니 모드` changes only the wording of the same financial judgment.

- Users register assets, monthly cash flow, a discretionary budget, and one savings goal.
- Manual transaction entry is the supported MVP source.
- Deterministic signals are computed before the structured AI judgment.
- Uncertain spending asks exactly one transaction-bound reason question.
- The MVP reads, asks, judges, and advises. It cannot block payments, transfer money, save automatically, invest, or recommend financial products.
- Account linkage remains disabled until a read-only provider and compliance scope are separately approved.
- One active spending plan owns an explicit period and user-confirmed discretionary budget. Code calculates actual spend, unresolved reservations, flexible remaining, segment progress, and revision differences; AI provides qualitative narrative only.

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

- Backend: 133 discovered tests passed; four Redis-gated tests were skipped in the default run and all four passed separately against an isolated Redis 8.6.2 instance.
- Frontend: 55 tests passed; ESLint and the TypeScript/Vite production build passed.
- Python compilation and `git diff --check` passed.
- Redis integration covers app/worker projections, encrypted plan storage, plan activation replay, idempotency, TTL behavior, direct/legacy judgment indexes, serialized pending-question mutation, and user deletion.
- Responsive browser QA covered the active plan, editable revision list, qualitative advisor preview, and `/agent` redirect at 390x844 and 1280x900.
- Credential-pattern scanning found no secret value in the intended Task 8.0 files.

## Remaining External Verification

- Run an owner-controlled authenticated production flow: signup/login, profile write/read, transaction, optional reason, judgment, correction, sign-out, sign-in, and persistence check.
- Run the labeled evaluator with the live configured OpenAI judge before claiming the product's judgment-agreement target.
- Product outcomes such as four-week discretionary-spend reduction and intentional sharing require pilot evidence and are not code-test claims.
- Render Free may cold-start after inactivity; `/health` and `/ready` must be rechecked after each release.
- Financial-provider linkage, Kakao production transport, and every money-movement capability remain outside the verified MVP.

## Task 8.0 Spending-Plan Coach

- The authenticated plan API supports non-persistent setup/revision previews, explicit activation/apply, maintain-or-adjust check-ins, and manual planned-expense matching.
- Current plan projections and append-only plan events use the existing encrypted memory/Redis repository boundary and are purged on user deletion.
- Home leads with the explicit plan period and flexible remaining; Plan provides the three-step setup and revision flow; Report compares original/current/actual; eligible expense responses include deterministic plan impact.
- The qualitative OpenAI plan advisor uses strict JSON Schema, `store=false`, aggregate-only allowlisted input, and deterministic fallback. Merchant, memo, raw reason, reflection note, account name, user identity, and raw transactions are excluded. Its validated result is encrypted with the plan version, so ordinary reads do not repeat model calls.
- Task 7.2 remains deferred at its external provider/release gate; no provider setting, production deployment, credential, or stored Redis data changed during Task 8.0.

## Next Task

Production provider cutover, live OpenAI quality, authenticated production flow, and physical-device E2E remain external gates; Task 7.2 stays deferred.
