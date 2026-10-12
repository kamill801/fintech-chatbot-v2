---
name: service-qa-release
description: Run a finite, evidence-based service QA and release loop when the user asks to repeatedly test an existing app, fix bugs and UX issues, preserve all features, and ship one verified commit/deployment. Complements service-review-improve; use that skill for a smaller service audit or report-only pass.
metadata:
  short-description: QA, fix, and release an existing service
---

# Service QA Release

Use this skill when the user wants an existing service exercised like a real product, improved until the discovered required issues are resolved, and released as one reviewable source/deployment revision. It is for implementation work, not a report-only review.

This skill complements `service-review-improve`: use that skill to understand whether the service experience works and what to fix; use this one when the task also requires repeated end-to-end QA, preservation of existing behavior, and a final commit/push/deploy path.

## Operating Boundaries

- Preserve the product's existing features, data model, auth boundaries, financial or business invariants, and provider accounts unless the user explicitly changes them.
- Do not create new infrastructure, paid services, credentials, destructive data changes, publication, or external account changes merely because release QA is requested.
- Separate confirmed behavior from unknowns. Passing local tests, a green build, HTTP 200, or an accepted async deploy does not prove authenticated production E2E.
- Treat AI output as interpretation unless the product spec explicitly assigns it deterministic authority. Calculations, authorization, eligibility, privacy, money movement, and source gating stay deterministic.
- For state, calculation, storage, navigation, or cross-step bugs, reproduce or lock the behavior with a meaningful regression before changing logic. Simple copy or spacing edits do not need artificial tests.
- Use native Codex goal tools only when the user explicitly requests a goal or `/goal`. A goal tracks continuation; it does not replace the finite QA matrix, evidence report, or release checks.

## Workflow

1. Establish the release claim: the exact user-facing service flow to prove, the features that must remain reachable, the provider/deployment targets, and the stop condition. Read the current project rules, source specs, plans, and dirty worktree before editing.
2. Build a scenario matrix before fixing broad issues. Include happy paths, incomplete input, error recovery, draft/refresh behavior, mobile and desktop layouts, persistence, auth/session edges, provider failure states, and any domain-specific invariants. Use [references/scenario-matrix.md](references/scenario-matrix.md) when the task needs a durable matrix.
3. Baseline with fresh evidence. Run the smallest local checks that expose current failures, then browser-test real workflows enough to see the user journey. Record whether each finding is confirmed, inferred, blocked, or out of scope.
4. Fix required defects in priority order: data loss and wrong results first, broken flows next, then layout/copy/accessibility polish. Keep diffs small and aligned with existing patterns.
5. After each fix, rerun the targeted reproduction plus any affected unit/integration/browser checks. Keep iterating while new confirmed required defects remain and a safe local path exists.
6. Before release, repeat the full matrix on representative responsive widths and the configured production-like environment. Check for horizontal overflow, hidden controls, keyboard/safe-area issues, stale state, confusing empty/error states, and accidental feature removal.
7. Run the full project verification appropriate to the change: tests, lint, typecheck, build, server smoke, storage/provider integration, and an independent diff review when the change is broad.
8. Commit and push only when authorized and after verification. Deploy only when release/deployment is explicitly requested or already authorized in the session; otherwise record deployment as a gap. Deploy the exact committed SHA to the existing configured providers; record deployment IDs, URLs, source SHA, and authenticated smoke evidence. Do not claim deployment completion from a queued or in-progress operation.
9. Finish with a concise report: what changed, what evidence passed, release identities, remaining explicit gaps, and how the user can test the result.

Stop when the matrix passes for required scenarios, no unresolved reproducible required defect remains, and release checks have evidence. If a scenario cannot be verified without credentials, destructive data changes, paid services, or user-owned device action, record that gap instead of marking it passed.

## Evidence

For substantial runs, keep a repo-local QA artifact with:

- release claim and preserved-feature list;
- scenario matrix with status and evidence links;
- defects found, root cause, fix, regression, and verification;
- responsive screenshots or notes for key screens;
- test/build/smoke command results;
- commit, push, deployment, and production smoke identities.

Use [references/evidence-report.md](references/evidence-report.md) as the report template when the project does not already have one.
