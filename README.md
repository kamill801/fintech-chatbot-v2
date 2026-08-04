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
       Normal / Roast
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
VITE_DEMO_DEFAULT=1 npm run build
vercel env add VITE_DEMO_DEFAULT production --value 1 --yes --no-sensitive
vercel --prod --yes
```

The first public Vercel release uses build-time demo mode because production authentication and the external Flask/Redis runtime are separate release gates. A successful frontend deployment does not prove financial persistence or live OpenAI judgment is configured.

Current public frontend: `https://jangbu-ai.vercel.app`

The selected production topology is Vercel for the web app, Supabase Auth for email sessions, a Render Free Flask web service in Singapore, and Upstash Redis over TLS. The free web deployment does not run RQ or claim always-on availability; Render may cold-start after idle periods. See `DEPLOYMENT.md` for the environment-variable boundary and activation order.

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
- Logs, Sheets, metrics, and shares reject raw financial or chat fields.
- Roast is presentation-only and cannot alter a financial decision.

## Project Status

The approved 15-screen web/PWA is implemented and locally verified at mobile, tablet, and desktop widths. Manual entry, one-question reasoning, backend-owned judgment, Normal/Roast rendering, correction, reports, settings, offline draft retention, and redacted image sharing are connected.

The trusted production authentication and deployment path is implemented locally. Provider creation and live configuration remain incomplete: the current Supabase organization has reached its two-project Free limit, and Render and Upstash require account sign-in. Vercel therefore remains intentionally demo-backed until the complete authenticated path passes live verification. A real financial-provider connection, live OpenAI quality evaluation, and money movement remain outside the verified MVP.
