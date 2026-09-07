# TrackMyExpense Competitive Review

Reviewed: 2026-09-02

## Evidence boundary

This review compares current official product claims with repository-verified Jangbu behavior. It does not treat store copy, ratings, privacy declarations, security language, subscriber counts, or revenue as independently audited facts.

Primary sources:

- [Google Play listing](https://play.google.com/store/apps/details?id=com.pankaj.TrackMyExpense&hl=en)
- [TrackMyExpense product and pricing site](https://trackmyexpense.app/)
- [TrackMyExpense privacy policy linked from Google Play](https://gist.github.com/pankajrathi95/1437d5394b8542a6b9d5adb835967844)
- Jangbu `TECHSPEC.md`, implemented frontend/backend, tests, and `DESIGN.md`

Google Play currently shows `1K+` downloads. Public stores do not expose paid-member or revenue totals, so TrackMyExpense is a relevant direct feature competitor, not evidence of category-leading scale.

## Positioning

| Product | Current promise | Primary value |
| --- | --- | --- |
| TrackMyExpense | Capture every expense before the user forgets it | Low-friction, broad-feature expense tracking with an AI query layer |
| Jangbu | Reduce spending the user later regrets | Korean household ledger plus evidence-backed behavior coaching |

TrackMyExpense is capture-first. Jangbu is behavior-change-first. They overlap in manual ledger, reports, budgets, and AI guidance, but their strongest product loops are different.

## Detailed comparison

| Area | TrackMyExpense official claim | Jangbu current verified state | Current advantage |
| --- | --- | --- | --- |
| Platforms | Native Android and iOS | Responsive installable web/PWA | TrackMyExpense |
| Sign-in | Google and Apple | Email/password deployed; Kakao OAuth locally implemented and awaiting provider activation | TrackMyExpense until Kakao E2E is live |
| Manual entry | Quick type and calculator-enabled amount entry | Amount-first entry for expense, income, and transfer; recent transactions can prefill fields | Rough parity, TrackMyExpense has the calculator edge |
| Voice entry | Voice capture | Not implemented | TrackMyExpense |
| Receipt capture | OCR from receipt photos | Not implemented | TrackMyExpense |
| Repeating money | Recurring expenses and income | Not implemented | TrackMyExpense |
| Offline use | Offline-first with later sync | Network-backed PWA with user-scoped local drafts, not a durable offline ledger queue | TrackMyExpense |
| Accounts | Multiple separate personal, business, and family spaces | Manual accounts and transfer-aware balances in one personal ledger | Depends: Jangbu is sufficient for personal use, TrackMyExpense is broader |
| Currency/language | 150+ currencies and 21 languages | Korean-first KRW product | TrackMyExpense for global breadth; Jangbu for Korean focus |
| Calendar/list | Reports and transaction history; store copy does not establish a calendar-first Korean ledger flow | Sunday-start monthly calendar, daily totals, selected-date records, searchable/filterable list | Jangbu for Korean ledger navigation |
| Transaction model | Expense and optional income modes | Expense, income, and transfer with transfer excluded from spend/income/AI totals | Jangbu |
| Editing | Expense management is claimed | Create, update, delete, retry idempotency, judgment history preservation | Jangbu has stronger auditable behavior |
| Budgets | Per-account monthly budget progress | Monthly living budget, category budgets, daily spendable amount, remaining budget | Jangbu |
| Reports | Monthly/custom-range category, payment-mode, and time analysis | Monthly summary, category bars, prior-month comparison, reflection summary, goal forecast | TrackMyExpense for date-range breadth; Jangbu for behavior/goal meaning |
| Export | PDF, Excel, and CSV | Local privacy-safe CSV | TrackMyExpense |
| Backup | Encrypted cloud sync and automatic backup are claimed | Redis-backed authenticated persistence and deletion/revocation controls | No independent winner without provider E2E/security audit |
| AI questions | Natural-language questions about recorded data | Structured judgment, weekly briefing, regret patterns, and deterministic summaries; not an open-ended ledger chat | TrackMyExpense for query breadth |
| Prediction | Three-month forecast from up to twelve months of history | Deterministic goal-delay calculation and trend comparison; no speculative forecast model | TrackMyExpense for forecast feature; Jangbu for inspectability |
| Overspending judgment | General AI assistant and prediction | Deterministic signals, confidence, evidence, correction, and same decision across voice modes | Jangbu |
| Personal learning | General history-based analysis is claimed | `잘 쓴 돈/애매함/후회함`, optional reflection, editable personal rules, regret-pattern aggregation | Jangbu |
| Behavior change | Insights and reminders | One measurable seven-day action, next-week result loop, goal-date impact | Jangbu |
| Character/virality | Conventional assistant | Opt-in 욕쟁이 할머니 voice and privacy-safe share card | Jangbu |
| Monetization | Paid Pro; current site lists weekly, monthly, and annual plans with no permanent freemium | No paid plan implemented | TrackMyExpense has a clearer business model; Jangbu has lower adoption friction today |

## Cold verdict

### Better household ledger today: TrackMyExpense

For a user who wants to capture daily transactions reliably with the fewest gaps, TrackMyExpense is ahead. Voice, receipt OCR, recurring entries, offline-first behavior, multi-platform native apps, custom-range reports, and PDF/Excel export cover more real-world bookkeeping situations.

### Better differentiated coaching model: Jangbu

For a user whose main goal is reducing later-regretted spending, Jangbu has the stronger product model. It does not only label categories or predict totals. It stores the user's own post-purchase judgment, learns explicit spending rules, explains deterministic evidence, permits judgment correction, converts spending into goal-delay days, and closes the loop with one next-week action.

### Overall current consumer utility: TrackMyExpense leads

Jangbu's differentiation is meaningful only if users keep recording data. Its present capture gaps create the largest strategic risk: incomplete data weakens every downstream judgment, briefing, and learned regret pattern. Until capture reliability approaches parity, TrackMyExpense remains the stronger general-purpose expense product.

## Privacy and trust comparison

TrackMyExpense's Google Play declaration says data is encrypted in transit and may include personal information, while its linked privacy policy describes possible sharing with hosting, analytics, legal, and business-transfer service providers. These are provider declarations, not an external security audit.

Jangbu's repository contract can be verified locally: Supabase bearer tokens protect production routes; direct identifiers become HMAC pseudonyms; Redis projections are encrypted; OpenAI receives an explicit allowlist with bounded calls; reflections are excluded from telemetry and shares; CSV export is local; deletion and revocation controls exist. This still does not prove production Kakao callback behavior, provider dashboard state, or an external security audit.

## Recommended improvement order

### P0 - Complete current authentication task

1. Activate Kakao Login in Kakao Developers and Supabase.
2. Verify consent, callback, new-user onboarding, returning-user persistence, sign-out, and email fallback in production.
3. Keep Kakao nickname/profile image display-only and avoid account auto-merging in the MVP.

### P1 - Close the data-capture gap

1. Recurring transactions and scheduled-payment reminders.
2. One low-friction capture channel: voice quick-add first for PWA reach, then receipt OCR with editable review.
3. Durable offline queue and conflict-safe sync rather than local form drafts only.

These improve both ledger parity and AI quality because they increase data completeness.

### P2 - Mature reporting without diluting the product

1. Custom date ranges and saved filters.
2. PDF and spreadsheet export in addition to CSV.
3. Grounded natural-language ledger questions over deterministic aggregates. Code must calculate totals; the model may select, summarize, and explain evidence but must not invent arithmetic.
4. Completeness reminders for missing recurring records and uncategorized transactions.

### Later provider/platform work

- Read-only Korean MyData or bank linkage after a separate provider, consent, retention, and compliance design.
- Native widgets or share extension after the web capture loop proves retention.
- SMS/notification parsing only with explicit permission, review, and correction UX.

## What not to copy now

- `150+` currencies and broad localization: they add surface area without strengthening the Korea-first wedge.
- Personal/business/family workspaces: separate jobs and permissions should not enter the personal MVP accidentally.
- Opaque AI expense prediction: forecast quality is difficult to inspect and is less defensible than regret feedback plus deterministic goal impact.
- An open-ended AI chat before transaction completeness: broad questions cannot compensate for missing ledger data.

## Product direction

The durable wedge remains:

> 다른 가계부가 어디에 썼는지 보여준다면, 장부는 다음 주에 무엇을 바꿀지 알려준다.

The roadmap should therefore reach capture parity without turning into a generic global expense tracker. Every parity feature should strengthen the same loop:

`빠른 기록 -> 사용자의 사후 평가 -> 개인 기준 학습 -> 한 가지 행동 -> 실제 후회 소비 감소 측정`
