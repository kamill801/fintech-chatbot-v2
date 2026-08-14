# Development Plan - AI Household Ledger Agent

## Current State

- Phase: 6 - production hardening
- Active task: none - Task 6.4 completed; the next product change requires a new approved task
- Approval: 2026-08-01 user-approved replacement of the legacy product, TECHSPEC, PLAN, and backend
- UI/UX approval: 2026-08-03 user-approved domestic-ledger benchmarking and joint design start
- Branch: `main`
- Sources of truth: `TECHSPEC.md` for product/backend invariants, `DESIGN.md` for UI/UX decisions
- Last pre-pivot commit: `64b46ae`

## Task 2.0 - AI Ledger Backend Pivot (Completed)

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

## Archived Work

Phase 1 migrated the old Kakao persona chatbot to the Responses API and added prompt/validator mechanics. Those commits remain in Git history, but their product plan is superseded by the 2026-08-01 pivot. Reuse is allowed only where it satisfies the new TECHSPEC invariants.
