# AI Household Ledger Agent

Responsive web/PWA and Flask backend for a Korean AI household-ledger agent. It combines deterministic financial signals with a structured AI judgment, asks one focused question when purchase context is insufficient, and renders the same decision in Normal or opt-in Roast tone.

## MVP Scope

- Store a financial profile and one savings goal.
- Accept manual transactions without an account provider.
- Expose a provider-neutral read-only account adapter contract.
- Compute overspending signals before every judgment.
- Ask exactly one reason question for uncertain transactions.
- Return a structured judgment and one corrective action.
- Record corrections, privacy-safe shares, metrics, and audit events.
- Support KakaoTalk through a thin Flask/RQ transport.
- Provide the complete onboarding, Home, ledger, agent, report, settings, judgment, correction, and privacy-safe sharing experience as a responsive installable web app.

The MVP cannot block payments, transfer money, create savings orders, invest, or recommend financial products. Production account linkage and production authentication are intentionally disabled pending separate provider and compliance decisions.

## Architecture

```text
Flask REST / KakaoTalk transport
              |
              v
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
       Normal / Roast
              |
   Redis Streams + projections
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

The Flask app serves `frontend/dist` at `/` and retains the existing API, health, readiness, and Kakao routes. Development identity headers are enabled only when `ALLOW_DEV_AUTH=1`.

For a frontend-only Vercel release, deploy from `frontend/`:

```bash
cd frontend
VITE_DEMO_DEFAULT=1 npm run build
vercel env add VITE_DEMO_DEFAULT production --value 1 --yes --no-sensitive
vercel --prod --yes
```

The first public Vercel release uses build-time demo mode because production authentication and the external Flask/RQ/Redis runtime are separate release gates. A successful frontend deployment does not prove financial persistence or live OpenAI judgment is configured.

Current public frontend: `https://jangbu-ai.vercel.app`

The production backend target is an always-on Flask API plus a separate RQ worker on Cloudtype, backed by managed Redis. Trusted user authentication must be implemented before switching the Vercel build out of demo mode or accepting real financial data.

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

A local passing suite does not prove production OpenAI behavior, a production financial-provider connection, production authentication, or deployment. Those require separate credentials, approvals, and live verification.

## Privacy Defaults

- Direct user identifiers are converted to HMAC pseudonyms.
- Financial projections and event payloads are encrypted at rest.
- OpenAI receives only the explicit derived-data allowlist.
- Logs, Sheets, metrics, and shares reject raw financial or chat fields.
- Roast is presentation-only and cannot alter a financial decision.

## Project Status

The approved 15-screen web/PWA is implemented and locally verified at mobile, tablet, and desktop widths. Manual entry, one-question reasoning, backend-owned judgment, Normal/Roast rendering, correction, reports, settings, offline draft retention, and redacted image sharing are connected.

Production authentication, a real financial-provider connection, live OpenAI quality evaluation, deployment, and money movement remain separate credential-, compliance-, or provider-gated work. The MVP does not claim those capabilities.
