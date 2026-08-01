# AI Household Ledger Agent - Backend Handoff

> Date: 2026-08-01
> Branch: `codex/ai-ledger-backend`
> Status: backend pivot complete at the UI/UX stop boundary

## Product Contract

The product is now a privacy-first AI household-ledger agent, not a persona-first spending chatbot.

- A user registers assets, monthly cash flow, a discretionary budget, and one savings goal.
- Manual transactions are first class; a production account provider is intentionally not selected yet.
- Deterministic financial signals are computed before the AI judgment.
- Uncertain spending asks exactly one transaction-bound reason question.
- Normal is the default. Roast is opt-in and changes only tone, never the financial decision.
- MVP is read, ask, judge, and advise only. Payment blocking, transfers, automatic savings, investment, and other money movement are prohibited.

`TECHSPEC.md` is the source of truth. The old Phase 1 persona plan is superseded.

## Implemented Backend

- Modular domain, application, adapter, rendering, privacy, and API layers under `ledger/`.
- Encrypted in-memory and Redis repositories with Redis Streams events, projections, retention TTL, idempotency, and user deletion.
- User-scoped Redis mutation lock prevents concurrent pending-question overwrites.
- Separate correction projection exposes original and effective labels without mutating the original judgment.
- Deterministic `overspending-v1` signal policy plus strict OpenAI Responses JSON Schema, `store=false`, one retry, and deterministic fallback.
- Versioned REST API for profile, settings, transactions, reason, correction, share, summary, metrics, revocation, and deletion.
- Thin Kakao callback transport with production secret, callback-host allowlist, verified request-id requirement, and Redis-only RQ guard.
- Manual and synthetic read-only account adapters plus a fail-closed disabled production adapter.
- Allowlisted telemetry replaces raw chat logging.

## Verification Evidence

- 67 non-Redis unit/integration/E2E tests passed; 3 Redis-only tests skipped without `LEDGER_TEST_REDIS_URL`.
- The 3 Redis integration tests passed separately against Redis 8.6.2 on an isolated local database.
- Redis tests cover app/worker shared projections, idempotency replay, events, correction state, per-user concurrency, encrypted storage, 1-day TTL, and repeated deletion.
- `python3 -m compileall -q app.py tasks.py worker.py ledger tests` passed.
- `git diff --check` passed.
- Real local HTTP smoke passed: `/health` 200, `/ready` 200, profile PUT 200, uncertain transaction POST 202 with one reason question.

## Explicit Gaps

- The target runtime is Python 3.11.6, but this machine only had Python 3.14.2 for verification.
- No live OpenAI call was made. The 85% judgment-agreement target needs labeled evaluation with a configured key and then pilot evidence.
- The 10% four-week discretionary-spend reduction and 10% Roast share-rate targets require a user pilot; they are not backend test claims.
- Production auth, financial-provider integration, credentials, compliance approval, deployment, and live Kakao verification remain unconfigured and unverified.

## Next Task

Start a new user-approved UI/UX co-design task. Do not implement screens before agreeing together on onboarding disclosure, home hierarchy, manual transaction capture, the reason-question interaction, Roast consent and controls, judgment correction, monthly progress, and privacy-safe sharing.

Do not push, deploy, choose a provider, or add money movement as an implicit next step.
