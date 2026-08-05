# fintech-chatbot V2 - AI Household Ledger Agent

Korean AI household-ledger backend. The primary product is a financial agent that tracks transactions, judges likely overspending, asks for missing context, and recommends one corrective action. The opt-in Roast mode changes tone only.

## Stack

- Python 3.11.6, Flask, RQ, Redis
- OpenAI Responses API with strict JSON Schema
- Redis Streams events plus encrypted projections
- Manual transactions first; provider-neutral read-only account port
- Optional redacted Google Sheets telemetry

## Required Workflow

1. Read `TECHSPEC.md` before code work.
2. Work only on the active task in `PLAN.md`.
3. Start each session with `pwd`, the final `progress.txt` block, `PLAN.md`, and `git log --oneline -10`.
4. One session is one active task and one scoped commit.
5. Append to `progress.txt`; never rewrite historical entries.
6. Run end-to-end tests before marking backend behavior complete.
7. Treat production credentials, providers, auth, deployment, and money movement as explicit approval boundaries.

## Product Invariants

- Accuracy comes before entertainment.
- Deterministic signals are computed before the AI judgment.
- Uncertain transactions ask exactly one focused reason question.
- Roast defaults off and is immediately reversible.
- Roast can change only the rendered message, never the judgment or recommendation.
- Necessary spending remains justified in Roast mode.
- The MVP can read, ask, judge, and advise; it cannot move money.
- Manual transaction entry must work without an account provider.
- Production account linkage stays disabled until separately approved.
- Sensitive financial data is encrypted at rest.
- Raw identifiers, amounts, merchants, reasons, balances, and chat text never enter logs, Sheets, metrics, shares, or model prompts outside the explicit TECHSPEC allowlist.

## Repository Boundaries

- `ledger/domain`: pure domain types and ports; no Flask, Redis, RQ, OpenAI, requests, Kakao, or Sheets imports.
- `ledger/application`: use-case orchestration, signal policy, and reason state machine.
- `ledger/adapters`: storage, AI, and read-only account implementations.
- `ledger/api.py` and `app.py`: thin HTTP transports.
- `tasks.py`: thin Kakao/RQ transport.
- `sheets_logger.py`: redacted allowlisted telemetry only.

## Current Stop Boundary

Complete and verify the backend, then stop. UI/UX, screen hierarchy, visual language, onboarding, transaction-capture interaction, Roast controls, reports, and share-card design must be defined with the user in the next approved phase.

## Source Documents

- `TECHSPEC.md`: immutable technical and product contract after the pivot.
- `PLAN.md`: active task and verification queue.
- `progress.txt`: append-only handoff history.
- `HANDOFF.md`: current implementation handoff.
