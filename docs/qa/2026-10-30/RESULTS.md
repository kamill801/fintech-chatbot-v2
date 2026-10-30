# 장부 AI 전체 서비스 및 할머니 말투 검증

- Run: `jangbu-qa-2026-10-30-01`; Task 8.5; native Codex.
- Baseline production: `ed2cadda4cff981f5c63705b575f86e725b18ebb`.
- Candidate: uncommitted working tree based on that revision. No application release in this run.
- Contract: [CONTRACT.md](CONTRACT.md), frozen nine-case [PERSONA-RUBRIC.md](PERSONA-RUBRIC.md), persisted [rounds.json](rounds.json).
- The six repair passes are not six successful complete E2E runs. The service passes exercised different retained journeys; actual model evaluation was blocked initially and later sampled on the older production revision.

## Confirmed login failure and recovery

The current public frontend bundle points to the registered existing Supabase ref `kkzsyprcujrxzrsognhb`, organization `mtydqzgsdegviajlzfwa`. Both project lookup and the project list returned `INACTIVE`; public DNS returned `NXDOMAIN`. This is an independent production authentication failure, not evidence of a bad deployed OpenAI key.

Restoration of that same Free Seoul project was accepted, progressed through `COMING_UP`, and then returned `ACTIVE_HEALTHY`. The public auth JWKS endpoint returned HTTP 200. A newly opened Chrome production tab restored the original authenticated account, existing records, plan and settings. No replacement project, credential, plan, region, financial profile or storage migration was created. Existing ledger storage remains encrypted Redis.

Restored-session access is verified; a new Kakao authorization-code callback remains a separate check. The previous failed consent attempts are not counted as successful callbacks.

## Repair batches and regressions

| Batch | Demonstrated problem and repair | Evidence |
|---|---|---|
| 1 / F1–F2 | Reason evidence counts expenses in the transaction-anchored KST seven-day window, excludes future/income/transfer rows, and identifies matching-month budget evidence. Corrected judgments honor the current voice. | Meaningful red-to-green tests; actual local reason/correction UI. |
| 2 / F3–F5 | New demo expenses no longer inherit the cafe example. Plan matches enforce period, timezone, expense/budget and unique-link eligibility. Account input labels are readable. | Context/plan regressions and 24 responsive route/width checks. |
| 3 / F6–F8 | Demo correction readback retains true original labels. Detail category icons match the transaction. Copy accurately uses 30 days. | Local income/transfer/edit/filter/correction journeys; regression tests. |
| 4 / F9–F12 | Remove invented prompt examples, constrain grounded Korean colloquial voice, disclose display substitutions separately, allow innocuous 설거지/positive acknowledgement, and use category icons in results. | Backend31 and frontend15 targeted cases; configured local model attempts both401, so no live semantic pass. |
| 5 / F13–F15 | Materially edited demo artifacts receive a new identity and do not inherit old corrections. Auth transport and body abort at90s; read-only session/metadata waits are bounded and stale snapshots cannot overwrite confirmed auth events. | Auth red7 failures and demo red3 failures → targeted45/45. Installed-SDK synthetic late-body sign-in prevention tested. Read-only independent review approved. |
| 6 / F16 | Restore the existing inactive production auth project. | Exact ref/org/live bundle match, healthy completion, auth endpoint200 and authenticated production UI readback. |

F17 was observed during pass6 verification: an actual hosted cafe judgment claims the budget was exceeded while the reason screen shows about41% used. Both normal and roast prose make that unsupported claim. The third hosted shopping case also invents a remorse signal absent from the reason; its101% budget-exceedance statement itself is supported. This is an unresolved semantic defect of the hosted baseline; it is not silently repaired inside verification or counted as a pass of the candidate prompt.

## Retained-feature matrix

`Passed` below is scoped to the stated environment. It does not imply hosted or hardware coverage.

| ID | Candidate evidence (test manifest in source-manifest.json) | Production / remaining gate | Status for full readiness |
|---|---|---|---|
| A Auth/session/ownership | Auth restore, failed/late reads, cancellation, body deadlines, SDK session persistence and server ownership regressions. | Existing session restored after same-project recovery. Fresh Kakao callback and hosted candidate auth transport unverified. | Partial |
| B Onboarding/profile/goal | Existing route/profile regression suite preserved and passed. | No fresh account onboarding mutation; original profile preserved. | Partial |
| C Home/navigation | Local browser home/settings/navigation; current summary rules in tests. | Hosted home, existing plan/goal/records/settings read back. Candidate not deployed. | Partial |
| D Expense/income/transfer | Local UI expense12500, income50000, transfer10000→edit11000; isolated storage/API tests. | Hosted QA expense8500→reason→judgment→Oct30 calendar8500. No hosted income/transfer candidate journey. | Partial |
| E Calendar/list/detail | Local selected date, filters, detail/edit and correction readback; backend fixtures include deletion. | Hosted three labeled QA rows survived reload: Oct30 total488500, month811000, settings export21 records. No production deletion performed. | Partial |
| F Reason/judgment/correction/reflection/share | Local reason, correction, reflection, mode and share/provenance regression coverage. | Hosted reason and both voices inspected; F17 unsupported assertion. Exact model/raw display provenance not exposed in baseline UI. Necessary treatment acknowledged but displayed voice mixes colloquial and formal endings. | Failed/Partial |
| G Plans | Local draft→preview→confirm→check-in→revisionv2; period/link regressions. | Original hosted plan retained and displayed; candidate hosted confirmation not verified. | Partial |
| H Reports/coach | Local report UI and backend aggregate/briefing tests; deterministic calculations preserved. | Candidate hosted AI quality not established. | Partial |
| I Settings | Local mode/accounts/dialog-cancel/settings; regression suite. | Hosted mode save/readback and original profile/budget/goal retained; original modeoff saved again after tests. | Partial |
| J Privacy/export/revoke | Actual local CSV downloaded and parsed; isolated backend deletion/revocation/privacy tests. | No destructive production actions or private upload performed. | Partial |
| K Recovery/accessibility | Late/failed response, stale revision, cancellation, draft/idempotency, auth race regressions; local focus/dialog/browser paths. | Candidate hosted recovery not deployed/verified. | Partial |
| L Responsive | 24 local route/width checks at320/390/414/1440: no document overflow, visible input text>=16px; approved tokens preserved. | Physical iPhone/WKWebView keyboard/safe area not rechecked. | Partial |
| M Persona semantics | Frozen nine fixtures; local provider401 evidence retained; deterministic rendering tests pass. | Actual older hosted output sampled; factual gate failed. Three completed successful live candidate batches not achieved. | Failed/Blocked |

KakaoTalk webhook delivery and physical-device installation are not proved by local adapters or browser viewport emulation. No competitor or viral-performance comparison was requested or established.

## Actual hosted sample outcomes

These are three cases on the existing production revision, not three completed evaluation batches of the new candidate. No claim of real model/raw output provenance can be made from this older UI alone.

| Case | Actual shown result | Semantic assessment |
|---|---|---|
| Cafe8500, reasonhabit, shown41% used | Overspending95%; claims budget exceeded in rationale and both voices. | Factual hard gate failed,7/10. Risk-based overspending could differ from budget exceedance; the latter claim lacks support. |
| Necessary treatment160000, shown61% | Justified85%; acknowledges needed treatment, then switches to formal advice. | Necessity respected; voice/action quality6/10, below threshold. |
| Mood shopping320000, shown101% | Overspending95%; budget exceedance supported, but rationale invents remorse. | Factual hard gate failed,6/10; immediate action is weaker than next-month advice. |

After reload, all three synthetic QA records remained on Oct30, totaling488500; month total811000. The settings export entry showed21 records, consistent with18 original plus3 QA records. No original records were deleted. The financial profile, budget and goal were preserved. The original grandma-modeoff setting was saved again and confirmed after authenticated reload. Detailed output and scores are in `hosted-persona.json`.

## Final source verification

| Check | Result |
|---|---|
| `cd frontend && npm test` |147/147,17 files. |
| Isolated Redis backend unittest discovery |170/170, no skips;33.236s. |
| `cd frontend && npm run lint` | Passed. |
| `cd frontend && npm run build` | TypeScript and Vite production build passed. |
| Python compile of changed ledger/validators/tests/evaluator | Passed. |
| `git diff --check` | Passed. |
| Independent focused auth review | Approved changed scope; synthetic tests, not hosted provider proof. |

The23 changed source/test files are fingerprinted in `source-manifest.json`; documentation-only updates after these checks do not change that tested code.

Fresh command logs: `/tmp/jangbu-final-frontend.log`, `/tmp/jangbu-final-backend.log`, `/tmp/jangbu-final-lint.log`, `/tmp/jangbu-final-build.log`. These are local evidence, not deployment evidence.

Local browser artifacts and screenshots are in `/Users/dd/.codex/visualizations/2026/09/13/01a09a1a-720c-7b51-bce2-8bb9d40591bf/jangbu-three-rounds-2026-10-30/`. Synthetic provider inputs/errors are in `persona-batch-1.json`; hosted output, context differences and semantic scores are in `hosted-persona.json`. Never interpret the deployed current profile as the fixed fixture's ratios.

## Release and outstanding work

Commit/push/deploy remain authorized, but the predeclared full required gates have not cleared. The new source has not been committed, pushed or deployed; no new Vercel/Render deployment ID exists for this candidate. Deployed confirmation slots used0/2. Existing `.agents/`, `AGENTS.md` and the old local resume artifact remain outside the source change scope.

The configured local provider401 does not justify changing an already connected production key. The user declined key replacement. Restore and test existing production first, as done here; retain unknowns rather than extracting credentials or declaring model success from fallback or lexical tests.

The frozen six-pass run closed6/6 with stop_reason `limit_reached_required_gates_unmet`; deployed confirmation remains0/2. Pass6 safe verification finished and the checkpoint is preserved. Full-service readiness and the requested release remain incomplete because of factual quality and candidate hosted verification gaps. A future authorized run must first reproduce F17 against recorded allowlisted model signals and distinguish risk-based overspending from an unsupported assertion that the budget itself was exceeded; then verify the candidate prompt on the original nine-case rubric before release. Keep the full feature inventory and thresholds unchanged.
