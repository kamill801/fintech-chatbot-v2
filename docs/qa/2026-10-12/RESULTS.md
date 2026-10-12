# Task 8.4 service verification

2026-10-12 Asia/Seoul. Baseline e9dbdcd. Native Codex Goal tracks continuation; the matrix below establishes finite evidence.

## Preservation

All current features/routes, providers, deterministic money calculations, ownership, encryption and audit history remain. No new dependency, remote font, auth scope, credential, schema, TECHSPEC amendment or infrastructure. Original production records are retained. Demo rendering is not actual AI or persistence; the new banner identifies examples. Destruction/conflict/failure tests use isolated storage.

## Scenario matrix

| Flow | Fresh evidence and boundaries |
| --- | --- |
| Authentication | 4 LoginPage, 7 auth-context, 2 kakao-login and 8 App tests: entry/callback errors/session/logout/owner-separated drafts. Authenticated live smoke follows release |
| Onboarding | App/HomeFlow tests cover intro once, blank/zero/large money, budget→goal→source, guard/back/storage recovery. Existing production profile was not purged to force onboarding |
| Home/navigation | Browser all nav/profile/recent views; direct-link back + malformed route regressions; period-state tests |
| Record | Browser synthetic expense, income 3,500,000 and transfer 50,000: date/calendar return and transfer excluded from expense total. MainPages/API/E2E tests cover failure/draft/idempotency/exclusion |
| Ledger | Browser month/date/list/search/type filters/detail; MainPages tests also category/account filtering |
| Judgment | Browser Korean demo reason/result and correction cancel; isolated backend reason/skip/correction/history/share/privacy contracts. Demo advice is illustrative |
| Reflection/edit | Browser 12,000→12,500 remains 12,500 after save; ambiguous rating/note saved. 5 JudgmentFlow tests + archived-account API regression. Deletion/failure only isolated storage |
| Plan | Browser same-period preview/apply: actual 377,500, reservation 100,000, flexible 322,500. 8 PlanPage + 11 context tests; backend preview-token, stale/conflict, check-in/matching/period calculation coverage |
| Report | Browser 320px current-month totals/categories/reflection/goal; MainPages tests prior-month comparison. Historical report month selector was not an existing feature and is not claimed; ledger month navigation remains |
| Settings | Browser budget/goal/accounts/category-budget/rules/mode/privacy dialogs; goal save→settings→back returns home. 3 ProfileSettings tests. CSV UI reports export count/success, browser download artifact not captured |
| Responsive/a11y | 8 routes×320/390/414/1440: document width equals viewport, input fonts≥16px. 1,000,000,000 goal visible at 320 after stacked fields. Dialog focus/Escape/busy/opener regressions. Safe-area CSS retained |
| Reliability/privacy | 162 backend tests with isolated Redis, no skips: unauthorized/cross-owner/encryption/idempotency/concurrency/AI allowlist/fallback. 11 API tests include offline/hung fetch/hung response-body cleanup |
| Final source | 101 frontend tests/16 files, lint, TypeScript/Vite build; backend 162; Python compile and diff check passed. Final independent review APPROVE, zero blockers |
| Release | Pending at source commit time. Same-SHA Vercel/Render and authenticated evidence are recorded in external RELEASE.md below |
| Reusable skill | service-qa-release forward test passed; all four bundles hash-match/validate. Codex/.agents/Mac/Wiki saves complete; Wiki index/doctor bookkeeping passed, no issues or external calls |

## Reproductions and repairs

1. Ended plans offered a current-week maintain action: period-aware labels and next-period flow now preserve the existing revision API and reviewed-token contract.
2. Direct-linked Back could leave the app: app history index now falls back to home at index zero, preserving demo context.
3. A saved budget/goal form reappeared on Back: successful save uses replace navigation.
4. Older detail reads overwrote successful edits: canonical mutation results update detail; stale reads cannot overwrite them.
5. Existing archived-account transactions could not be corrected: only the record's previous archived account can be retained, while new/switch-to-archived assignments remain rejected.
6. Hung response bodies outlived fetch timeout: one abort deadline now covers fetch and body read with Korean recovery; mutations are not automatically retried.
7. Fonts named unloaded families, tiny controls and squeezed large-money fields: explicit system stack, 44px controls, readable native fields, stacked forms, contained dialogs and bottom clearances.
8. Demo revision reset actual spend and wrong-period records changed balance: Korean calendar dates and in-period deltas preserve arithmetic; examples remain explicitly identified.

Detailed repros are in adjacent findings files. No discovered required defect remains after integrated checks and independent review. This is bounded verification, not a universal bug-free claim.

## Fresh validation

- Isolated local Redis 127.0.0.1:6389/15, persistence disabled. Full backend: 162 tests, 9.903s, OK, no skips.
- Frontend: 16 files, 101 tests; lint and tsc/Vite build passed. Local bundles index-Bi6BP2DT.js and index-DJFe0hP0.css.
- Python compileall, git diff --check passed; final staged checks precede commit.
- Independent review APPROVE. Reviewer lacked literal LSP/AST tools and substituted build/lint/tests/compile/diff/scoped scans. Root full Redis run covers the reviewer's four skips.
- Responsive measurements: `/Users/dd/.codex/visualizations/2026/09/13/01a09a1a-720c-7b51-bce2-8bb9d40591bf/jangbu-full-qa-2026-10-12/responsive-matrix.json`.
- Skill: Codex bundle, .agents mirror, Mac standalone/bundle/catalog/manifest, Wiki immutable source/operating bundle/source page/catalog/index/log complete. All bundles validate. Wiki bookkeeping_passed=true, issues=[], external_calls=0; human meaning approval was not inferred.

## Release and limitations

No Task 8.4 deployment is claimed in this source artifact. The one final source commit is followed by release verification in `/Users/dd/.codex/visualizations/2026/09/13/01a09a1a-720c-7b51-bce2-8bb9d40591bf/jangbu-full-qa-2026-10-12/RELEASE.md` (full SHA, existing provider IDs, readiness, authenticated read/write/reload/session).

Physical iPhone/Safari/WKWebView keyboard, safe areas and Kakao return were not directly observed this turn; Chrome sizing is separate. Local Python is 3.14; Render retains Python 3.11.6, so hosted readiness and authenticated smoke remain required. No original record or production account was deleted for QA.
