# Plan reliability findings — 2026-10-12

## Scope

- Reviewed and changed `frontend/src/pages/PlanPage.tsx` and `frontend/src/pages/PlanPage.test.tsx` only for plan-period behavior.
- Backend plan/domain files were not changed because the reproduced issue was copy/action state for an already ended plan, not a calculation or persistence defect.
- Shared CSS/router work is owned by root. I did not make additional router/shared edits after the lane conflict was identified.

## Reproduced issue

Production/browser evidence from root showed an Oct 5–11 plan viewed on Oct 12. The app correctly marked the user as outside the plan period, but the check-in still asked whether to keep “this week’s” plan and offered a maintain action. That made a completed plan look actionable for the current week.

## Fix made

- Completed plan now reads as historical state:
  - Header label: `완료된 계획 · v{version}`
  - Period metric: `종료됨`
  - Check-in title: `이 기간 계획은 마무리됐어요`
  - Maintain check-in button is removed for completed periods.
- Completed plan now offers a forward action:
  - `다음 기간 계획 세우기` opens a new 7-day draft starting the day after the ended plan.
  - Priorities and the latest discretionary budget are carried into the draft; planned expenses start empty for the new period.
- Upcoming plan copy is also period-aware:
  - Header label: `시작 전 계획`
  - Maintain action is disabled before the plan starts.
  - Secondary action changes to `시작 전 수정`.
- Active plans keep the existing maintain/adjust behavior, with the copy changed from weekly wording to plan-period wording.

## Validation

- `cd frontend && npm run test -- PlanPage.test.tsx` → 8 tests passed.
- Added regression: completed plans are treated as history and the next-period draft opens with the expected dates.
- Earlier targeted backend plan/API verification remained green before this doc update: `python3 -m pytest tests/integration/test_spending_plan.py tests/integration/test_plan_reliability.py tests/e2e/test_flask_api.py` → 53 passed.
- Local browser accessibility output on `http://127.0.0.1:4174/plan?demo=1` showed the active demo plan using period-aware active copy: `진행 중인 계획 · v1`, `현재 구간`, and `이번 계획을 유지할까요?`.

## Remaining owner boundary

- Full frontend test/build status depends on concurrent root-owned router and shared CSS changes. I did not claim final full-suite status from this lane after the router ownership conflict.

## Follow-up polish — next-period intent

- Completed-plan CTA now starts a next-period flow instead of showing revision-mode UI.
- The next-period flow uses setup copy (`다음 기간에 쓸 돈을 정해요`) and hides the revision reason field.
- Backend contract still requires revision endpoints whenever an existing plan is present: `preview_spending_plan` and `activate_spending_plan` reject creation if any active/current plan exists.
- Because of that contract, next-period flow now calls `previewPlanRevision` and `applyPlanRevision` with the default reason `다음 기간 계획 시작`, but the review screen hides before/after revision copy and displays the revision `after` values as the next-period preview.
- Regression covers clicking the completed-plan CTA, reviewing the full draft, confirming revision endpoints are used, and confirming create/activate endpoints are not called.

## Follow-up validation

- `cd frontend && npm run test -- PlanPage.test.tsx ledger-context.test.tsx` → 19 tests passed.
- `cd frontend && npm run test` → 16 files, 101 tests passed.
- `cd frontend && npm run lint` → passed.
- `cd frontend && npm run build` → passed.
