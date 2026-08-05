# AI Household Ledger Agent - Backend Handoff

> Date: 2026-08-04
> Branch: `codex/ui-ux-foundation`
> Status: trusted production path implemented locally; provider activation blocked

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
- Supabase access-token verification uses asymmetric JWKS keys and requires the exact issuer, audience, expiry, and subject before deriving the existing HMAC user pseudonym.
- Production REST routes reject development identity headers and exact-origin CORS accepts only configured browser origins without credentialed cookies.
- `render.yaml` defines a Render Free Flask web service in Singapore; production Redis requires a TLS `rediss://` URL and sensitive payloads remain application-encrypted.
- The frontend owns Supabase email sessions and sends only the short-lived bearer access token to Flask. No service-role key is used.

## Verification Evidence

- The backend suite discovered 81 tests: 78 passed and 3 Redis-only tests skipped without `LEDGER_TEST_REDIS_URL`.
- The 3 skipped Redis integration tests passed separately against Redis 8.6.2 on an isolated local database.
- Redis tests cover app/worker shared projections, idempotency replay, events, correction state, per-user concurrency, encrypted storage, 1-day TTL, and repeated deletion.
- Frontend Vitest passed 9 tests; ESLint, TypeScript/Vite production build, and production dependency audit passed with zero reported vulnerabilities.
- `python3 -m compileall -q app.py tasks.py worker.py ledger tests` passed.
- `render.yaml` parsed successfully and contains every required production variable boundary.
- Intended source and built bundles passed the credential-pattern and local-secret-value scan.
- `git diff --check` passed.
- Real local HTTP smoke passed: `/health` 200, `/ready` 200, authenticated profile GET 200, allowed CORS preflight 204, and disallowed origin 403 without credential headers.

## Explicit Gaps

- The target runtime is Python 3.11.6, but this machine only had Python 3.14.2 for verification.
- No live OpenAI call was made. The 85% judgment-agreement target needs labeled evaluation with a configured key and then pilot evidence.
- The 10% four-week discretionary-spend reduction and 10% Roast share-rate targets require a user pilot; they are not backend test claims.
- Supabase project `ijdodqldneduqeblkivo` is selected and Healthy in Seoul. Production Site URL/redirect URL, email auth, email confirmation, ES256 JWKS compatibility, and Vercel Production public variables are configured.
- Render and Upstash were not authenticated, so no service, Redis database, provider credential, or production environment variable was created.
- Vercel remains in explicit demo mode. Do not set `VITE_DEMO_DEFAULT=0` until Supabase, Upstash, Render, CORS, readiness, and one real authenticated API flow are verified together.
- Production account-provider integration, compliance approval, live OpenAI quality evaluation, live Kakao verification, and money movement remain outside this task.

## Next Task

Resolve the remaining provider gates in this order: sign in to Upstash and Render, create the resources from `DEPLOYMENT.md`, verify the live authenticated API path, then switch Vercel out of demo mode and redeploy.

Do not paste provider credentials into chat or commit them. Do not activate live Vercel mode based only on successful builds or health checks.
