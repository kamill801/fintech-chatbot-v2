# service-qa-release Skill Findings

## Scope

Created a repo-staged portable skill bundle at `tools/skills/service-qa-release/` for the user's requested repeat-QA, fix, and final-release workflow. This bundle is intentionally generic across service projects and does not hardcode Jangbu AI ledger behavior.

## Relationship To Existing Skills

- `service-review-improve` remains the smaller service audit and improvement skill.
- `service-qa-release` covers the larger loop the user requested here: scenario matrix, repeated browser/service QA, regression-backed fixes, full verification, one source commit, same-revision provider deployment, and release evidence.
- Native Codex `/goal` is described as a continuation tracker when explicitly requested. It is not treated as equivalent to the QA matrix or release evidence.

## Bundle Contents

- `SKILL.md`: main instructions, boundaries, finite workflow, and stop criteria.
- `agents/openai.yaml`: UI metadata and implicit invocation enabled.
- `references/scenario-matrix.md`: reusable matrix schema and status terms.
- `references/evidence-report.md`: reusable QA/release evidence template.

## Collision Check

Checked installed skill entrypoints under `/Users/dd/.codex/skills`, `/Users/dd/.agents/skills`, and the project `.agents/skills`. No existing `service-qa-release` skill was found.

## Global Save Destinations For Root

The user asked to save reusable skills using the full saving contract. After review, root should copy and validate this bundle in all required destinations:

- Codex bundle: `/Users/dd/.codex/skills/service-qa-release/`
- Agents mirror: `/Users/dd/.agents/skills/service-qa-release/`
- Mac Skills entrypoint: `/Users/dd/Documents/Skills/service-qa-release.md`
- Mac Skills bundle: `/Users/dd/Documents/Skills/bundles/service-qa-release/`
- Mac Skills indexes: `/Users/dd/Documents/Skills/INDEX.md` and `/Users/dd/Documents/Skills/manifest.json`
- Wiki raw/versioned source and operating bundle under `/Users/dd/Documents/LLM-Wiki/`
- Wiki central catalog: `/Users/dd/Documents/LLM-Wiki/wiki/synthesis/Personal skill catalog.md`
- Wiki index/log plus local `brain.py index` and `doctor`

This subtask did not perform global writes, activation, commit, push, deployment, cloud publication, or credential changes.

## Root completion evidence

Root completed all destinations after the forward test. All four bundles hash-match and validate. Mac standalone/INDEX/manifest and Wiki immutable source, request excerpt, source page, operating bundle, catalog, index/log are saved. Local brain index/doctor: bookkeeping_passed=true, issues=[], external_calls=0. No human semantic approval, cloud publication or credential action is inferred.
