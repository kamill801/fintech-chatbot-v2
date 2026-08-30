# Household Ledger Benchmark - 2026-08-30

## Method and evidence limit

App stores do not publish verified paid-subscriber counts for these products. This benchmark therefore uses public proxies: Android install bands, review volume, App Store paid chart placement, paid purchase price, subscriptions/in-app purchases, and official feature descriptions. It does not claim a private subscriber ranking.

Official sources:

- [Money Manager / 편한가계부 - App Store Korea](https://apps.apple.com/kr/app/%ED%8E%B8%ED%95%9C%EA%B0%80%EA%B3%84%EB%B6%80/id560481810)
- [Money Manager - Google Play](https://play.google.com/store/apps/details?id=com.realbyteapps.moneymanagerfree)
- [위플 가계부 Pro - App Store Korea](https://apps.apple.com/kr/app/%EC%9C%84%ED%94%8C-%EA%B0%80%EA%B3%84%EB%B6%80-pro/id441683476)
- [Wallet by BudgetBakers - Google Play](https://play.google.com/store/apps/details?id=com.droid4you.application.wallet)
- [Monefy - Google Play](https://play.google.com/store/apps/details?id=com.monefy.app.lite)
- [뱅크샐러드 가계부 도움말](https://help.banksalad.com/2d2116e2-39f6-800b-84d4-cd26a7ba7dc4)
- [토스 - App Store Korea](https://apps.apple.com/kr/app/%ED%86%A0%EC%8A%A4/id839333328)

Observed public scale on the research date:

| Product | Public adoption/paid proxy | Product emphasis |
| --- | --- | --- |
| 편한가계부 | Google Play 10M+ installs and roughly 460K reviews; App Store roughly 86K ratings; subscription/IAP | Deep manual ledger, account/card, recurring, search, backup/export |
| 위플 가계부 Pro | Paid iOS app, Finance paid chart leader in observed listing, roughly 8.7K ratings | Fast one-screen input, calendar, budget, report |
| Wallet | Google Play 10M+ installs, roughly 384K reviews, Editors' Choice, IAP | Bank sync, budgets/goals, planned bills, sharing, multi-account reports |
| Monefy | Google Play 10M+ installs, roughly 194K reviews, Editors' Choice, IAP | Amount-first one-click entry, simple chart, recurring, account and budget support |
| 토스 | Large Korean finance super-app; App Store listing emphasizes integrated assets and spending | Automatic aggregation, card/consumption/subscription overview |
| 뱅크샐러드 | Established Korean asset-management product | Automatic classification, correction learning, category budgets, daily recommended allowance |

## Detailed capability comparison

Legend: `yes` supported, `partial` limited, `deferred` requires native/provider work, `no` absent before Task 7.0.

| Capability | Market baseline | Jangbu before 7.0 | Task 7.0 decision |
| --- | --- | --- | --- |
| Amount-first fast input | Core in Weple and Monefy | yes | keep, add recent quick-entry suggestions |
| Expense/income/transfer | Core in full ledgers | no, expense only | implement all three |
| Cash/bank/card accounts | Core in Money Manager/Wallet | no | implement manual accounts/payment sources |
| Monthly calendar | Core in Korean ledgers | yes | keep as default |
| Chronological list | Core in all comparators | no | implement view toggle |
| Search and filters | Expected in mature ledgers | no | implement merchant/memo/category search and filters |
| Transaction edit/delete | Expected table stakes | no | implement with audit events |
| Category budgets | Core in Banksalad/Wallet/Money Manager | profile-wide budget only | implement per-category budgets and daily allowance |
| Previous-period comparison | Common report feature | no | implement previous-month deltas |
| Recurring/planned bills | Strong convenience feature | no | defer background scheduling; preserve as next parity task |
| Backup/export | Common trust feature | full account deletion only | implement browser CSV export; server restore deferred |
| Bank/MyData sync | Major Toss/Wallet advantage | provider port only | deferred until provider/compliance approval |
| SMS parsing / receipt OCR | Native convenience feature | no | deferred because web/PWA cannot provide reliable parity |
| Widgets | Native quick-entry feature | no | deferred to a native shell |
| Household sharing | Wallet advantage | no | defer until roles/consent model is designed |
| AI spending coach | Weak or generic in many ledgers | strong | keep separate from ledger arithmetic |
| Personal regret learning | Differentiated | yes | keep expense-only |

## Cold assessment

Before Task 7.0, Jangbu was a useful AI expense coach but not a complete household ledger. Calendar entry, transaction detail, monthly category reporting, goals, and AI briefings were credible. However, expense-only records meant income shown in the UI came from the onboarding profile rather than actual ledger entries, transfers could not be represented, there was no account model, and users could not search, edit, delete, or export individual records. On ledger fundamentals it was materially behind the named products.

The target for Task 7.0 is not feature-count parity with native apps. It is a trustworthy web ledger baseline: every manually entered KRW movement is representable, totals cannot be distorted by transfers, records are maintainable and findable, budgets are actionable, and users can take their data out. Native/provider advantages remain explicitly deferred rather than represented by dead controls.

## UX principles adopted

1. Keep amount-first entry and expose transaction kind before secondary details.
2. Default to the calendar but never trap power users there; list/search/filter is one tap away.
3. Show actual recorded income, expense, and net cash flow. Never substitute profile income for ledger income.
4. Treat transfer as movement between accounts, not spending.
5. Put remaining budget and daily allowance near the category decision, not only in a month-end report.
6. Reuse recent entries for speed instead of asking users to configure templates before value exists.
7. Keep AI out of arithmetic. AI explains patterns after deterministic ledger calculations are complete.
