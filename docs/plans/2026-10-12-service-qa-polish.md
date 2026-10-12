# Task 8.4 execution plan

User authorized a complete existing-service test/fix loop and final release, preserving every capability. Work uses native Codex, one active task, one final source commit. TECHSPEC is unchanged.

1. Inventory reachable routes and success/error/persistence outcomes. Review the existing release and inspect live screens before changes. Keep production records intact; synthetic development/demo fixtures cover destructive and failure scenarios.
2. Reproduce material defects through the real browser and targeted regression tests. Prioritize data loss, wrong state, blocked actions, navigation, misleading periods, then layout/readability/accessibility.
3. Implement bounded changes using existing components, style tokens, and adapters. Ownership lanes: root handles shared CSS/components and release; delegated lanes own their assigned feature files or staged skill artifacts. No new dependencies or providers.
4. Test each changed invariant, integrate, and exercise the whole route matrix at 320/390/414/1440 widths, including keyboard, large money/long text, empty states, failure/retry, and reload/back behavior. Capture before/after evidence and iterate on newly observed defects.
5. Run existing full tests with isolated Redis, frontend lint/build, independent review, and final browser paths. Test provider calls only within existing approved credentials/privacy limits.
6. Save a reusable native `service-qa-release` workflow with explicit scenario evidence, regression policy, safe user-data boundaries, finite completion criteria, and Goal routing. Validate the bundle and all required backups/catalogs.
7. Stage only the intended app/test/docs files, perform the existing commit/push security checks, commit once, push, and deploy the exact final source to existing Vercel/Render. Verify public readiness plus authenticated behavior. Record honest physical-device/provider gaps.

Stop only after completion evidence is satisfied, explicit user pause/cancellation, or a demonstrated external blocker has no remaining safe recovery path. Do not equate arbitrary repeated green tests with universal bug freedom.
