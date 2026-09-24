# Development Plan - AI Household Ledger Agent

## Current State

- Phase: 8 - AI spending-plan coach
- Active task: Task 7.4 iPhone Home Screen web app setup
- Approval: 2026-08-01 user-approved replacement of the legacy product, TECHSPEC, PLAN, and backend
- UI/UX approval: 2026-08-03 user-approved domestic-ledger benchmarking and joint design start
- Branch: `main`
- Sources of truth: `TECHSPEC.md` for product/backend invariants, `DESIGN.md` for UI/UX decisions
- Last pre-pivot commit: `64b46ae`

## Task 2.0 - AI Ledger Backend Pivot (Completed)

> Historical contract. Task 6.7 supersedes the reason-question and mode-interaction rules below while preserving the evidence and judgment invariants.

### Goal

Replace the persona-first spending chatbot with a privacy-first AI household-ledger backend that can store a financial profile, accept manual transactions, compute deterministic risk signals, ask exactly one reason question when context is weak, produce a structured AI judgment, and render that same judgment in a default or opt-in `욕쟁이 할머니 모드` voice.

### Stop Boundary

Stop and report after backend implementation and local verification. Do not make UI/UX, visual design, information architecture, screen, or share-card design decisions without the user.

Do not add production account-provider integration, production authentication, deployment, payment blocking, transfers, automatic savings, investments, or any money-movement capability.

### Ordered Checkpoints

- [x] Replace `TECHSPEC.md` with the approved pivot contract.
- [x] Replace the legacy execution queue with this backend plan.
- [x] Add domain models, event contracts, repository ports, and privacy primitives.
- [x] Add Redis Streams and in-memory repositories with encrypted projections and idempotency.
- [x] Add deterministic signals, one-question state machine, structured OpenAI judge, and deterministic fallback.
- [x] Add 기본 말투/욕쟁이 할머니 모드 parity rendering and safety validation.
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
- `욕쟁이 할머니 모드` defaults off and changes only the selected message, never label, confidence, rationale, factors, or recommendation.
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

## Task 3.0 - Benchmark-led UI/UX Foundation (Completed)

> Historical design contract. Task 6.7 supersedes the presentation-only mode rule and list-first ledger default below.

### Goal

Define the mobile-first household-ledger information architecture and a distinct visual direction before frontend implementation. Preserve familiar Korean ledger behavior while making the AI agent's pending questions, evidence, and advice visible without turning the product into a chat-first novelty.

### Scope

- Research current official materials for established Korean finance and household-ledger products.
- Translate the supplied warm-paper Notion references into a finance-appropriate visual system.
- Define onboarding, home, ledger, manual entry, agent, judgment, reports, goals, settings, and sharing flows.
- Define 기본 말투/욕쟁이 할머니 모드 mode interaction and content-safety rules without changing judgment logic.
- Create one focused mobile home-screen visual candidate for user review.
- Stop at the visual approval gate. Do not implement frontend routes or components in this task.

### Ordered Checkpoints

- [x] Review current product/backend contracts and user-provided references.
- [x] Research current official sources for Toss, Banksalad, Money Manager, and Smart Money.
- [x] Create the canonical `DESIGN.md` foundation.
- [x] Generate and inspect one mobile home-screen visual candidate.
- [x] Record unresolved design decisions and request visual approval.
- [x] Run documentation checks, append `progress.txt`, and create one scoped local commit.

### Acceptance Criteria

- `DESIGN.md` records observed benchmark patterns separately from product design decisions.
- The primary navigation and every MVP screen have a clear user job.
- Manual entry remains first-class while account connection remains future-facing and read-only.
- The AI asks for context in a transaction-bound flow rather than becoming a generic chatbot.
- `욕쟁이 할머니 모드` is visibly opt-in, instantly reversible, and presentation-only.
- Financial amounts and evidence remain more visually prominent than character decoration.
- The design uses the supplied warm-paper, bold-type, flat-card references without copying Notion's marketing composition.
- Accessibility, responsive behavior, loading/empty/error states, and Korean financial-number formatting are specified.
- No frontend implementation starts before the user approves a visual direction.

## Task 3.1 - Full Visual Screen Set (Completed)

> Historical implementation contract. Task 6.7 supersedes the presentation-only mode rule below.

### Goal

Create an implementation-ready image reference for every MVP screen using the user-approved Home direction. Keep the visual system coherent across the complete journey before writing frontend code.

### Screen Set

- Trust onboarding
- Financial baseline
- Goal setup
- Data-source choice
- Home (approved reference)
- Manual transaction entry
- Reason question
- 기본 말투 판단
- 욕쟁이 할머니 모드 판단
- Ledger
- Transaction detail and correction
- Agent inbox
- Monthly report
- Settings
- Privacy-safe share preview

### Ordered Checkpoints

- [x] Persist the approved Home reference in `design/screens/v1`.
- [x] Generate the remaining 14 screens in the approved visual direction.
- [x] Inspect Korean copy, hierarchy, visual continuity, and safety/privacy states.
- [x] Add a screen index with implementation notes and known generation deviations.
- [x] Update `DESIGN.md`, append `progress.txt`, verify image dimensions, and create one scoped local commit.

### Acceptance Criteria

- Every screen is a separate image in the same mobile aspect ratio.
- Home remains the visual source of truth for palette, typography, spacing, and illustration treatment.
- Images show one primary job per screen rather than feature inventory.
- 기본 말투와 욕쟁이 할머니 모드 판단 화면은 모든 금융 사실을 공유하고 표현 문구와 모드 상태만 다르다.
- Manual entry is live; account connection remains explicitly future/read-only.
- Generated Korean copy is readable enough to guide implementation; any image-generation artifacts are documented rather than copied into code.
- No frontend code is implemented in this task.

## Task 4.0 - Complete Responsive Web/PWA Implementation (Completed)

### Goal

Implement the user-approved 15-screen visual set as a complete mobile-first web app and installable PWA. Connect the live UI to the existing Flask ledger API while preserving backend ownership of financial judgment, confidence, evidence, recommendation, and 기본 말투/욕쟁이 할머니 모드 parity.

### Scope

- Add a React, Vite, and TypeScript frontend with one reusable design-token and component system.
- Implement every screen and primary action defined in `design/screens/v1/README.md`.
- Connect onboarding, profile, settings, manual transactions, reason answers, judgments, corrections, sharing, summary, and privacy actions to the existing API.
- Add deterministic demo fixtures only for visual QA and first-run previews; never use frontend fixtures to make a live judgment.
- Add responsive mobile, tablet, and desktop shells, PWA metadata, loading, empty, error, offline, focus, and reduced-motion states.
- Serve the production frontend build from Flask without weakening the API authentication or privacy boundaries.
- Stop after local implementation, visual QA, automated verification, documentation updates, and one scoped local commit. Do not push or deploy.

### Ordered Checkpoints

- [x] Lock this implementation task and verify the existing API contracts.
- [x] Add the frontend runtime, API client, state model, routes, PWA metadata, and shared visual tokens.
- [x] Implement onboarding, Home, manual capture, reason, and default/grandma-mode judgment flows.
- [x] Implement ledger, transaction detail/correction, agent inbox, report, settings, and privacy-safe sharing.
- [x] Add Flask production static serving and focused backend/frontend tests.
- [x] Run typecheck, lint, unit tests, production build, Flask tests, and real local API flow checks.
- [x] Capture the 15 approved states at 390x844, compare against references, and iterate on material visual differences.
- [x] Verify 360px, 390px, 430px, tablet, desktop, keyboard focus, reduced motion, and offline draft behavior.
- [x] Update `README.md`, this plan, append `progress.txt`, and create one scoped local commit.

### Acceptance Criteria

- All 15 approved screen contracts exist as reachable responsive routes or states and every primary action is interactive.
- The 390x844 implementation preserves the approved warm-paper palette, bold editorial hierarchy, flat fills, amount emphasis, and mobile navigation.
- Live labels, confidence, evidence, recommendation, and 기본 말투/욕쟁이 할머니 모드 messages come from the backend judgment artifact.
- `욕쟁이 할머니 모드` remains opt-in, immediately reversible, and presentation-only.
- Manual transaction entry works without account connection and retains an unsent draft offline.
- Account connection remains visibly future/read-only and cannot initiate money movement.
- Sharing begins from a redacted preview with amount and merchant excluded by default.
- Loading, empty, error, fallback, correction, offline, focus, screen-reader, and reduced-motion behavior are represented.
- Flask can serve a successful production frontend build while `/api/v1`, `/health`, `/ready`, and Kakao routes retain their existing behavior.
- Frontend typecheck, lint, tests, build, backend tests, local HTTP smoke, and visual screenshot checks pass, or any explicit validation gap is reported.

## Task 5.0 - Vercel Frontend Production Deployment (Completed)

### Goal

Deploy the verified Vite/PWA frontend to Vercel production without misrepresenting the unavailable production backend, authentication, Redis, or live OpenAI path as complete.

### Scope

- Add Vercel SPA routing configuration and ignore local Vercel project metadata.
- Use build-time demo mode for the first public frontend deployment so every approved screen remains usable without production financial storage.
- Link a dedicated Vercel project, deploy production, and verify the public URL and deep routes.
- Keep the Flask API, RQ worker, Redis, authentication, and secrets out of Vercel until their production runtime is configured separately.

### Ordered Checkpoints

- [x] Re-check the production boundary, current Vercel account, and project inventory.
- [x] Add deterministic Vercel/Vite SPA deployment configuration.
- [x] Run frontend tests, lint, audit, and production build with demo mode enabled.
- [x] Deploy to a dedicated Vercel production project and inspect deployment readiness.
- [x] Verify the public Home, onboarding, deep route, manifest, service worker, and asset responses.
- [x] Update deployment documentation, append `progress.txt`, and create one scoped local commit.

### Acceptance Criteria

- The production URL serves the frontend and all client-side routes resolve on direct navigation.
- The deployed build is explicitly demo-backed until the production API and authentication are connected.
- No backend secret, Redis credential, OpenAI key, or Vercel project metadata enters Git.
- The existing Flask/RQ/Redis architecture and production authentication fail-closed contract are not weakened for deployment convenience.
- Verification distinguishes Vercel frontend readiness from backend/live-AI readiness.

## Task 6.0 - Trusted Production Backend Setup (Provider configured; authenticated E2E pending)

### Goal

Replace the frontend-only demo boundary with a fail-closed production web path: Supabase Auth issues short-lived user JWTs, Flask verifies asymmetric signatures and claims, Render hosts the API, Upstash provides TLS Redis persistence, and Vercel calls the API with the authenticated session token.

### Scope

- This task is the dedicated authorization to revise `TECHSPEC.md` for the selected production auth and deployment architecture.
- Add Supabase email/password authentication to the web app and send only the session access token to Flask.
- Verify production bearer tokens against the project JWKS, issuer, audience, expiry, and required subject before deriving the existing HMAC pseudonym.
- Add an exact-origin CORS allowlist for the Vercel production domain.
- Add a Render Blueprint that keeps credentials out of Git and generates application encryption/HMAC secrets inside Render.
- Use Upstash Redis over TLS for the production repository.
- Keep Kakao/RQ out of the free web deployment; RQ remains an optional Kakao-only transport for a later worker-capable runtime.
- Configure provider projects, environment variables, and Vercel live mode where existing authenticated sessions and approval boundaries permit.

### Ordered Checkpoints

- [x] Confirm Supabase JWT, Render Blueprint, and Upstash security contracts against current official documentation.
- [x] Revise `TECHSPEC.md` and deployment documentation with the selected architecture and free-tier limitations.
- [x] Add production JWT verification, fail-closed configuration, and exact-origin CORS tests.
- [x] Add frontend Supabase session handling, email sign-in, bearer API client, sign-out, and production API base URL support.
- [x] Replace the initial magic-link UX with user-approved email/password login and immediate signup.
- [x] Add `render.yaml` with non-secret configuration, generated application secrets, and prompted provider credentials.
- [x] Run backend/frontend tests, lint, build, compile, dependency audit, and a secret scan of the intended diff.
- [x] Configure Supabase, Upstash, Render, and Vercel and verify public health/readiness where provider authentication permits.
- [ ] Complete the authenticated production transaction-to-judgment E2E with an owner-controlled test account.
- [x] Append `progress.txt` and create one scoped local commit without staging unrelated workspace files.

### Acceptance Criteria

- Production REST routes reject `X-User-Id`, missing bearer tokens, invalid signatures, wrong issuer/audience, expired tokens, and tokens without `sub`.
- A valid Supabase user token maps only its verified `sub` through the existing HMAC pseudonymization boundary.
- Browser requests are accepted only from the exact configured Vercel origin; credentials and wildcard origins are not enabled.
- No Redis URL, OpenAI key, Supabase secret/service-role key, encryption key, HMAC secret, or provider token enters Git, frontend bundles, command output, or chat.
- The browser receives only the Supabase project URL and publishable key, which are public client configuration by design.
- Render production startup requires Redis, trusted auth configuration, encryption, and pseudonymization secrets.
- Upstash transport uses TLS and sensitive ledger payloads remain application-encrypted at rest.
- The free Render deployment does not claim an always-on SLA and does not run the RQ/Kakao worker.
- Local verification passes; provider deployment and real authenticated API behavior are reported separately with direct evidence or an explicit login/credential blocker.

## Task 6.1 - Post-deployment UX Correction (Release approved)

### Goal

Correct the first production usability defects without changing the financial judgment contract: replace vague auth copy, simplify the overlapping bookkeeper mark, make KRW fields fully replaceable, and prevent demo values or fixed dates from appearing as live user data.

### Scope

- Refresh the login hero around the product's concrete benefit and keep the form visible earlier in the first viewport.
- Render the bookkeeper as one canonical avatar mark with a separate optional label instead of overlapping icons and a stamp.
- Add one reusable KRW input that supports an empty editing state, select-all replacement, digit-only input, formatted display, and explicit minimum validation.
- Apply the KRW input to the baseline, goal, and manual transaction flows.
- Replace hard-coded live month/date labels and truthy fallbacks that turn valid zero values into demo amounts.
- Preserve demo fixtures only when explicit demo mode is active.
- Run focused component tests, the full frontend suite, lint, build, and responsive visual QA.
- Stop and report before commit, push, or deployment.

### Acceptance Criteria

- A user can clear `1`, type `800000`, and leave the field as `800,000원` without an inserted leading digit.
- Mobile number inputs show no browser stepper and expose an appropriate numeric keyboard hint.
- The login hero explains recording, budget/goal context, and reason-first judgment without implying money custody.
- Every `BookkeeperMark` contains one avatar icon and no overlapping decorative icon.
- Live zero spend, zero income, and empty category data remain zero or empty instead of showing demo fixtures.
- Visible dates and month labels come from the current date or API summary outside explicit demo mode.
- No backend judgment, 욕쟁이 할머니 모드 parity, authentication, privacy, or money-movement boundary changes.
- Release only after explicit user approval; approval was granted on 2026-08-05.

## Task 6.2 - 욕쟁이 할머니 모드 Naming and Voice Correction (Release approved)

### Goal

Replace the foreign-facing Roast label with the exact Korean product name `욕쟁이 할머니 모드`, and make every generated or fallback line feel like evidence-based household-ledger scolding rather than a generic insult or a hard-coded cafe joke.

### Scope

- Replace every user-facing `Roast` or `Normal` mode label with `욕쟁이 할머니 모드` and `기본 말투`.
- Preserve `roast_enabled`, `roast_message`, and `mode=roast` as internal API/schema identifiers for backward compatibility.
- Render the backend judgment message as the primary headline instead of a category-specific hard-coded sentence.
- Require the mode voice to include a recognizable grandmother marker, a household or ledger metaphor, supplied evidence, and the recommended next action.
- Keep the same label, confidence, evidence, rationale, and recommendation in both voices.
- Keep threats, death/self-harm language, slurs, protected-trait attacks, appearance insults, sexual humiliation, and invented personal facts blocked.
- Update web, Kakao, fallback, OpenAI prompt, tests, and current design/release documentation.
- Stop and report before commit, push, or deployment.

### Acceptance Criteria

- No user-facing web or Kakao copy uses `Roast` or `Normal` as a mode name.
- Justified spending receives a grudging acknowledgement rather than a contradictory scolding verdict.
- Caution and overspending copy cites supplied spending evidence and ends with the same recommended action as the structured judgment.
- A bland, unsafe, or off-character model response falls back to a deterministic safe grandmother-mode line.
- Judgment headlines work for every category and no longer contain a hard-coded cafe-name joke.
- Focused mode-copy tests, the full frontend suite, lint, build, backend tests, compile checks, and responsive browser QA pass.

## Task 6.3 - Manual Transaction Submit Repair (Release approved)

### Goal

Ensure a formatted KRW amount never triggers silent browser constraint validation and prevent the manual transaction form from appearing unresponsive when the user requests an AI judgment.

### Scope

- Remove the numeric-only HTML pattern that conflicts with comma-formatted currency values.
- Keep numeric keyboard hints and digit-only input sanitization in the shared currency input.
- Route validation through the manual transaction form's visible application error state instead of native browser blocking.
- Add a regression test that submits a form while the amount is rendered as `12,800`.
- Stop and report before commit, push, or deployment.

### Acceptance Criteria

- A comma-formatted amount is a valid form control.
- Clicking `기록하고 판단받기` invokes the submit handler and advances to the reason or judgment route.
- The full frontend test suite, lint, production build, and a real browser submission pass.

## Task 6.4 - Production Trust, Reliability, and UX Hardening (Completed)

### Goal

Close the highest-risk production gaps found in the full-service audit without changing the approved financial-judgment policy: isolate browser drafts per authenticated user, make retries idempotent, prevent load failures from masquerading as new accounts, bound AI cost, and remove misleading or non-functional product states.

### Scope

- Scope browser financial drafts to the authenticated user and clear them on sign-out and data deletion.
- Preserve one client operation identifier across transaction retries so a lost response cannot duplicate a ledger entry or AI judgment.
- Distinguish profile absence from API failure and provide a recoverable error state.
- Add Redis-backed per-user judgment limits, explicit OpenAI timeout/retry bounds, and redacted fallback diagnostics.
- Replace scan-based judgment lookup with a direct transaction index and return transactions newest-first.
- Keep corrected judgments and live share previews consistent with the effective judgment.
- Count share views separately from successful native shares or image downloads.
- Remove or clearly disable UI controls that do not perform the action they promise.
- Add a repeatable agreement evaluator for the versioned human-labeled judgment fixture without representing fallback results as live-AI quality.
- Update deployment and operator documentation, run full verification, then create one scoped commit and deploy it to the existing Vercel and Render production path.

### Acceptance Criteria

- One user's local financial draft cannot be loaded by another user on the same browser and no financial draft survives that user's sign-out or full data deletion.
- Retrying a transaction after an ambiguous network failure reuses the same idempotency key.
- A backend load failure shows a retryable error and never redirects an existing user into onboarding.
- Production judgment requests are bounded per pseudonymous user in Redis and return a safe `429` without invoking OpenAI after the limit.
- OpenAI timeout/retry configuration is explicit and fallback diagnostics contain no financial values, free text, or user identifier.
- Existing Redis records remain readable while new judgment lookups use a direct transaction index.
- Persisted transaction lists render newest-first after reload.
- Live share content never uses demo fixtures, corrected labels are honored, and share success is recorded only after a completed share/download action.
- Visible production controls either work, are explicitly unavailable, or are removed; no local-only success message claims server persistence.
- Frontend tests/lint/build, backend tests/compile, dependency audit, secret scan, local browser smoke, and public deployment health checks pass or an external credential gap is reported explicitly.

## Task 6.5 - Demo and Cross-screen Data Consistency (Completed)

### Goal

Eliminate contradictory financial values and judgment evidence across the demo Home, reason, judgment, report, and settings flows so one underlying fixture always produces one user-visible truth.

### Scope

- Derive Home budget usage, remaining budget, and goal progress from the same profile and summary records used by Report and Settings.
- Keep the demo reason-question recurrence count aligned with the judgment artifact's recurrence evidence.
- Align the demo judgment budget evidence with the current demo monthly summary.
- Add focused regression coverage for budget, goal, and recurrence consistency.
- Do not change the production API, deterministic judgment policy, authentication, storage, or provider configuration.

### Ordered Checkpoints

- [x] Record this user-approved consistency task and inspect every affected demo data path.
- [x] Add failing regression tests for the contradictory values.
- [x] Replace screen-specific demo constants with shared derived values.
- [x] Run the focused frontend tests, full frontend suite, lint, and production build.
- [x] Append the verified result to `progress.txt` and mark this task complete.

### Acceptance Criteria

- Home remaining budget equals discretionary budget minus monthly spending and its percentage matches Report.
- Home, Report, Settings, and onboarding show the same goal progress for the same profile.
- The reason-question recurrence count and judgment rationale describe the same occurrence number.
- The judgment budget-usage evidence matches the current demo summary instead of a separate hard-coded percentage.
- No production financial, security, privacy, or deployment behavior changes.

## Task 6.6 - Manual Transaction Form Clarity and Mobile Layout (Completed)

### Goal

Remove the misleading half-empty transaction-type control and make the native transaction date fully readable on narrow mobile screens without expanding the MVP beyond manual expense entry.

### Scope

- Replace the two-column transaction-type visual with a compact, non-interactive summary that clearly states the supported transaction type is `지출`.
- Give the native date input the full value column and remove the duplicate trailing chevron that competes with the browser calendar control.
- Preserve transaction creation, draft persistence, validation, routing, and backend contracts.
- Add focused regression coverage and verify the form at the 390px mobile viewport.
- Stop and report before commit, push, or deployment.

### Ordered Checkpoints

- [x] Record this resumed user-approved UI correction and inspect the current form structure.
- [x] Add regression coverage for the fixed expense type and accessible date field.
- [x] Implement the semantic form and responsive style changes.
- [x] Run the focused frontend tests, full frontend suite, lint, TypeScript, production build, and mobile browser check.
- [x] Append the verified result to `progress.txt` and mark this task complete.

### Acceptance Criteria

- The transaction form no longer resembles a two-option selector with one blank option.
- Users can immediately identify that the current manual entry records an expense.
- The full native date value remains visible and operable at 390px without a duplicate chevron.
- The submit flow and existing draft/idempotency behavior remain unchanged.
- No production API, judgment policy, authentication, storage, or provider configuration changes.

## Task 6.7 - Mode-aware Recording, Calendar Ledger, and AI Briefing (Completed)

### Goal

Reduce everyday recording friction while making the opt-in `욕쟁이 할머니 모드` deliberately interactive: normal mode records and judges without a reason step, grandma mode requires one transaction-bound reason for every expense, the ledger opens as a monthly calendar, and actual AI judgment artifacts power a useful weekly briefing.

### Scope

- This task is the dedicated authorization to revise `TECHSPEC.md` for the mode-specific reason workflow and weekly briefing contract.
- Preserve one deterministic signal policy, judgment labels, confidence handling, recommendations, corrections, and privacy boundaries across both modes.
- In normal mode, record and complete the best-available AI judgment without interrupting the user for a reason.
- In `욕쟁이 할머니 모드`, require one reason for every new expense before completing its judgment and prevent a second unanswered question from being overwritten.
- Make the monthly calendar the default ledger view, with daily totals, date selection, selected-day transactions, and date-aware expense entry.
- Aggregate stored transaction-level AI judgments into a weekly briefing with spend/count summary, top category, caution/overspending counts, one concrete concern, and one recommended improvement.
- Replace copy that falsely describes grandma mode as presentation-only or implies that normal mode always asks a question.
- Add backend and frontend regression coverage, then run full tests, lint, build, compile, and responsive browser verification.
- Stop and report before commit, push, or deployment unless the user explicitly requests release.

### Ordered Checkpoints

- [x] Inspect the current mode, reason, summary, ledger, agent, report, and test paths.
- [x] Revise `TECHSPEC.md` and add failing mode/briefing/calendar regression tests.
- [x] Implement the backend mode gate and judgment-backed weekly briefing.
- [x] Implement normal-mode immediate recording, grandma-mode reason UX, and date-aware entry.
- [x] Replace the ledger list default with a responsive monthly calendar and selected-day list.
- [x] Surface weekly AI briefing, improvement, and overspending callout in Agent and Report.
- [x] Run focused and full verification, responsive browser QA, and a secret/diff review.
- [x] Append `progress.txt` and mark this task complete.

### Acceptance Criteria

- Normal mode never returns or displays a reason question for a newly recorded expense and routes the user back to the ledger after a successful record.
- `욕쟁이 할머니 모드` returns exactly one reason question for every expense without a supplied reason, regardless of the deterministic risk band.
- A second unanswered grandma-mode expense cannot overwrite the first pending question.
- Both modes use the same deterministic signals, AI judgment schema, labels, recommendations, corrections, and safety rules.
- The ledger opens on a Korean Sunday-to-Saturday monthly calendar; selecting a date shows that day's records and adding from the selected date pre-fills the transaction date.
- The weekly briefing is derived from the authenticated user's real transactions and stored AI judgment artifacts, never fabricated demo content in live mode.
- Agent and Report clearly show weekly total/count, top category, AI-reviewed caution/overspending counts, one concern, and one next action when evidence exists.
- Empty states remain honest and useful when no transactions or judgments exist.
- Backend tests, frontend tests, lint, TypeScript/build, compile, and 390px plus desktop browser checks pass.

## Task 6.8 - Regret-aware Personal Spending Coach (Completed - release approved)

### Goal

Differentiate the product from a generic AI ledger by learning each user's own definition of a worthwhile or regretted purchase, then turning those reflections and stored AI judgments into one measurable weekly behavior change.

### Scope

- This task is the dedicated user authorization to revise `TECHSPEC.md` for regret reflection, editable spending rules, regret-aware briefings, and behavior-change metrics.
- Let users reflect on a judged expense as `well_spent`, `unsure`, or `regretted`, with an optional short note, without deleting or rewriting the original transaction or AI judgment.
- Store up to eight editable personal spending rules in the existing encrypted settings projection and include them in the allowlisted AI judgment context.
- Aggregate reflected transactions into regret count, regret amount, regret rate, the strongest repeated regret category, and a deterministic goal-delay estimate.
- Make the weekly coach prioritize one concrete action from actual regret evidence, falling back to judgment evidence only when reflections are sparse.
- Surface the reflection control in transaction detail and the learned pattern, goal impact, one action, and personal rules in Agent, Report, and Settings.
- Keep normal recording uninterrupted and preserve the exact same labels, evidence, recommendations, and safety policy across 기본 말투 and 욕쟁이 할머니 모드.
- Add backward-compatible storage defaults so existing Redis records remain readable and user deletion purges every new projection and event.

### Ordered Checkpoints

- [x] Inspect the current transaction, settings, repository, summary, API, and frontend contracts.
- [x] Record the approved product contract in this plan and `TECHSPEC.md`.
- [x] Add failing backend and frontend regression tests for reflection, rules, and regret-aware coaching.
- [x] Implement domain, memory/Redis storage, service, API, and OpenAI allowlist changes.
- [x] Implement transaction reflection and Agent, Report, and Settings UI changes.
- [x] Run focused and full verification, responsive browser QA, and secret/diff review.
- [x] Update release documentation and append `progress.txt`; stop before commit, push, or deployment unless explicitly requested.

### Acceptance Criteria

- A user can set or replace one reflection per expense and the original transaction, AI judgment, and any judgment correction remain auditable.
- Existing transactions and settings written before Task 6.8 load with no reflection and no personal rules.
- Personal rules are user-editable, encrypted at rest, excluded from telemetry and shares, and sent to OpenAI only as sanitized allowlisted context.
- Weekly and monthly summaries never invent regret patterns; regret rates and goal impact are derived from reflected transactions and deterministic arithmetic.
- With enough reflections, the coach prioritizes the category with the most regretted transactions and proposes one bounded action for the next seven days.
- With sparse or no reflections, the UI explicitly asks for feedback or uses existing judgment evidence without presenting it as learned regret behavior.
- Normal recording remains uninterrupted and 욕쟁이 할머니 모드 remains optional and immediately reversible.
- Backend tests, Redis integration, frontend tests, lint, TypeScript/build, compile, and responsive browser checks pass.

## Task 7.0 - Core Ledger Parity Foundation (Completed locally)

### Goal

Make the product credible as a standalone Korean household ledger before expanding the AI layer. Match the web-compatible convenience baseline visible in Money Manager, Weple Money Pro, Wallet, Monefy, Toss, and Banksalad while keeping bank sync, SMS parsing, receipt OCR, widgets, and money movement outside this web MVP.

### Scope

- This task is the dedicated authorization to revise `TECHSPEC.md` for transaction kinds, manual accounts, category budgets, transaction maintenance, and deterministic cash-flow summaries.
- Support expense, income, and transfer entries while applying overspending judgment and regret coaching only to expenses.
- Add encrypted user-managed accounts/payment sources and require valid source/destination semantics for transfers.
- Add quick-entry suggestions derived from the user's recent records without sending extra data to AI.
- Add calendar/list views, transaction search, type/category/account filters, monthly income/expense/net totals, and previous-month comparison.
- Add deterministic category-budget status and remaining daily allowance.
- Add transaction editing and deletion with idempotent mutation routes and append-only audit evidence.
- Add privacy-safe CSV export in the authenticated browser.
- Preserve existing Redis records by defaulting missing transaction kinds to expense and missing settings collections to empty/default values.

### Explicit Deferrals

- Production bank/MyData sync, SMS notification parsing, receipt OCR, native widgets, family sharing, recurring background jobs, and automated money movement remain separate provider/platform tasks.
- AI must not calculate balances, totals, budget usage, or cash flow. It may only explain deterministic values and coach expense behavior.

### Ordered Checkpoints

- [x] Benchmark leading domestic and global ledger apps using official store/product evidence and record evidence limits.
- [x] Map the current product against the benchmark and rank the gaps.
- [x] Revise `PLAN.md` and `TECHSPEC.md` with the approved ledger-parity contract.
- [x] Add failing domain, service, repository, API, and frontend regression tests.
- [x] Implement backward-compatible ledger domain and encrypted persistence changes.
- [x] Implement faster entry, account/budget controls, maintenance actions, search/filter, and report improvements.
- [x] Run full backend/frontend verification, browser flow capture, and secret/diff review.
- [x] Append `progress.txt`, mark this task complete, and create one scoped local commit without pushing or deploying unless explicitly requested.

### Acceptance Criteria

- Users can record expense, income, and transfer entries without a bank connection.
- Transfers require two different accounts and never inflate income, expense, budget usage, category reports, or AI coaching.
- Only expenses invoke the judgment pipeline, reason workflow, reflection, and regret metrics.
- Existing transactions/settings load without migration downtime and behave as expense/default settings records.
- Users can find a transaction by merchant, memo, or category and narrow by type, category, and account.
- Calendar and list views show the same filtered source data and monthly totals.
- Category budgets expose spent, remaining, usage, and a remaining-days daily allowance using deterministic arithmetic.
- Users can edit or remove their own transaction and the monthly summary refreshes immediately.
- CSV export contains only the authenticated user's currently visible ledger fields and is generated locally without a third-party sink.
- Backend tests, Redis integration, frontend tests, lint, TypeScript/build, compile, and responsive browser checks pass.

## Task 7.1 - Kakao OAuth and TrackMyExpense Comparison (Completed Locally)

### Goal

Reduce Korea-first onboarding friction with Kakao Login while preserving the existing email/password fallback and Supabase user-ID ownership boundary. Compare the current product against TrackMyExpense using current official store and product evidence, then separate proven product advantages from ledger-parity gaps.

### Scope

- Add Kakao as the primary Supabase OAuth entry point without removing existing email/password authentication.
- Keep all backend authorization and financial-record ownership keyed by the verified Supabase `user.id`; never use Kakao nickname, email, or profile image as an identity key.
- Read optional Kakao nickname and profile-image metadata only for display and provide safe fallbacks for email users or missing consent.
- Document provider-console setup without placing Kakao credentials in Vercel, source files, tests, commands, or logs.
- Compare capture, core ledger, reports, AI, behavior change, localization, platform, privacy, and monetization using Google Play and the competitor's current product site.

### Explicit Deferrals

- Kakao Developers and Supabase dashboard activation require account-owner credentials and remain an external activation gate.
- Automatic account merging, legal-name collection, phone-number collection, Kakao friends, and KakaoTalk message permissions are excluded.
- Receipt OCR, voice capture, recurring transactions, offline sync, PDF/Excel export, and native app work remain separately approved ledger-parity tasks.

### Ordered Checkpoints

- [x] Add failing Kakao OAuth and login-page interaction tests.
- [x] Implement Kakao-first login with email/password fallback and optional display metadata.
- [x] Document the secret-safe Kakao Developers and Supabase activation path.
- [x] Record the TrackMyExpense comparison, evidence limits, current winner, and prioritized gaps.
- [x] Run frontend tests, lint, production build, and responsive browser verification.
- [x] Append `progress.txt`, mark this task complete locally, and report the provider activation gate without pushing or deploying unless explicitly requested.

### Acceptance Criteria

- The login screen exposes one clear primary Kakao action and retains usable email login and signup.
- The OAuth call uses the Supabase Kakao provider and a same-origin callback destination that can be allowlisted explicitly.
- Kakao OAuth failures are visible and do not remove the email fallback.
- A Kakao user's nickname/profile image may be displayed, but missing or mutable metadata never changes record ownership.
- No Kakao secret or provider token is bundled into frontend code or committed documentation.
- The comparison distinguishes official claims from code-verified current capabilities and does not claim review, revenue, or subscriber figures that the stores do not publish.
- Frontend tests, lint, TypeScript/build, and 390px/desktop browser checks pass.

## Task 7.2 - New Supabase Project and Kakao Login (Completed for login-only scope)

### Scope

- Resume the owner-approved provider setup on Supabase project `kkzsyprcujrxzrsognhb` (`jangbu-ai`, Jangbu AI, Seoul, Free).
- Connect Kakao app `1567306` (`장부`) through direct OIDC code exchange on Render and Supabase ID-token sign-in; keep the existing Kakao key and secret server-side.
- Use optional nickname/profile-image consent and allow Kakao users without email.
- Update the Vercel public Auth configuration and Render JWT issuer together after provider setup is verified.
- Preserve Redis data and encryption keys. A new Supabase project issues new user IDs; historical accounts/data are not automatically migrated or merged.
- Commit and push the reviewed Task 7.1/7.2 paths, deploy, and verify public routing separately from authenticated E2E.

### Checkpoints

- [x] Create the dedicated free Supabase project and register the production origin plus the two port-3015 local QA origins (2026-09-22).
- [x] Repoint Kakao app `1567306` to the new Supabase callback and preserve the existing optional profile consent (2026-09-22).
- [x] Connect and verify the new Supabase Kakao provider with email-less users allowed; its public authorize endpoint returns `302` to `kauth.kakao.com` (2026-09-22).
- [x] Run fresh frontend/backend checks and inspect the release diff for secrets (2026-09-22: 55 frontend tests, lint/build, 134 backend passes with 4 Redis-gated skips, compileall, diff and scoped credential-pattern checks).
- [x] Apply matching Vercel/Render settings, push, deploy, and verify service health (2026-09-23: Vercel production bundle contains only the current project ref; Render deployed `7346cd2`; `/health` and Redis-backed `/ready` returned 200).
- [x] Enable Kakao OIDC and add the production `/auth/kakao` redirect URI to the existing REST API key while retaining the Supabase callback (2026-09-23).
- [x] Deploy the Kakao OIDC ID-token sign-in path without the `account_email` scope. The existing Kakao key and secret are stored in Render; commit `3efc705` is live on Render and the existing Vercel production alias. The production start API returned an authorization URL with the correct callback, nonce, and S256 PKCE challenge and no `scope`; the real Kakao screen shows only optional nickname/profile-image consent (2026-09-23).
- [x] Verify owner-controlled Kakao consent without optional nickname/profile-image selections, callback, Supabase session, authenticated API access, session restoration after reload, sign-out, and repeat sign-in (2026-09-23). During the real test, the Render API rejected the valid session because its live `SUPABASE_URL` pointed at a different project despite the correct `render.yaml`; correcting that dashboard value and redeploying resolved the error. The existing Vercel project was redeployed with a logout button available before financial onboarding.

The Kakao login-only scope is verified in production. No financial profile or transaction was created during the login test. Transaction persistence, both modes, live AI quality, and physical-device checks remain separate product verification gates.

## Task 7.3 - First-run Introduction and Return Routing (Completed)

### Goal

Show a short, service-led introduction once per account. After it is acknowledged, resume incomplete financial setup; accounts with a saved profile enter Home directly.

### Scope

- Replace the first onboarding screen with the approved `장부 AI` introduction, one clear `시작하기` action, and a small privacy-details disclosure.
- Store the introduction acknowledgement in the authenticated user's Supabase metadata, separate from the financial profile and without financial values.
- Route profile-complete accounts to Home, and profile-incomplete accounts to their locally available setup step or the baseline step. Preserve the profile-load error retry state.
- Verify first login, reload, repeat login, established accounts, setup return, mobile and desktop layout, then commit, push, and deploy to the existing Vercel project.

### Checkpoints

- [x] Implement introduction copy, layout, and account-scoped acknowledgement.
- [x] Verify first-run and returning account routes with focused tests and browser checks.
- [x] Update design and deployment notes, append progress, commit, push, and deploy.

The account-controlled Kakao browser flow showed the introduction, advanced on `시작하기`, stayed on financial setup after reload, and skipped the introduction after logout and repeat login. Profile-complete direct Home routing is covered by a frontend test; no financial values were saved during this browser check.

## Task 7.4 - iPhone Home Screen Web App Setup (Active)

### Goal

Make the existing Vercel `jangbu-ai` site install cleanly from iPhone Safari as a persistent Home Screen web app with the correct name and icon for ongoing device testing.

### Scope and checks

- Reuse the existing PWA, Vercel project, and production domain; add iOS touch icon metadata and PNG assets derived from the existing icon.
- Set a consistent `장부 AI` install name, scope, and standalone launch behavior; refresh the service-worker shell cache.
- Verify asset dimensions, metadata, frontend tests, lint, build, and production HTTP responses, then commit, push, and deploy to the existing Vercel project.
- Open the deployed URL on the paired iPhone when available. Safari's Home Screen Add action remains an on-device user action; verify the icon with the user rather than claiming remote installation.

### Checkpoints

- [x] Add and verify iPhone/PWA icon assets and metadata.
- [x] Run local frontend checks and deploy the existing production project.
- [ ] Verify the physical Home Screen icon and launch after the owner taps Add on the iPhone. Production asset responses are already verified; CoreDeviceService currently prevents a remote Safari launch.

## Task 8.0 - AI Budget and Spending-Plan Coach (Completed Locally)

### Goal

Evolve the ledger into a plan-led spending coach. The user confirms one discretionary budget for an explicit period, reserves known expenses inside that same budget, follows deterministic date-segment progress, and receives one bounded qualitative AI action without giving the model authority over any financial number.

### Scope

- Add one encrypted active spending-plan projection with append-only activation, revision, check-in, and planned-expense-match events in memory and Redis.
- Store the plan period, confirmed discretionary budget, up to three priorities, deterministic weekly/date segments, planned expenses, version, history, status, and timestamps.
- Calculate actual spend only from in-period expense transactions where `exclude_from_budget=false`; keep total expense reporting unchanged.
- Define `total remaining = confirmed budget - actual spend`, `reserved remaining = unresolved planned expenses`, and `flexible remaining = total remaining - reserved remaining`, preserving negative shortfalls.
- Support non-persistent setup and revision previews, explicit activation/apply, maintain-or-adjust check-ins, and manual matching of one owned expense to one planned expense.
- Add a privacy-bounded qualitative plan advisor using OpenAI Responses strict JSON Schema, `store=false`, aggregate allowlisted input, deterministic numeric facts, and an honest fallback.
- Replace the bottom navigation with 홈/장부/계획/리포트; add the three-step Plan flow, plan-led Home, original/current/actual Report comparison, and post-expense plan impact.
- Revise `TECHSPEC.md` and `DESIGN.md` under this dedicated approved task and update implementation documentation.

### Ordered Checkpoints

- [x] Add deterministic plan domain models, progress formulas, matching rules, revisions, and check-ins.
- [x] Persist encrypted plan projections and append-only events in memory and Redis with idempotency and deletion coverage.
- [x] Add authenticated preview, activation, revision, check-in, and match APIs.
- [x] Add a strict-schema qualitative plan advisor with an aggregate allowlist and deterministic fallback.
- [x] Implement Plan setup/editing, active coaching, Agent-content consolidation, Home, Report, navigation, and post-expense impact.
- [x] Update product, technical, design, handoff, and append-only progress documentation.
- [x] Run backend, Redis, frontend, compile, lint, build, diff, secret-pattern, and responsive browser verification.

### Acceptance Criteria

- Code owns all budgets, totals, reservations, segment progress, before/after differences, and shortfalls; AI output contains qualitative narrative only.
- Preview endpoints never persist, and activation/revision/check-in/match mutations require idempotency keys and enforce ownership.
- Matching replaces an unresolved reservation with an already-counted actual expense and prevents one transaction from matching twice.
- Memory and Redis keep encrypted current projections, append-only plan events, backward-compatible empty defaults, and complete deletion behavior.
- The plan advisor never receives merchant, memo, raw reason, reflection note, account name, user identity, or a raw transaction list; timeout/schema/safety failure returns a marked deterministic fallback.
- Home uses `budget_spent_krw` for the legacy monthly budget fallback and plan/signals respect the configured timezone and excluded-expense flag.
- Setup, active progress, revision preview/apply, check-in, matching, Home, Report, nav, and post-expense impact are covered by frontend tests.
- Backend unit/integration/API tests, Redis integration when available, frontend tests/lint/build, compile, and browser QA pass or external limitations are reported precisely.

## Archived Work

Phase 1 migrated the old Kakao persona chatbot to the Responses API and added prompt/validator mechanics. Those commits remain in Git history, but their product plan is superseded by the 2026-08-01 pivot. Reuse is allowed only where it satisfies the new TECHSPEC invariants.
