# 장부 AI — 전체 서비스 3회 / 할머니 말투 3회 검증

- Run: `jangbu-qa-2026-10-30-01`; owner: native Codex coordinator.
- Baseline: `ed2cadda4cff981f5c63705b575f86e725b18ebb`; source: TECHSPEC.md and DESIGN.md.
- Claim: checked feature journeys and demonstrated repairs, not universal absence of defects or proven virality.
- Limits: service passes 1–3 followed by persona passes 4–6 (three batches). Each pass advances inspect → frozen fix batch → verify; new failures go to the next available pass. No seventh automatic cycle.
- Model budget: up to 36 actual provider attempts total (including retry/failure), through the existing configured application provider only. Up to 18 attempts reserved for three persona batches of three synthetic cases; remaining attempts for functional model paths. User explicitly requested actual service and persona testing; no new paid connection, purchase or key provisioning. Actual cost is unknown until usage is returned, never assumed zero.
- Environments: isolated local API/storage and browser for side effects; current production read-only compatibility where available. Existing authenticated sessions may be inspected. No production record deletion or replacement. No invented provider proof from demo/fallback.
- Release authority: continuing prior same-thread request to repair, commit, push and deploy to existing Vercel `upglow/jangbu-ai` and Render `jangbu-api`; release only after required gates clear. At most two separately recorded read-only deployed checks.
- Visual baseline: warm paper backgrounds, blue primary actions, peach emphasis, system font, Phosphor icons, existing navigation and components. Check 320/390/414/1440 CSS pixels, 44px targets, input font >=16px, no overflow/overlap, keyboard and focus recovery.
- Frozen persona rubric: `PERSONA-RUBRIC.md` must be saved before evaluating improved output. All money, judgments, confidence, factors and recommended actions stay invariant across voices. Necessary/justified spending must not be condemned for humor.

## Required retained-feature and scenario matrix

Each row requires current evidence. Automated fixtures, real local UI, live-provider output, production readback and physical-device proof are separate evidence levels. Unknown/blocked rows stay visible.

| ID | Retained feature / journey | Required checks | Initial state |
|---|---|---|---|
| A | Kakao/email login, session, ownership | restore, invalid/expired auth, logout; no data cross-user | Unknown |
| B | First-login onboarding, baseline and goal | empty/zero/invalid fields, save → goal → home, revisit | Unknown |
| C | Home, navigation, pending question | current budget/goal/records, profile corner, mode off/on | Unknown |
| D | Expense, income, transfer | create → result → calendar date → reload; balances/budget invariant | Unknown |
| E | Ledger calendar/list/search/detail | select date/month, filter/search, edit, isolated delete, reflected totals | Unknown |
| F | Reason/judgment/correction/reflection/share | one reason in grandma mode, skip, normal uninterrupted, audit preserved, private share | Unknown |
| G | Spending plan | draft → preview → confirm → revisit, revisions, reservations/matches, check-in | Unknown |
| H | Reports and AI coach | period/category/regret arithmetic, advice freshness, Korean text and provenance | Unknown |
| I | Settings | accounts/archive, budgets, goal/profile, spending rules, mode persistence | Unknown |
| J | Privacy/data controls | CSV, deletion/revocation with isolated fixtures only, no sensitive export to AI/share | Unknown |
| K | Recovery and accessibility | failed/slow response, no duplicates/lost draft, back/refresh, empty/error/loading | Unknown |
| L | Responsive design | required widths and shared screens, focus, readability, touch/safe areas | Unknown |
| M | Persona semantics | three distinct evaluation batches; frozen support/voice/parity criteria | Unknown |

Physical iPhone and Kakao webhook delivery remain explicit integration rows even if unavailable. No device claim from browser emulation; no actual third-party delivery claim from local adapter tests.

## User-directed environment correction (before production mutations)

The user declined key creation and explicitly authorized testing the existing Vercel production service on 2026-10-30. The local401 describes the local.env connection only and is not evidence about the deployed provider. No new key/account/connection is to be created. Production synthetic examples entered through the existing authenticated UI are now authorized; original records/profile are retained, test entries use a QA marker, and no production record deletion occurs. This overrides the initial production-read-only boundary only for those examples. Existing pass/provider counters remain unchanged. Browser currently requires the user to sign in; never request passwords/tokens in chat. Original fixed-signal nine-case rubric remains retained; deployed cases must record the actual current financial context rather than pretend they received those synthetic ratios.
