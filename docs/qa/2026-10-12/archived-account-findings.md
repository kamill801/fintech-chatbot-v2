# Archived account transaction update findings

## Scope

Task 8.4 backend follow-up for historical transactions that reference accounts later hidden or archived in Settings.

## Confirmed issue

`LedgerService.update_transaction()` reused `_validate_transaction_accounts()` with the same active-account-only rule used for new transaction creation. After a user hid an account, existing transactions still stored that account ID, but a simple edit such as changing the amount was rejected with `invalid_account` because the preserved account was archived.

This broke the intended frontend behavior where historical records can still display and preserve their original account while hidden accounts are unavailable for new assignments.

## Fixed behavior

- New transactions still require active, non-archived account IDs.
- Updating an existing transaction may preserve its previous source account ID when that account still exists in settings, even if archived.
- Updating an existing transfer may preserve its previous destination account ID when that account still exists in settings, even if archived.
- Updating a transaction cannot switch to a different archived account.
- Updating a transaction cannot reuse a previous account ID after that account has been removed from settings.
- Cross-role switching is not allowed: an archived previous destination does not become a valid new source account, and an archived previous source does not become a valid destination account.

## Regression evidence

Added `FlaskLedgerE2ETests.test_archived_transaction_accounts_can_only_be_preserved_on_update` to cover:

1. Create expense on active `cash`, archive `cash`, update amount while preserving source `cash`.
2. Create transfer from active `bank` to active `cash`, archive `cash`, update amount while preserving destination `cash`.
3. Attempt a new expense against archived `cash`, rejected with `invalid_account`.
4. Attempt to switch an existing `bank` expense to archived `cash`, rejected with `invalid_account`.

Before the service fix, the first preserved-source update returned HTTP 400 instead of 200.
