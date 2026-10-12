# Scenario Matrix

Create the matrix before broad fixes so every later claim has a target. Keep it specific to the current product and remove rows that do not exist in the service.

## Suggested Columns

| Area | Scenario | User Data | Expected Result | Evidence | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Auth/session | Existing user returns after refresh | Existing account | Session restores without repeating first-run setup | Test or browser note | Unknown |  |
| Onboarding/setup | New user completes required setup | Fresh or demo user | Saved profile leads to first usable screen | Test or browser note | Unknown |  |
| Core create flow | User creates the primary record | Valid required fields | Record persists and appears in the canonical list/calendar/dashboard | Test or browser note | Unknown |  |
| Core edit/delete | User corrects or removes a record | Existing record | Derived totals and detail views update consistently | Test or browser note | Unknown |  |
| AI/provider path | AI or external provider is slow/unavailable | Stubbed or live failure | User sees bounded fallback/retry behavior and no false success | Test or browser note | Unknown |  |
| Reports/insights | User views summary after new data | Existing records | Numbers match deterministic source data | Test or browser note | Unknown |  |
| Settings/preferences | User changes a persisted preference | Existing user | Preference survives refresh and does not affect unrelated data | Test or browser note | Unknown |  |
| Responsive UI | Key screens at mobile, tablet, desktop | Representative data | No horizontal overflow, hidden primary controls, or overlapping text | Screenshot or measurement | Unknown |  |
| Error recovery | Network/storage error during save | Stubbed failure | Draft is preserved or loss is clearly prevented | Test or browser note | Unknown |  |

## Status Terms

- `Passed`: verified in this run with linked evidence.
- `Failed`: reproduced defect remains.
- `Fixed`: defect was reproduced, changed, and reverified.
- `Blocked`: cannot verify without missing authority, credentials, provider state, or user-owned device action.
- `Out of scope`: not part of the current product or explicit task.
- `Unknown`: not yet checked; do not treat as passed.

## Coverage Notes

Preserve an existing product-specific matrix if one exists. Add only rows that help prove user-facing behavior or important contracts. Do not count screenshots of static pages as persistence, authorization, or provider evidence unless the underlying action was exercised.
