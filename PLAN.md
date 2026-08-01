# Development Plan - AI Household Ledger Agent

## Current State

- Phase: 2 - full product pivot
- Active task: none - waiting for user-approved UI/UX co-design
- Approval: 2026-08-01 user-approved replacement of the legacy product, TECHSPEC, PLAN, and backend
- Branch: `codex/ai-ledger-backend`
- Source of truth: `TECHSPEC.md`
- Last pre-pivot commit: `64b46ae`

## Task 2.0 - AI Ledger Backend Pivot (Completed)

### Goal

Replace the persona-first spending chatbot with a privacy-first AI household-ledger backend that can store a financial profile, accept manual transactions, compute deterministic risk signals, ask exactly one reason question when context is weak, produce a structured AI judgment, and render that same judgment in Normal or opt-in Roast tone.

### Stop Boundary

Stop and report after backend implementation and local verification. Do not make UI/UX, visual design, information architecture, screen, or share-card design decisions without the user.

Do not add production account-provider integration, production authentication, deployment, payment blocking, transfers, automatic savings, investments, or any money-movement capability.

### Ordered Checkpoints

- [x] Replace `TECHSPEC.md` with the approved pivot contract.
- [x] Replace the legacy execution queue with this backend plan.
- [x] Add domain models, event contracts, repository ports, and privacy primitives.
- [x] Add Redis Streams and in-memory repositories with encrypted projections and idempotency.
- [x] Add deterministic signals, one-question state machine, structured OpenAI judge, and deterministic fallback.
- [x] Add Normal/Roast parity rendering and safety validation.
- [x] Add profile, settings, transaction, reason, correction, share, summary, metrics, revocation, and deletion use cases.
- [x] Add versioned Flask REST API and thin Kakao/RQ transport.
- [x] Replace raw Sheets chat logging with allowlisted redacted telemetry.
- [x] Add manual, synthetic read-only, and disabled production account adapters.
- [x] Add versioned evaluation fixtures and unit, integration, and E2E tests.
- [x] Run unit/integration/E2E, compile, Redis integration, and local API smoke verification.
- [x] Update `README.md`, `HANDOFF.md`, this plan, and append `progress.txt`.
- [x] Create one scoped local commit. Do not push unless the user asks.

### Acceptance Criteria

- Manual transaction entry works without an account provider.
- Transactions cannot be judged before a financial profile exists.
- Every judgment includes deterministic evidence and a policy version.
- Medium/uncertain cases ask exactly one transaction-bound reason question.
- OpenAI receives only the explicit privacy allowlist and uses strict JSON Schema with `store=false`.
- OpenAI/schema failure retries once and then returns an auditable deterministic fallback.
- Roast defaults off and changes only the selected message, never label, confidence, rationale, factors, or recommendation.
- Corrections preserve the original judgment and append audit evidence.
- Mutating API operations are idempotent.
- Production rejects development identity headers and fails closed without trusted auth/secrets/storage.
- Sensitive values and free text are encrypted at rest.
- Sheets, logs, metrics, and share payloads cannot receive forbidden raw fields.
- Account ports are read-only and the production adapter remains disabled.
- Data revocation and deletion contracts are exercised by tests.
- All verification commands pass, or any external credential/provider gap is reported explicitly.

### Verification Commands

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall app.py tasks.py worker.py ledger tests
```

Local Redis integration and Flask smoke tests are also required. A live OpenAI call and production financial-provider E2E are not required without credentials and approvals; they must not be represented as verified.

## Next Phase - UI/UX Co-design (Blocked by Stop Boundary)

Start only after the backend report and a new user-approved task. Define together:

- onboarding and financial-profile disclosure;
- home information hierarchy;
- manual transaction capture;
- reason-question conversation;
- Normal/Roast toggle and consent;
- judgment explanation and corrections;
- monthly report and goal progress;
- privacy-safe sharing.

## Archived Work

Phase 1 migrated the old Kakao persona chatbot to the Responses API and added prompt/validator mechanics. Those commits remain in Git history, but their product plan is superseded by the 2026-08-01 pivot. Reuse is allowed only where it satisfies the new TECHSPEC invariants.
