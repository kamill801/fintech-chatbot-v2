# Development Plan - AI Household Ledger Agent

## Current State

- Phase: 5 - Vercel frontend production deployment complete
- Active task: none; Task 5.0 is complete and production frontend verified
- Approval: 2026-08-01 user-approved replacement of the legacy product, TECHSPEC, PLAN, and backend
- UI/UX approval: 2026-08-03 user-approved domestic-ledger benchmarking and joint design start
- Branch: `codex/ui-ux-foundation`
- Sources of truth: `TECHSPEC.md` for product/backend invariants, `DESIGN.md` for UI/UX decisions
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

## Task 3.0 - Benchmark-led UI/UX Foundation (Completed)

### Goal

Define the mobile-first household-ledger information architecture and a distinct visual direction before frontend implementation. Preserve familiar Korean ledger behavior while making the AI agent's pending questions, evidence, and advice visible without turning the product into a chat-first novelty.

### Scope

- Research current official materials for established Korean finance and household-ledger products.
- Translate the supplied warm-paper Notion references into a finance-appropriate visual system.
- Define onboarding, home, ledger, manual entry, agent, judgment, reports, goals, settings, and sharing flows.
- Define Normal/Roast mode interaction and content-safety rules without changing judgment logic.
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
- Roast is visibly opt-in, instantly reversible, and presentation-only.
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
- Normal judgment
- Roast judgment
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
- Normal and Roast judgment screens share all financial facts and differ only in rendered message and mode state.
- Manual entry is live; account connection remains explicitly future/read-only.
- Generated Korean copy is readable enough to guide implementation; any image-generation artifacts are documented rather than copied into code.
- No frontend code is implemented in this task.

## Task 4.0 - Complete Responsive Web/PWA Implementation (Completed)

### Goal

Implement the user-approved 15-screen visual set as a complete mobile-first web app and installable PWA. Connect the live UI to the existing Flask ledger API while preserving backend ownership of financial judgment, confidence, evidence, recommendation, and Normal/Roast parity.

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
- [x] Implement onboarding, Home, manual capture, reason, and Normal/Roast judgment flows.
- [x] Implement ledger, transaction detail/correction, agent inbox, report, settings, and privacy-safe sharing.
- [x] Add Flask production static serving and focused backend/frontend tests.
- [x] Run typecheck, lint, unit tests, production build, Flask tests, and real local API flow checks.
- [x] Capture the 15 approved states at 390x844, compare against references, and iterate on material visual differences.
- [x] Verify 360px, 390px, 430px, tablet, desktop, keyboard focus, reduced motion, and offline draft behavior.
- [x] Update `README.md`, this plan, append `progress.txt`, and create one scoped local commit.

### Acceptance Criteria

- All 15 approved screen contracts exist as reachable responsive routes or states and every primary action is interactive.
- The 390x844 implementation preserves the approved warm-paper palette, bold editorial hierarchy, flat fills, amount emphasis, and mobile navigation.
- Live labels, confidence, evidence, recommendation, and Normal/Roast messages come from the backend judgment artifact.
- Roast remains opt-in, immediately reversible, and presentation-only.
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

## Archived Work

Phase 1 migrated the old Kakao persona chatbot to the Responses API and added prompt/validator mechanics. Those commits remain in Git history, but their product plan is superseded by the 2026-08-01 pivot. Reuse is allowed only where it satisfies the new TECHSPEC invariants.
