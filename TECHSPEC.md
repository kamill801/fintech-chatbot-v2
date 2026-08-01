# Technical Specification - AI Household Ledger Agent

> This document is the backend source of truth after the 2026-08-01 product pivot.
> Future changes require a dedicated PLAN.md task and explicit approval.

## 1. Product Goal

Build a Korean AI household-ledger agent that understands a user's financial position and goal, tracks manually entered or read-only imported transactions, judges likely overspending, asks for missing purchase context, and recommends one concrete corrective action.

The primary outcome is behavior change, not transaction storage alone.

The product has two presentation modes:

- Normal: direct, non-shaming financial coaching.
- Roast: opt-in Korean market-grandmother scolding.

Roast is a presentation layer. It cannot change evidence, confidence thresholds, labels, or financial recommendations.

## 2. Success Criteria

The MVP is successful only when all three product metrics can be measured:

1. Overspending judgment agreement is at least 85% on a versioned, human-labeled scenario set.
2. Four-week pilot users reduce discretionary spending by at least 10% against their defined baseline.
3. Intentional Roast-result shares are at least 10% of eligible Roast-result views.

Backend completion before design requires:

- Financial profile and one goal can be stored and retrieved.
- Manual transactions work without any account provider.
- Deterministic signals are computed before every final judgment.
- Low or medium confidence causes exactly one transaction-bound reason question.
- AI returns a structured final judgment.
- Normal and Roast modes share one judgment artifact.
- Corrections, audit events, views, and shares are recorded.
- Sensitive data is encrypted at rest and excluded from external sinks by allowlist.
- User data deletion and account revocation contracts exist.
- Unit, integration, E2E, compile, and local API smoke checks pass.

## 3. Scope

### 3.1 In Scope

- Financial profile: liquid assets, income, fixed expenses, debt payments, discretionary budget.
- One active financial goal: name, target amount, current amount, target date.
- Manual transaction entry as a first-class source.
- Provider-neutral read-only account adapter port.
- Synthetic provider adapter for contract tests.
- Deterministic financial signals.
- OpenAI Responses API strict JSON Schema judgment.
- Deterministic fallback judgment when OpenAI is unavailable.
- One-question reason workflow.
- Normal and Roast rendering from the same judgment.
- User agreement/disagreement and corrected labels.
- Privacy-safe share payload and share metrics.
- Append-only audit events and current-state projections.
- Legacy Redis state import without creating fake monetary transactions.
- KakaoTalk webhook/RQ compatibility as a thin transport.
- Versioned JSON REST API for future UI use.

### 3.2 Out of Scope

- UI/UX, design system, screens, share-card visual design.
- Production deployment.
- Production financial-data provider selection, contract, or paid integration.
- Production auth-provider selection.
- Payment blocking, transfers, automatic savings, or investment orders.
- Any autonomous movement of money.
- Investment, insurance, credit, or loan product recommendations.
- Receipt or image processing.
- Multiple personas.
- Production Open Banking or MyData launch approval.

### 3.3 Stop Boundary

Stop and report after the backend and its tests are complete. Do not begin UI/UX decisions. The next phase must start with the user and cover information architecture, onboarding, transaction capture, agent conversation, Roast toggle, reports, and sharing.

## 4. Product Invariants

1. Accuracy before entertainment.
2. Roast defaults off and is immediately reversible.
3. Roast never changes a judgment or recommended action.
4. Missing context triggers one focused question before a final accusation.
5. Justified purchases remain justified in Roast mode.
6. The MVP is read-and-advise only.
7. User corrections append evidence; they never erase the original judgment.
8. Production startup fails closed when encryption, pseudonymization, or authentication trust is missing.
9. Production account linkage remains disabled until separately approved.
10. Raw sensitive financial data never enters Sheets, structured logs, metrics, or share payloads.

## 5. Architecture

### 5.1 Selected Architecture

Use a modular monolith that preserves Flask, RQ, and Redis:

```text
KakaoTalk or future UI
        |
        v
Flask transports: app.py + ledger/api.py
        |
        v
ledger/application/service.py
        |
        +--> profile and goal use cases
        +--> transaction ingestion
        +--> deterministic signals
        +--> reason-question state machine
        +--> structured AI judgment
        +--> mode-specific rendering
        +--> correction/share/deletion use cases
        |
        v
Repository ports
        |
        +--> Redis Streams + projections
        +--> InMemory repository for tests

RQ worker: async Kakao callback adapter only
External sinks: centralized privacy allowlist first
```

### 5.2 Rejected Alternatives

- Extend legacy user_state JSON: rejected because it cannot reliably replay events, enforce idempotency, or preserve correction history.
- Split microservices: rejected because it adds deployment and coordination cost before product validation.
- Add Postgres now: deferred. SQL is stronger for cross-user reporting, but Redis is the current production dependency. The event schema must remain portable to a later Postgres migration.

### 5.3 Required File Boundaries

```text
ledger/
  domain/
    models.py
    events.py
    ports.py
  application/
    service.py
    signals.py
    state_machine.py
  adapters/
    memory.py
    redis_store.py
    manual.py
    synthetic.py
    openai_judge.py
  api.py
  factory.py
  privacy.py
  rendering.py
  telemetry.py

tests/
  fixtures/judgment_scenarios_v1.json
  unit/
  integration/
  e2e/
```

Domain modules cannot import Flask, Redis, RQ, OpenAI, requests, Kakao code, or Google Sheets code.

## 6. Domain Model

Money is stored as integer KRW. Timestamps are timezone-aware ISO 8601 UTC strings.

### 6.1 FinancialProfile

```json
{
  "user_ref": "pseudonymous-id",
  "monthly_income_krw": 3500000,
  "liquid_assets_krw": 10000000,
  "fixed_expenses_krw": 1400000,
  "monthly_debt_payment_krw": 300000,
  "discretionary_budget_krw": 800000,
  "goal": {
    "goal_id": "uuid",
    "name": "비상금",
    "target_amount_krw": 10000000,
    "current_amount_krw": 3000000,
    "target_date": "2027-12-31"
  },
  "created_at": "UTC timestamp",
  "updated_at": "UTC timestamp",
  "schema_version": 1
}
```

Validation:

- All money fields are non-negative integers.
- Monthly fixed expenses plus debt payments may exceed income, but this creates a high goal-pressure signal.
- Discretionary budget must be positive.
- Goal target amount must exceed or equal current amount.
- Goal target date cannot be before the current date when first created.

### 6.2 UserSettings

```json
{
  "roast_enabled": false,
  "locale": "ko-KR",
  "timezone": "Asia/Seoul",
  "schema_version": 1
}
```

### 6.3 Transaction

```json
{
  "transaction_id": "uuid",
  "user_ref": "pseudonymous-id",
  "amount_krw": 120000,
  "merchant": "encrypted raw merchant or null",
  "category": "shopping",
  "description": "encrypted optional text",
  "occurred_at": "UTC timestamp",
  "source": "manual",
  "source_reference": null,
  "reason": null,
  "status": "recorded",
  "created_at": "UTC timestamp",
  "schema_version": 1
}
```

Allowed source values: manual, synthetic, provider_readonly, legacy.

Allowed status values: recorded, awaiting_reason, judged, corrected.

### 6.4 DeterministicSignalSet

```json
{
  "budget_usage_after": 0.72,
  "transaction_budget_share": 0.15,
  "goal_pressure": 0.55,
  "baseline_deviation": 1.4,
  "recurrence_30d": 3,
  "essentiality": 0.2,
  "risk_score": 0.61,
  "data_confidence": 0.66,
  "requires_reason": true,
  "factors": ["budget_usage", "goal_pressure"]
}
```

All ratios and scores are clamped to documented ranges. Signals are evidence, not the final label.

### 6.5 JudgmentResult

```json
{
  "judgment_id": "uuid",
  "transaction_id": "uuid",
  "label": "caution",
  "confidence": 0.81,
  "rationale": "목표 달성 속도를 늦추지만 필수 지출은 아니다.",
  "recommended_action": "이번 주 외식 예산에서 같은 금액을 줄인다.",
  "decision_factors": ["goal_pressure", "user_reason"],
  "normal_message": "...",
  "roast_message": "...",
  "fallback_used": false,
  "model": "configured model or deterministic-fallback-v1",
  "policy_version": "overspending-v1",
  "created_at": "UTC timestamp",
  "schema_version": 1
}
```

Allowed labels: justified, caution, overspending, insufficient_context.

### 6.6 PendingQuestion

```json
{
  "question_id": "uuid",
  "transaction_id": "uuid",
  "question": "이 지출이 꼭 필요했던 이유가 뭐야?",
  "asked_at": "UTC timestamp",
  "answered_at": null,
  "attempt_count": 0
}
```

A transaction can create at most one PendingQuestion.

## 7. Event and Storage Contract

### 7.1 Event Envelope

```json
{
  "event_id": "uuid",
  "user_ref": "HMAC-derived pseudonym",
  "event_type": "transaction.recorded",
  "schema_version": 1,
  "created_at": "UTC timestamp",
  "source": "api",
  "correlation_id": "uuid",
  "idempotency_key": "client key",
  "redacted_metadata": {},
  "encrypted_payload": "Fernet ciphertext"
}
```

### 7.2 Event Types

- profile.upserted
- settings.roast_changed
- transaction.recorded
- judgment.reason_requested
- transaction.reason_added
- judgment.completed
- judgment.corrected
- share.viewed
- share.clicked
- account.revoked
- legacy.imported
- data.deletion_requested

### 7.3 Redis Keys

```text
ledger:{user_ref}:events                         Redis Stream
ledger:{user_ref}:profile                        encrypted JSON
ledger:{user_ref}:settings                       encrypted JSON
ledger:{user_ref}:transactions                   sorted set by occurred_at
ledger:{user_ref}:transaction:{transaction_id}   encrypted JSON
ledger:{user_ref}:judgment:{judgment_id}         encrypted JSON
ledger:{user_ref}:correction:{judgment_id}       encrypted latest correction projection
ledger:{user_ref}:pending_question               encrypted JSON
ledger:{user_ref}:idempotency:{key}              encrypted cached result
ledger:{user_ref}:legacy_imported                 marker
```

Repository writes must append the event and update projections atomically with a Redis pipeline transaction where supported.
All mutations for one user are serialized by one user-scoped Redis lock. This prevents two different idempotency keys from overwriting the single active pending question while allowing different users to proceed independently.

### 7.4 Idempotency

- POST and DELETE endpoints require Idempotency-Key.
- Repeated keys return the original status and body without adding another event.
- Production Kakao/RQ requires a verified platform request/job identifier and derives the idempotency key from it. Development/test may generate a temporary identifier only for local execution.
- Idempotency records follow the same retention and deletion policy as user data.

### 7.5 Legacy Import

On first access:

1. Check ledger:{user_ref}:legacy_imported.
2. Read legacy user_state:{raw_transport_user_id} only inside the transport migration boundary.
3. Import only category counts, emotion labels, and message-count metadata.
4. Do not create fake monetary transactions.
5. Emit one legacy.imported event and marker.
6. Preserve the old key for rollback until a separately approved cleanup task.

## 8. Judgment Pipeline

### 8.1 Initial Signal Formula

The first calibrated policy uses:

```text
risk_score = clamp(
    0.30 * budget_usage_after
  + 0.25 * transaction_budget_share
  + 0.20 * goal_pressure
  + 0.15 * normalized_baseline_deviation
  + 0.10 * normalized_recurrence
  - 0.25 * essentiality,
  0,
  1
)
```

Initial reason-question triggers:

- risk_score is between 0.35 and 0.75 inclusive; or
- category is unknown; or
- a high-budget-share transaction lacks a reason; or
- profile/history completeness produces data_confidence below 0.75.

Policy term definitions for `overspending-v1`:

- `normalized_baseline_deviation = clamp(baseline_deviation / 2, 0, 1)`.
- `normalized_recurrence = clamp(recurrence_30d / 5, 0, 1)`.
- History is sparse until three prior transactions exist.
- `data_confidence` starts at 1.0, subtracts 0.35 for an incomplete profile and 0.30 for sparse history, then clamps to 0..1.
- `goal_pressure` is required monthly goal savings divided by disposable monthly income, clamped to 0..1. Required monthly savings is the remaining goal gap divided by remaining months. Disposable income is income minus fixed expenses and debt payments.
- When fixed expenses plus debt payments meet or exceed income, `goal_pressure` is 1.0.

Weights and thresholds may change only through a versioned policy and labeled evaluation.

### 8.2 State Machine

```text
transaction.recorded
  -> signals_computed
  -> awaiting_reason | judged

awaiting_reason
  -> reason_added
  -> judged

judged
  -> corrected
```

Rules:

- Profile absence rejects transaction creation with profile_required.
- Exactly one reason question is permitted per transaction.
- At most one unanswered reason question may exist per user; concurrent attempts are serialized and cannot overwrite it.
- A repeated reason submission is idempotent.
- Corrections append an audit event and update a separate latest-correction projection. Reads expose original_label, effective_label, and correction while the original judgment remains immutable.
- Roast state is read only during rendering.

### 8.3 AI Input Allowlist

OpenAI receives only:

- transaction amount or amount bucket;
- normalized category;
- deterministic ratios and factor names;
- recurrence count;
- sanitized user reason;
- policy version.

OpenAI never receives:

- raw user identifier or user_ref;
- account number, provider token, or source reference;
- exact asset, income, balance, debt, or fixed-expense values;
- raw merchant name;
- unsanitized free text;
- unrelated chat history.

### 8.4 OpenAI Responses Contract

Use client.responses.create with store=false and strict JSON Schema output.

Required output fields:

- label
- confidence
- rationale
- recommended_action
- decision_factors
- normal_message
- roast_message

If the response fails schema validation, retry once with the same allowlisted input. If the retry fails or OpenAI is unavailable, use deterministic-fallback-v1 and set fallback_used=true.

Fallback judgments are auditable and usable for continuity, but excluded from the 85% live-AI agreement claim.

## 9. Rendering and Roast Safety

Both messages are generated from one JudgmentResult.

Normal mode:

- direct and non-shaming;
- explains the deciding factors;
- gives one concrete next action.

Roast mode:

- opt-in and default off;
- Korean market-grandmother character;
- household metaphors, ledger-inspection tone, and caring scolding;
- may be provocative but cannot use credible threats, protected-trait abuse, self-harm encouragement, poverty/debt humiliation, or coercion;
- must acknowledge justified purchases;
- cannot reveal sensitive financial values.

Rendered output validation is separate from judgment policy. A renderer failure cannot change label or recommended action.

## 10. Read-only Account Adapter

The domain port supports only:

- list_connections
- fetch_balances
- fetch_transactions
- revoke_connection

No transfer, payment, withdrawal, savings execution, or order method may exist in the MVP port.

Implementations in this milestone:

- ManualTransactionSource
- SyntheticReadOnlyAccountAdapter
- DisabledProductionAccountAdapter

Production provider access returns provider_unavailable until a separately approved integration task is completed.

## 11. REST API Contract

All JSON responses use:

```json
{"data": {}, "meta": {"correlation_id": "uuid"}}
```

Errors use:

```json
{"error": {"code": "machine_code", "message": "safe message"}, "meta": {"correlation_id": "uuid"}}
```

Routes:

- GET /health: process liveness.
- GET /ready: repository/config readiness.
- GET /api/v1/me/profile
- PUT /api/v1/me/profile
- GET /api/v1/me/settings
- PUT /api/v1/me/settings
- GET /api/v1/me/transactions
- POST /api/v1/me/transactions
- GET /api/v1/me/transactions/{transaction_id}
- POST /api/v1/me/transactions/{transaction_id}/reason
- POST /api/v1/me/judgments/{judgment_id}/corrections
- POST /api/v1/me/judgments/{judgment_id}/share-view
- POST /api/v1/me/judgments/{judgment_id}/share
- GET /api/v1/me/summary
- GET /api/v1/me/metrics
- POST /api/v1/me/accounts/{connection_id}/revoke
- DELETE /api/v1/me/data

Transaction creation returns:

- 201 with judgment when no reason is needed.
- 202 with pending_question when a reason is required.
- 409 profile_required when onboarding is incomplete.

### 11.1 Authentication Boundary

- development/test: X-User-Id is accepted only when APP_ENV is development or test and ALLOW_DEV_AUTH=1.
- production: X-User-Id is always rejected.
- production REST routes return AUTH_NOT_CONFIGURED until a trusted auth provider is separately selected.
- Kakao user identity is resolved only inside the Kakao transport from the verified platform payload.
- Production Kakao requests require `KAKAO_WEBHOOK_SECRET`, and callback URLs must match the exact host allowlist in `KAKAO_CALLBACK_HOSTS` before any outbound request is queued.
- Production Kakao requests without a verified platform request identifier are rejected instead of receiving a generated idempotency key.

## 12. Privacy, Encryption, and Retention

### 12.1 Data Classes

- Secrets/tokens: never logged or prompted; encrypted when storage is ever introduced.
- Direct identifiers: converted to HMAC user_ref before domain/storage.
- Raw financial values: encrypted at rest; excluded from external sinks.
- Free text: sanitized before prompts; encrypted at rest.
- Derived metrics: allowed only through an explicit sink allowlist.
- Share fields: label, privacy-safe Roast message, generic category, recommended action.

### 12.2 Encryption

- Fernet encryption via cryptography>=46,<48.
- LEDGER_ENCRYPTION_KEY is required in production.
- LEDGER_USER_REF_SECRET is required in production for HMAC-SHA256 pseudonyms.
- Development/test may generate ephemeral secrets with a warning.
- Key material is never written to logs or Redis.

### 12.3 Retention

- LEDGER_RETENTION_DAYS defaults to 365.
- Cleanup removes expired sensitive event streams, projections, pending questions, and idempotency records.
- User deletion overrides retention immediately.
- Deleted or expired aggregates are ignored during replay/rebuild.

### 12.4 Revocation and Deletion

POST /api/v1/me/accounts/{connection_id}/revoke:

- calls the provider revocation port when configured;
- deletes stored credential references;
- emits account.revoked;
- returns provider_unavailable when no production provider exists.

DELETE /api/v1/me/data:

1. Append data.deletion_requested.
2. Purge the user's events, projections, transactions, judgments, pending question, idempotency records, and credential references.
3. Remove any transport-to-user mapping.
4. Emit only a non-linkable deletion completion metric with random deletion_id and timestamp.
5. Return 204.

## 13. Telemetry and Sheets

Allowed structured event fields:

- event_type
- event_id
- pseudonymous user_ref
- label
- confidence_band
- adapter_source
- reason_question_asked
- fallback_used
- correction_flag
- share_flag
- latency_ms
- redaction_status
- policy_version

Sheets may receive only these redacted fields. Raw user messages, assistant messages, amounts, merchants, income, assets, debt, reasons, or account identifiers are forbidden.

## 14. Evaluation and Tests

### 14.1 Versioned Evaluation Fixture

tests/fixtures/judgment_scenarios_v1.json contains labeled cases for:

- necessary high-cost purchase;
- repeated low-cost discretionary spending;
- emergency expense;
- goal-threatening purchase;
- reimbursable purchase;
- merchant/category misclassification;
- sparse history;
- conflicting explanation;
- normal/Roast parity;
- false-positive correction.

The evaluation report separates label agreement from tone quality and excludes deterministic fallback calls from a live-model claim.

### 14.2 Test Matrix

Unit:

- domain validation;
- signal formula and boundaries;
- state transitions and one-question limit;
- strict judgment schema parsing;
- fallback marker;
- Normal/Roast semantic parity;
- redaction and sanitizer;
- encryption/config fail-closed behavior;
- idempotency;
- legacy import.

Integration:

- manual profile, transaction, reason, and judgment flow;
- local Redis event/projection behavior when Redis is available;
- user-scoped Redis mutation serialization and pending-question concurrency;
- app/worker Redis projection sharing and RQ storage-mode guards;
- synthetic provider contract;
- correction/audit flow;
- share metrics;
- deletion and revocation;
- production dev-auth rejection;
- Sheets redaction.

E2E:

- Flask test-client REST flow;
- Kakao webhook/RQ callback flow with fake judge and repository.

Commands:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall app.py tasks.py worker.py ledger tests
LEDGER_TEST_REDIS_URL=redis://127.0.0.1:6389/15 python3 -m unittest tests.integration.test_redis_repository -v
```

## 15. Environment

- APP_ENV: development, test, or production.
- REDIS_URL: required for Redis storage and RQ.
- LEDGER_STORE: redis or memory; memory is forbidden in production and cannot be used by the RQ worker. Kakao runs inline when the store is memory-backed.
- OPENAI_API_KEY: optional only when deterministic fallback is acceptable.
- OPENAI_LEDGER_MODEL: defaults to gpt-4o for backward compatibility.
- LEDGER_ENCRYPTION_KEY: Fernet key; required in production.
- LEDGER_USER_REF_SECRET: HMAC secret; required in production.
- LEDGER_RETENTION_DAYS: defaults to 365.
- ALLOW_DEV_AUTH: must be 1 to accept X-User-Id outside production.
- KAKAO_WEBHOOK_SECRET: required to authenticate the production Kakao webhook transport.
- KAKAO_CALLBACK_HOSTS: comma-separated exact callback hosts allowed in production.
- GOOGLE_SHEET_ID and GOOGLE_CREDENTIALS_JSON: optional redacted telemetry sink only.

## 16. Dependencies

- Python 3.11.6
- Flask
- redis-py
- RQ
- OpenAI Python SDK with Responses API support
- cryptography>=46,<48
- requests
- python-dotenv
- gunicorn
- optional gspread and google-auth for redacted telemetry

No new database, auth provider, or financial-data provider is introduced in this milestone.

## 17. External Provider Constraints

KFTC Open Banking documents OAuth-based account registration and balance/transaction inquiry. Production use requires an approved application, user consent, security review, and separate provider/compliance work.

References:

- https://developers.kftc.or.kr/dev/openapi/open-banking/oauth
- https://developers.kftc.or.kr/dev/openapi/open-banking/transaction
- https://developers.kftc.or.kr/dev/starter/starter
- https://www.fsc.go.kr/no010101/84780

## 18. Decisions Log

| Date | Decision | Result |
| --- | --- | --- |
| 2026-08-01 | Product direction | Pivot from persona-first spending chatbot to AI household-ledger agent |
| 2026-08-01 | MVP authority | Read, ask, judge, and advise only |
| 2026-08-01 | Overspending | Hybrid deterministic signals plus AI final judgment |
| 2026-08-01 | Roast | Opt-in renderer only; judgment parity is invariant |
| 2026-08-01 | Account data | Production read-only linking preferred but manual entry is mandatory fallback |
| 2026-08-01 | Storage | Redis Streams events plus projections; schema portable to Postgres |
| 2026-08-01 | Privacy | Encrypted sensitive payloads and allowlisted external sinks |
| 2026-08-01 | Stop boundary | Backend complete, stop before UI/UX design |
