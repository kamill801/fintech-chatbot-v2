# AI Household Ledger Agent

Responsive web/PWA and Flask backend for a Korean AI household-ledger agent that helps users reduce purchases they later regret. It combines deterministic financial signals, structured AI judgment, and the user's own post-purchase feedback to learn a personal spending standard. Normal mode records without interruption; the opt-in `욕쟁이 할머니 모드` asks one focused reason per expense and changes the interaction style without changing the underlying financial evidence.

## MVP Scope

- Store a financial profile and one savings goal.
- Accept manual transactions without an account provider.
- Expose a provider-neutral read-only account adapter contract.
- Compute overspending signals before every judgment.
- Record and judge immediately in normal mode; ask exactly one reason per expense in `욕쟁이 할머니 모드`.
- Return a structured judgment and one corrective action.
- Let users mark each purchase as `잘 쓴 돈`, `애매함`, or `후회함` and optionally explain why.
- Store up to eight editable personal spending rules as encrypted user data.
- Use a monthly calendar as the default ledger and combine stored judgments with post-purchase feedback in a weekly AI briefing.
- Prioritize one seven-day behavior change, show its estimated goal-date impact, and measure the result in the next briefing.
- Record corrections, privacy-safe shares, metrics, and audit events.
- Keep authenticated browser drafts user-scoped, clear them on sign-out/deletion, and reuse one operation ID across ambiguous retries.
- Bound per-user AI judgment usage and distinguish a share preview from a completed native share or image download.
- Retain KakaoTalk as an optional thin Flask/RQ transport outside the free web deployment.
- Provide the complete onboarding, Home, ledger, agent, report, settings, judgment, correction, and privacy-safe sharing experience as a responsive installable web app.

The MVP cannot block payments, transfer money, create savings orders, invest, or recommend financial products. Production account linkage remains disabled pending separate provider and compliance decisions.

## Architecture

```text
Vercel web/PWA or KakaoTalk
              |
       Supabase Auth JWT
              |
              v
       Render Flask API
              |
      application service
              |
    +---------+----------+
    |                    |
deterministic signals  structured AI judge
    |                    |
    +---------+----------+
              |
       shared judgment
              |
       Default / 욕쟁이 할머니 모드
              |
 post-purchase reflection loop
              |
 personal rules + weekly action
              |
   Upstash Redis + projections
```

See `TECHSPEC.md` for the complete product, privacy, API, and storage contract.

## Local Setup

Python 3.11.6 is the target runtime.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

For a dependency-free local data path, keep `LEDGER_STORE=memory`. Kakao messages run inline in that mode. Set `OPENAI_API_KEY` only when testing the live structured judge; otherwise the auditable deterministic fallback is used.

Install the frontend dependencies:

```bash
cd frontend
npm install
cd ..
```

Run the API and production frontend build:

```bash
cd frontend && npm run build && cd ..
flask --app app run --debug
```

The Flask app serves `frontend/dist` at `/` and retains the existing API, health, readiness, and Kakao routes. Development identity headers are enabled only when `ALLOW_DEV_AUTH=1`; production accepts only verified Supabase bearer tokens.

For a frontend-only Vercel release, deploy from `frontend/`:

```bash
cd frontend
npm run test && npm run lint && npm run build
vercel --prod --yes
```

Production variables are managed in the Vercel dashboard or CLI and must never be inlined in a command committed to documentation. The public frontend defaults to live mode and calls the Render API; append `?demo=1` only for deterministic visual QA. A successful frontend deployment alone does not prove authenticated persistence or live OpenAI judgment quality.

Current public frontend: `https://jangbu-ai.vercel.app`

The selected production topology is Vercel for the web app, Supabase Auth with Kakao as the primary sign-in and email/password as a fallback, a Render Free Flask web service in Singapore, and Upstash Redis over TLS. Kakao nickname and profile-image metadata are optional display fields only; financial-record ownership remains keyed by the verified Supabase `user.id`. The free web deployment does not run RQ or claim always-on availability; Render may cold-start after idle periods. See `DEPLOYMENT.md` for the environment-variable boundary and activation order.

For frontend hot reload, run these in separate terminals:

```bash
flask --app app run --debug
cd frontend && npm run dev
```

Open `http://127.0.0.1:3015`. The Vite server proxies API requests to Flask on port `5000`. Use `http://127.0.0.1:3015/?demo=1` only for deterministic visual QA; live mode always uses backend judgment artifacts.

Run Redis and the Kakao worker when exercising the asynchronous transport:

```bash
redis-server
LEDGER_STORE=redis python worker.py
```

## Verification

```bash
cd frontend && npm run test && npm run lint && npm run build && npm audit --omit=dev
cd ..
python3 -m unittest discover -s tests -v
python3 -m compileall app.py tasks.py worker.py ledger tests
LEDGER_TEST_REDIS_URL=redis://127.0.0.1:6389/15 \
  python3 -m unittest tests.integration.test_redis_repository -v
```

A local passing suite does not prove production OpenAI behavior, a production financial-provider connection, provider configuration, or live authenticated deployment. Those require separate credentials, approvals, and runtime verification.

## Privacy Defaults

- Direct user identifiers are converted to HMAC pseudonyms.
- Financial projections and event payloads are encrypted at rest.
- OpenAI receives only the explicit derived-data allowlist.
- Personal spending rules and category-level reflection history are sanitized before they enter that allowlist.
- Logs, Sheets, metrics, and shares reject raw financial or chat fields.
- Post-purchase reflections are encrypted at rest, excluded from telemetry and shares, and never rewrite the original transaction or AI judgment.
- `욕쟁이 할머니 모드` changes the reason-question gate and voice, but cannot alter deterministic evidence, labels, recommendations, corrections, or safety rules.
- User-facing copy never calls the feature Roast. Internal compatibility fields such as `roast_enabled` and `roast_message` remain unchanged.
- Local financial drafts are keyed by a one-way browser hash of the authenticated user ID and are removed on sign-out or full data deletion.
- Redis projections, events, idempotency records, and direct judgment indexes inherit the configured 365-day retention contract.

## Production Reliability

- Transaction retries reuse the same client operation ID so a lost response cannot create a second ledger entry or judgment.
- Profile/API load failures remain visible and retryable instead of being treated as a new user onboarding state.
- Production AI calls use explicit timeouts, at most two judgment attempts, a bounded output size, and Redis-backed daily/rate limits per pseudonymous user.
- Quota checks fail closed with a safe `429` before a new immediately judged transaction or reason is persisted.
- Transaction lists are newest-first and judgment lookup uses a direct Redis transaction index with legacy backfill.
- Shared cards use the effective corrected judgment, and successful shares are counted only after native share completion or image download.
- Visible controls that cannot perform their promised action are removed or marked unavailable.

## Project Status

The approved web/PWA is implemented as a regret-aware spending coach: mode-aware manual entry, a monthly calendar ledger, backend-owned judgment, editable personal spending rules, post-purchase reflection, regret-aware weekly coaching with one action and goal impact, default/`욕쟁이 할머니 모드` rendering, correction, reports, settings, user-scoped draft retention, and redacted image sharing.

The trusted production path is provisioned: Supabase project `ijdodqldneduqeblkivo` provides email/password authentication with immediate signup, Upstash provides the TLS Redis store, Render serves `https://jangbu-api.onrender.com`, and Vercel has the four public live-mode variables. The frontend Kakao OAuth path is implemented locally. The replacement Supabase project `cvrmgnjniptpncwuuzmj` has its Kakao provider configured and routing verified as of 2026-09-07; coordinated Vercel/Render Auth cutover and real consent/callback tests remain pending. Task 6.8 local verification on 2026-08-17 passed 107 backend tests with four environment-gated skips, all four Redis integration tests against an isolated local Redis, 44 frontend tests, lint, production build, compileall, diff/secret checks, and mobile plus desktop browser QA. A real authenticated Kakao sign-in, reflection-to-next-judgment E2E, and live OpenAI quality evaluation still require an owner-controlled test account; financial-provider linkage and money movement remain outside the verified MVP.
