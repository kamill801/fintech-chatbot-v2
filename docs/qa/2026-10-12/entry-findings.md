# Entry, Ledger, Judgment Flow Findings

Scope: `HomeFlow.tsx`, `MainPages.tsx`, `JudgmentFlow.tsx`, and focused tests for Task 8.4.

## Checked

- Manual transaction drafts, idempotent retry, double-tap guard, normal-mode ledger return, grandma-mode reason gate, income save, and selected-date prefill.
- Ledger calendar/list navigation, saved transaction deep link, search and type/category/account filtering, report empty state, and settings mode preview.
- Judgment headline, reflection save, correction-aware share preview, and share success recording.

## Fixed

- Transaction detail editing now opens the date input with the Korean ledger date via `transactionDateKey()` instead of slicing the UTC ISO timestamp. This prevents late-night UTC timestamps from opening one day earlier than the date shown in the ledger.
- Added a regression that confirms the edited transaction payload preserves the Korean date and saves the changed amount.
- Added a regression that the weekly concern card renders a single category icon, preventing compact cards from being pushed by duplicate icon content.

## Gaps For Root Browser QA

- Real authenticated browser path should still confirm `add -> save -> ledger saved row -> detail -> edit -> save -> detail reload` against the shared provider.
- Mobile viewport QA should confirm no horizontal overflow in the transaction edit dialog and settings account/category budget dialogs at 320, 390, and 414px.
- Shared router ownership issue found outside this lane: `npm run test -- --run src/router.test.tsx` currently fails 3/5. Two failures leave multiple `뒤로` buttons or call `history.go(-1)` on a direct entry, and one real route-matching defect throws `URIError: URI malformed` for `/transactions/%E0%A4%A` at `router.tsx:145`.

## Transaction detail canonical mutation response

Browser QA reproduced a demo/local race where saving a transaction edit from the detail screen closed the modal, but the visible detail could stay on the old amount/category because an older `getTransaction()` reload resolved after the mutation response. `TransactionDetailPage` now applies `updateTransaction()` and `reflectTransaction()` responses as the canonical detail state and ignores stale reloads through a local revision guard. The regression in `JudgmentFlow.test.tsx` keeps `getTransaction()` stale and verifies the saved amount, merchant, and category remain visible after the modal closes.
