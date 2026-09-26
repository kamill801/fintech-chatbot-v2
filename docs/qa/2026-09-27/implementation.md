# Task 8.2 implementation verification — 2026-09-27

## Scope and outcome

The new frontend keeps a confirmed transaction saved when a later summary or plan read fails, updates the list by transaction ID, and returns from manual entry to the saved transaction's KST calendar date. An uncertain POST retry uses the same payload and operation ID. Home has a functional top-right profile entry; Settings has budget and goal edit screens. Onboarding starts real accounts without demo financial values; plan creation restores drafts, validates its period and expenses, and requires a preview matching the current draft/version before confirmation. Mobile forms, settings, reports, and transaction labels were tightened without adding dependencies or changing backend behavior.

## Local proof

- Frontend Vitest: 16 files, 81 tests passed. Includes mutation success boundary, retry identity/double tap, calendar date return, settings edit, new-account values, plan preview invalidation, and the backend's 366-day plan limit.
- `npm run lint`, TypeScript/Vite `npm run build`, and `git diff --check` passed.
- Chromium visual checks in explicit demo mode covered 320, 375, 414, and 768 CSS-pixel widths on Home, add, ledger, report, settings, and plan. No document-level horizontal overflow was observed after the 320px fix. A horizontal recent-entry strip scrolls within its own area by design. The plan's date and amount inputs, its progress spacing, top-right profile button, and narrow settings toggle were checked visually.
- No real account transaction, provider setting, secret, or financial record was changed for QA. Backend files were not modified; the existing Render service was not redeployed.

## Production proof

- Manual production deploys target the existing `upglow/jangbu-ai` project (`prj_gTH83PeOngR9KgAURhLloW94X32F`) and its `https://jangbu-ai.vercel.app` alias; the CLI reported `READY`.
- Production root HTML referenced the generated JavaScript bundle; the bundle returned HTTP 200 with JavaScript content type. Direct `/plan` and `/settings/budget` requests returned HTTP 200 with the SPA HTML.
- In the production demo, Home exposed `내 프로필 및 설정`; selecting it opened `/settings?demo=1`, and the budget row opened `/settings/budget?demo=1` with the existing demo values.

## Unproven

- The exact HTTP response and server-side cause of the user's earlier failed transaction are unavailable. The reproduced frontend path of a successful POST followed by a failed secondary read is fixed, but this is not a claim that every backend failure mode is resolved.
- Authenticated account storage/calendar persistence and a real iPhone WKWebView date field, keyboard, safe-area, and Home Screen test were not performed in this release. Those need device/account evidence before claiming real-device E2E completion.
