# Demo plan preview findings — 2026-10-12

## Confirmed defect

- In demo mode, an unchanged Aug 1–31 plan revision preview showed remaining living money changing from `322,500원` to `700,000원`.
- Root cause: the demo preview helper rebuilt plan progress from the new draft budget and reserved expense only. It did not carry forward the current plan's `actual_spent_krw`, so the already-recorded `377,500원` disappeared from the revision preview and apply result.

## Fix

- `frontend/src/ledger-context.tsx` now distinguishes same-period revisions from changed-period revisions in demo mode.
- Same-period demo revisions preserve the current plan's actual spending while recomputing remaining money from the reviewed draft budget and still-unmatched planned expenses.
- Existing planned expense matches are preserved when the planned expense id is still present in the draft.
- Changed-period demo revisions compute actual spending from the available demo transaction list for the selected date range, rather than inventing missing records from summary totals.
- Demo apply now builds the reviewed revision once, increments the plan version, keeps the original plan snapshot, and stores the reviewed progress instead of resetting back to the setup preview shape.

## Demo limitation documented

- The demo fixture is intentionally synthetic and incomplete: `demoSummary` says August has 14 transactions and `377,500원` in spending, while the exported `demoTransactions` list contains only the visible sample rows.
- Because of that mismatch, same-period plan revisions preserve the existing plan progress snapshot, while changed-period previews use only available demo transactions.
- The demo transaction flow still does not fully persist/recompute every monthly summary invariant after arbitrary manual edits. That should be treated as a separate demo-state consistency task if product wants demo mode to behave like a full local database.

## Validation

- `cd frontend && npm run test -- ledger-context.test.tsx` → 8 tests passed.
- `cd frontend && npm run test` → 16 files, 97 tests passed.
- `cd frontend && npm run lint` → passed.
- `cd frontend && npm run build` → passed.

## Follow-up fix — demo date and plan deltas

- Demo transaction dates now use the Korean calendar day, so `2026-08-31T15:30:00Z` is treated as `2026-09-01` for period matching.
- Creating a demo expense outside the active plan period no longer subtracts from the active Aug 1–31 plan balance.
- In-period demo transaction edits and deletes now apply only the old/new in-period amount delta to plan progress.
- The baseline legacy demo plan progress remains preserved at `377,500원` actual spending and `322,500원` flexible remaining unless an in-period delta is applied.

## Follow-up validation

- `cd frontend && npm run test -- PlanPage.test.tsx ledger-context.test.tsx` → 19 tests passed.
- `cd frontend && npm run test` → 16 files, 101 tests passed.
- `cd frontend && npm run lint` → passed.
- `cd frontend && npm run build` → passed.
