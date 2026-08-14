# Design

## Source of truth

- Status: Implemented - post-deployment correction release approved
- Last refreshed: 2026-08-05
- Product name: undecided; screen copy uses `내 장부` as a neutral working label
- Primary product surfaces: mobile app first, responsive web second, Kakao transport retained as a thin secondary surface
- Product contract: `TECHSPEC.md`
- Execution queue: `PLAN.md`
- Evidence reviewed:
  - User-provided Notion screenshots: bold editorial headline, inline peach pill, warm white canvas, sparse hand-drawn accents, flat modular feature panels
  - User-provided style note: "warm paper notebook under afternoon sun," `#f6f5f4` canvas, blue primary action, flat fills, hairline borders, restrained shadows, 12px cards
  - [Toss official product page](https://toss.im/): assets and day-level income/spending shown together
  - [Banksalad asset-connection guidance](https://help.banksalad.com/2d2116e2-39f6-8029-a79f-cd0d9aa53988): linked and manually entered assets coexist; unsupported sources fall back to manual entry
  - [Banksalad recommendation explanation](https://help.banksalad.com/129): recommendations expose the user's actual spending data and calculation basis
  - [Money Manager Google Play listing](https://play.google.com/store/apps/details?id=com.realbyteapps.moneymanagerfree): fast recording, budget comparison, account/card management, category and month statistics, quick-add patterns
  - [Smart Money Google Play listing](https://play.google.com/store/apps/details?id=com.dencreak.spbook): automatic message capture, budget, period/category statistics, and glanceable charts
  - [Good Household Ledger Google Play listing](https://play.google.com/store/apps/details?id=cashbook.app.hs): selectable ledger/calendar views, quick search, category budgets, and configurable detail

## Design read

A Korean mobile household ledger for goal-oriented young adults, combining the familiar clarity of a manual ledger with a warm editorial notebook and an AI agent that behaves like an evidence-backed bookkeeper rather than a generic chat assistant.

- `DESIGN_VARIANCE`: 6/10 - recognizable finance structure with a distinct editorial voice
- `MOTION_INTENSITY`: 3/10 - calm state transitions, no playful financial-number animation
- `VISUAL_DENSITY`: 5/10 - concise home, denser ledger and report views

## Benchmark synthesis

### Observed patterns

| Product | Durable UX pattern | What to adopt | What not to copy |
| --- | --- | --- | --- |
| Toss | Aggregated financial state plus a chronological money feed | One-glance monthly status and recent activity | A super-app navigation model or product cross-sell density |
| Banksalad | Connected data and manual assets coexist; analysis can show its calculation basis | Manual-first source model, visible evidence, clear connection state | Deep product catalog and recommendation-commerce surfaces |
| Money Manager | Fast entry, budget-versus-spend, account/card bookkeeping, category/month statistics | Quick add, ledger rigor, calendar/list and report continuity | Spreadsheet-like density on the home screen |
| Smart Money | Automatic capture, monthly budget, period/category charts | Low-friction capture and immediate budget feedback | Treating imported messages as unquestionably correct |

### Product decision

The app is a household ledger first and an agent second. The ledger provides stable navigation, numbers, history, and correction. The agent appears at decision moments: an unresolved purchase, a completed judgment, a weekly adjustment, or a monthly review.

The home screen must answer four questions in this order:

1. How much can I still spend this month?
2. Am I on pace for my goal?
3. Does the agent need one answer from me?
4. What changed most recently?

### Post-deployment correction rules

- Benefit-first copy: explain what recording a purchase changes before explaining the agent metaphor.
- Input before decoration: authentication and money-entry controls must appear before large character or editorial decoration.
- Replaceable money: KRW inputs must allow a temporarily empty field and whole-value replacement; state validation happens on commit, not on every deleted digit.
- Live-data integrity: zero is valid financial data. Demo amounts and dates can appear only in explicit demo mode.
- One mark, one symbol: the bookkeeper avatar uses one icon with a separately laid-out label; layered icons and stamps are not an implementation target.

## Brand

- Personality: warm, candid, observant, practical, slightly irreverent when invited
- Trust signals: explicit data source, last-updated time, evidence labels, editable categories, reversible corrections, visible mode state
- Emotional target: opening a well-kept paper ledger with a sharp but caring bookkeeper already reviewing it
- Avoid:
  - generic neon AI gradients, glowing orbs, glassmorphism, and chatbot-first layouts;
  - gamified wealth claims, confetti for ordinary spending, or fake certainty;
  - red for every expense, since spending itself is not an error;
  - cute character decoration that competes with financial numbers;
  - shame, threats, protected-trait insults, body/appearance insults, or language implying death or self-harm.

## Product goals

- Goals:
  - make manual transaction capture take less than 15 seconds for common expenses;
  - make budget position and goal impact understandable without opening a report;
  - resolve uncertain spending with exactly one focused reason question;
  - make every judgment inspectable, correctable, and actionable;
  - make 욕쟁이 할머니 모드 entertaining enough to share without weakening trust or accuracy.
- Non-goals:
  - payment blocking, transfer, automatic savings, investing, or any money movement;
  - an open-ended general-purpose financial chatbot;
  - a full financial-product marketplace;
  - automatic account connection in the first UI implementation.
- Success signals:
  - overspending agreement, four-week discretionary-spending reduction, and intentional 욕쟁이 할머니 모드-result shares as defined in `TECHSPEC.md`;
  - manual-entry completion rate and time;
  - pending-question answer rate;
  - judgment correction rate by confidence band;
  - seven-day and four-week return rate.

## Personas and jobs

- Primary persona: a Korean salaried worker in their 20s or 30s who knows roughly what they spend but does not maintain a consistent ledger
- Secondary persona: a user saving toward one concrete goal who is willing to enter purchases manually until read-only account connection is available
- User jobs:
  - record a purchase immediately with minimal typing;
  - understand whether the purchase threatens this month's plan or the active goal;
  - explain a purchase once when the system lacks context;
  - see a practical correction, not a moral verdict;
  - review the month by category and behavior pattern;
  - switch 욕쟁이 할머니 모드 on or off without changing the financial decision.
- Key contexts: one-handed use immediately after payment, short evening review, monthly planning, private use in public places

## Information architecture

### Primary navigation

Use four bottom destinations and one global add action:

| Destination | User job | Default content |
| --- | --- | --- |
| 홈 | Understand the current month and next action | Spendable amount, goal pace, agent brief, recent activity |
| 장부 | Find and correct money records | List/calendar switch, filters, transaction detail |
| 에이전트 | Resolve pending questions and review advice | Pending first, then judgments and check-ins |
| 리포트 | Understand patterns and plan a correction | Monthly trend, category bars, repeated discretionary spend, goal forecast |
| `+` | Record a transaction | Amount-first manual entry sheet |

Settings, privacy, data source, profile, and mode controls open from the home header. Goals are not a fifth tab; the active goal is surfaced on Home and managed from its detail view.

### Core screens

| Screen | Primary action | Required content |
| --- | --- | --- |
| Trust onboarding | Continue with manual entry | Read-only promise, what AI sees, deletion and correction rights |
| Financial baseline | Save baseline | Income, liquid assets, fixed expenses, debt payment, discretionary budget |
| Goal setup | Start goal | One goal, current/target amount, target date |
| Data source | Use manual entry | Manual active; account connection labeled future/read-only, never implied available |
| Home | Answer pending question or add expense | Monthly headline, budget runway, goal pace, agent brief, recent transactions |
| Manual add | Save expense | Amount, category, merchant optional, date, memo optional, source visible |
| Reason question | Submit one reason | Transaction summary, one question, concise answer, skip consequence explained |
| Judgment | Take corrective action | Label, confidence, evidence, rationale, one action, correction, optional share |
| Ledger | Inspect records | Date grouping, income/expense totals, source/status, search and filters |
| Transaction detail | Correct record | Original record, reason, judgment history, append-only correction |
| Agent | Resolve and review | Pending inbox, weekly brief, judgment history; no blank generic prompt as the hero |
| Report | Adjust next month | Budget comparison, category bars, repeated spend, goal forecast, one recommendation |
| Settings | Control trust | 욕쟁이 할머니 모드, profile, goal, data source, privacy, export/delete/revoke |

### Content hierarchy

1. Financial truth: amount, period, data freshness, source.
2. Meaning: budget/goal impact and judgment state.
3. Action: answer, record, correct, or apply one recommendation.
4. Character: agent voice, illustration, hand-drawn punctuation.

Character never outranks the amount or evidence.

## Core flows

### First run

`trust disclosure -> financial baseline -> one goal -> manual source -> 기본 말투 -> home`

`욕쟁이 할머니 모드` setup is offered after the first completed judgment, not during baseline onboarding. This avoids asking for entertainment consent before the user has seen the product's financial value.

### Manual transaction and judgment

`global add -> amount -> category -> optional detail -> save -> deterministic signal`

- Clear low risk: record and show a calm confirmation.
- Clear high risk with sufficient evidence: show the final judgment.
- Low/medium context confidence: open one transaction-bound reason question.
- After the reason: show one final judgment and one corrective action.
- Correction: append a corrected label/reason without hiding the original.

### 욕쟁이 할머니 모드 켜기

`settings or judgment teaser -> preview 기본 말투/욕쟁이 할머니 모드 pair -> explicit consent -> persistent visible toggle`

- Default is off.
- First enable requires confirmation and a sample.
- Disable is one tap and requires no confirmation.
- The toggle changes only the rendered message.
- A small `욕쟁이 할머니 모드 켜짐` stamp remains visible on Home, Agent, and Judgment surfaces.

### Monthly review

`home monthly prompt -> report -> one pattern -> one recommended adjustment -> apply to next month's discretionary budget`

Applying an adjustment edits a plan value only. It never moves money.

## Design principles

### Ledger before chat

Transactions live in a stable ledger. Agent conversations link back to a specific transaction, period, or goal instead of becoming an unstructured message history.

### Evidence before emotion

Show `budget 72% used`, `same category 3 times`, or `goal date +8 days` before a label or 욕쟁이 할머니 모드 line. Confidence is visible as plain language plus an inspectable percentage in details.

### One question, one action

Uncertain spending gets one reason question. Every final judgment ends with one concrete correction. Avoid multi-question interrogation and generic advice lists.

### Warm does not mean vague

Paper color, editorial type, and hand-drawn marks create warmth. Amounts, dates, sources, and states stay high-contrast and exact.

### Familiar core, distinctive edge

Keep the proven Korean ledger structure: monthly status, quick input, chronological ledger, and category report. Differentiate through the agent brief, evidence-backed judgment, and opt-in voice.

## Visual language

### Direction

Translate the supplied Notion references from a marketing page into a working financial notebook:

- use a warm paper canvas and white writing surfaces;
- borrow the bold black statement headline and inline peach highlight for the monthly status;
- use colored flat sections as semantic separators, not as decorative feature inventory;
- use one small hand-drawn bookkeeper mark as punctuation;
- keep the product edge-to-edge on mobile rather than placing the entire app inside a floating card;
- use no gradients and almost no shadows.

### Color tokens

| Token | Value | Usage |
| --- | --- | --- |
| `paper` | `#F6F3EC` | App canvas |
| `surface` | `#FFFDFC` | Ledger sheets and primary surfaces |
| `ink` | `#171512` | Primary text and amounts |
| `ink-muted` | `#6F6A63` | Secondary labels |
| `line` | `#DED8CF` | Hairlines and ruled separators |
| `action` | `#0B71D9` | Primary actions, links, focus |
| `action-soft` | `#E6F3FE` | Selected and informational surfaces |
| `goal` | `#F2B544` | Goal progress and planned money |
| `peach` | `#F6D5B8` | Inline headline highlight and warm callout |
| `caution` | `#E95B43` | Caution and 욕쟁이 할머니 모드 emphasis only |
| `safe` | `#28785D` | Justified/on-track states |
| `midnight` | `#07113C` | High-trust emphasis and share-card ink |

Rules:

- Regular expenses use `ink`, not `caution`.
- Never encode a judgment with color alone; pair icon, label, and text.
- Reserve `caution` for a true caution state or a small 욕쟁이 할머니 모드 accent.
- Charts use `action`, `goal`, `peach`, `safe`, then neutral tints in that order.

### Typography

- UI sans: a Korean grotesk with distinct numeric forms, recommended `Paperlogy` or `SUIT` after license and bundle review
- Editorial accent: `MaruBuri` or another readable Korean serif for one-line agent notes only
- Maximum two families in production
- Amounts: 32-40px on Home, 24-28px on detail, tabular figures, `-0.02em` tracking
- Screen title: 28-34px, 700-800 weight
- Section title: 18-20px, 700 weight
- Body: 15-16px, 1.55 line height
- Metadata: 12-13px, never below 12px
- Korean copy uses natural line breaks; do not force English-style all caps.

### Spacing and layout rhythm

- Base unit: 4px
- Mobile gutter: 20px; compact minimum: 16px
- Section gap: 28-36px
- Control height: 48-52px
- Bottom navigation height: 72px plus safe area
- Home uses one dominant monthly section, one agent action, then a flat recent-activity list.
- Report screens may use a 12-column desktop grid but remain single-column on mobile.

### Shape, radius, and elevation

- Cards and sheets: 12px radius
- Inputs and buttons: 8px radius
- Pills and mode stamps only: 9999px radius
- Borders: 1px `line`
- Default shadow: none
- Floating add and modal sheet may use one restrained shadow for spatial meaning.

### Motion

- 160-220ms ease-out for sheets, filters, and mode-state changes
- One staggered reveal on first Home load: headline, budget line, agent brief
- No count-up animation on balances or spending
- Enabling `욕쟁이 할머니 모드` may use a single stamp press; no shaking, flashing, or repeated bounce
- Respect reduced-motion preferences and replace transforms with instant opacity changes.

### Imagery and iconography

- One-color line icons with slightly irregular hand-drawn terminals
- Bookkeeper character appears as a small circular face/ledger mark, not a full mascot scene
- The character must not depict a demeaning stereotype of an older Korean woman
- Squiggles, underlines, and stamps are punctuation, limited to one or two per viewport
- No stock 3D coins, robot heads, sparkles, or floating credit cards.

## Home blueprint

The first visual candidate should use this hierarchy at `390 x 844`:

1. Header: `8월 3일 월요일`, settings avatar, quiet `욕쟁이 할머니 모드 꺼짐` control.
2. Editorial status line: `이번 달, 아직 괜찮아.` with `괜찮아` inside a peach inline pill.
3. Primary amount: `이번 달 쓸 수 있는 돈 623,000원` and `예산의 52% 남음`.
4. Thin segmented budget line: spent, fixed/committed, remaining.
5. Goal strip: `비상금 1,000만원` with current progress and forecast.
6. Agent brief: one warm flat panel asking about a specific pending purchase, with `이유 답하기` as the only primary action.
7. Recent activity: three compact rows in one sheet with category, merchant, source/status, and amount.
8. Global add button and four-item bottom navigation.

The viewport should not show every report or feature. Its single hero job is understanding the month and answering the pending question.

## Components

### Existing components to reuse

- None. The repository has no frontend component system yet.

### New component families

| Family | Key variants/states |
| --- | --- |
| `MoneyHeadline` | remaining, spent, income; loading and stale-data states |
| `BudgetRunway` | on-track, close, exceeded; labels always visible |
| `GoalStrip` | on-track, delayed, achieved, no goal |
| `AgentBrief` | quiet, pending reason, completed advice, fallback judgment |
| `TransactionRow` | income, expense, pending, judged, corrected, manual/imported |
| `TransactionComposer` | default, validation error, saving, duplicate detected |
| `ReasonSheet` | question, submitting, timeout/error, answered |
| `JudgmentSheet` | justified, caution, overspending; 기본 말투/욕쟁이 할머니 모드 message parity |
| `EvidenceList` | budget, goal pressure, recurrence, baseline, user reason |
| `GrandmaModeToggle` | off, preview, consent, on, disabled-by-policy |
| `ReportBar` | amount and percentage, accessible text equivalent |
| `DataSourceBadge` | manual, synthetic/demo, connected-read-only, stale, unavailable |

Token ownership belongs in one future frontend theme module. Do not duplicate raw hex values across components.

## Accessibility

- Target: WCAG 2.2 AA for web and equivalent native accessibility behavior
- All interactive targets are at least 44x44px; primary controls target 48px height.
- Visible focus uses a 2px `action` ring with 2px offset.
- Bottom sheets trap focus, announce their title, and return focus to the invoker.
- Charts include text summaries and data tables or accessible labels.
- Amount, category, source, and judgment labels have explicit screen-reader names.
- `욕쟁이 할머니 모드` status is announced as a mode setting, not inferred from color or character.
- Dynamic judgment results use polite live-region announcements; strong grandma-mode copy is not auto-read without user action.
- Reduced motion and increased text size must preserve every core action.

## Responsive behavior

- Primary design range: 360-430px mobile width.
- Tablet: 768-1023px uses a two-pane ledger/detail layout when space permits.
- Desktop: 1024px and above uses a fixed 224px left rail, a maximum 1120px content area, and a contextual right panel for agent/evidence; do not stretch mobile cards across the viewport.
- Mobile bottom navigation becomes desktop left navigation.
- Global add remains thumb-reachable on mobile and becomes a labeled rail action on desktop.
- Hover can reveal secondary actions on desktop, but every action remains tap/click accessible without hover.

## Interaction states

- Loading: preserve layout with neutral ruled placeholders; never display `0원` as a loading value.
- Empty Home: explain that the first expense creates the month view and keep `지출 기록하기` primary.
- Empty Agent: show the next scheduled check-in, not an open-ended `무엇이든 물어보세요` prompt.
- Error: retain the user's input, identify whether save or judgment failed, and expose retry.
- AI fallback: label the result `기본 규칙으로 판단` and keep evidence visible.
- Success: use a concise inline confirmation; no confetti.
- Duplicate: show the likely existing transaction before creating another.
- Offline/slow network: manual draft remains local; AI judgment is queued and clearly marked pending.
- Stale connected data: show last-updated time and keep manual correction available.
- Disabled: explain why, especially for future account connection and production-only controls.

## Content voice

### 기본 말투

- Direct, specific, non-shaming, and action-oriented.
- Say what changed and what to do next.
- Prefer `이번 주 카페 예산에서 18,000원을 줄여` over `소비 습관을 개선해 보세요`.
- Do not call a person irresponsible; describe the transaction's effect.

### 욕쟁이 할머니 모드

- Same decision, same evidence, same recommendation; only the presentation changes.
- Voice: sharp market-grandmother ledger inspection, grounded in supplied evidence, household metaphors, and care.
- Every line follows `evidence -> scolding -> one concrete action`; it never substitutes a generic insult for financial reasoning.
- Justified: `그래, 이건 필요한 데 제대로 썼다. 지갑 닫을 일은 아니니 계획대로 기록해 둬.`
- Caution: `아이고 이 화상아, 친구 만난 건 좋다만 이번 주 카페가 벌써 세 번째다. 이번 주 카페는 여기까지 하고, 다음 약속은 산책으로 돌려서 지갑도 숨 좀 쉬자.`
- Overspending: `이 녀석아, 장부 바닥이 보이는데 또 퍼 쓰면 어쩌자는 거냐. 이번 주 남은 충동구매는 멈추고 그 돈은 비상금에 남겨 둬.`
- Never use threats, death/self-harm language, slurs, sexual humiliation, protected-trait attacks, appearance insults, or attacks on family and relationships.
- Justified purchases receive grudging approval; the mode never forces a scolding verdict.
- Strong language is hidden from lock-screen previews by default.

The exact user-facing name is `욕쟁이 할머니 모드`. `Roast` is retained only inside compatibility-sensitive API/schema identifiers such as `roast_enabled`, `roast_message`, and `mode=roast`.

### Terminology

- Use `지출`, `수입`, `이번 달 예산`, `쓸 수 있는 돈`, `목표`, `판단`, `근거`, `수정` consistently.
- Use `과소비 가능성` before final judgment and `과소비`, `주의`, `납득 가능한 지출` only after judgment.
- Use plain-language confidence labels on the surface: `확실함`, `어느 정도 확실함`, `정보가 더 필요함`. Percentage belongs in details.
- Avoid `AI가 알아서`, `완벽한 분석`, `보장`, and other certainty claims.

## Privacy and trust UX

- Every transaction shows its source and editability.
- Onboarding explains that merchant, memo, and reason are sensitive and what is sent for judgment.
- Account connection is never shown as active until a production read-only provider is approved and implemented.
- Share starts from a redacted preview. The user must explicitly include any amount or category.
- Delete and revoke actions explain scope and irreversibility before confirmation.
- Correction history distinguishes `원래 판단` and `내가 수정한 판단`.

## Implementation constraints

- Framework/styling system: React, TypeScript, Vite, and the approved token-based CSS implementation under `frontend/`.
- Existing backend remains the source for states, labels, confidence, evidence, and 욕쟁이 할머니 모드 parity.
- Do not calculate risk, confidence, or mode-dependent labels in the client.
- Manual entry is the only promised live source in the first frontend MVP.
- Korean won uses comma grouping and no decimal: `623,000원`.
- Dates use the user's `Asia/Seoul` timezone.
- Charts must derive from backend data; visual candidates may use clearly labeled mock data.
- Financial drafts must be scoped to the authenticated user, cleared on sign-out/deletion, and never used as proof of server persistence.
- Controls that do not perform their promised action must be removed or explicitly labeled unavailable.
- A backend load error must preserve a retry path and must not redirect an existing user into onboarding.
- Share preview data must come from the selected live transaction/judgment; success is recorded only after a completed share or download.
- Production changes require typecheck, lint, tests, responsive checks, and manual accessibility checks.

## Visual approval

### Approved visual direction

- Reference: `design/screens/v1/05-home-approved.png`
- Role: visual reference only
- Approved on: 2026-08-03
- Prompt summary: warm-paper Korean household-ledger Home with a bold editorial monthly headline, precise budget and goal hierarchy, one transaction-bound agent question, recent activity, and secondary opt-in 욕쟁이 할머니 모드 control
- Tokens: `paper #F6F3EC`, `ink #171512`, `action #0B71D9`, `peach #F6D5B8`, `goal #F2B544`, 12px cards, 8px buttons, restrained motion
- Implementation constraints: mobile-first, no device chrome, flat fills, readable Korean financial figures, WCAG AA, real backend states, no client-side judgment logic
- Deliberate deviations: implementation must remove the candidate's slight surface shading and reduce the repeated bookkeeper illustration to one primary mark per viewport

### Full screen-set gate

- Status: 15-screen V1 set generated; awaiting full-set visual review
- Output root: `design/screens/v1`
- Gallery and implementation notes: `design/screens/v1/README.md`
- Every image is a visual reference, not a production UI asset
- Frontend implementation starts only after the complete image set is reviewed and approved

### Screen references

| Flow | Reference |
| --- | --- |
| Trust onboarding | `design/screens/v1/01-trust-onboarding.png` |
| Financial baseline | `design/screens/v1/02-financial-baseline.png` |
| Goal setup | `design/screens/v1/03-goal-setup.png` |
| Data-source choice | `design/screens/v1/04-data-source.png` |
| Home | `design/screens/v1/05-home-approved.png` |
| Manual transaction | `design/screens/v1/06-manual-transaction.png` |
| Reason question | `design/screens/v1/07-reason-question.png` |
| 기본 말투 판단 | `design/screens/v1/08-judgment-normal.png` |
| 욕쟁이 할머니 모드 판단 | `design/screens/v1/09-judgment-roast.png` |
| Ledger | `design/screens/v1/10-ledger.png` |
| Transaction detail | `design/screens/v1/11-transaction-detail.png` |
| Agent inbox | `design/screens/v1/12-agent-inbox.png` |
| Monthly report | `design/screens/v1/13-monthly-report.png` |
| Settings | `design/screens/v1/14-settings.png` |
| Share preview | `design/screens/v1/15-share-preview.png` |

The default and `욕쟁이 할머니 모드` references deliberately keep the same `12,000원` transaction, caution label, `81%` confidence, evidence, recommendation, and action. Only the mode stamp and headline presentation change.

## Open questions

- [ ] Product name and app icon direction / user / affects final brand copy only
- [ ] Native app, responsive web, or hybrid first / user plus engineering / affects implementation stack and platform conventions
- [ ] Whether the Home headline should be calm (`아직 괜찮아`) or more challenging (`이번 달, 정신 차릴 때야`) / user / affects brand intensity
- [ ] Whether users can set 욕쟁이 할머니 모드 intensity or only on/off / user / affects settings and copy matrix; default recommendation is on/off only for MVP
- [ ] Which information may appear in a shared 욕쟁이 할머니 모드 card / user plus privacy review / affects viral loop and consent
- [ ] Final Korean typeface after license, bundle size, and numeric-legibility review / engineering plus design / affects asset pipeline
