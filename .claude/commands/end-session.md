---
description: Wrap up the current session for fintech-chatbot V2
---

Wrap up this session in a clean state. All steps required.

## 1. Verify changes work

- Run any tests that apply (`python -m py_compile <file>`, manual review, etc.)
- For Phase 1 Task 1.4 onwards: actually test with kakao callback (requires .env)
- If verification fails, stop and ask user how to proceed

## 2. Stage and commit

```bash
git add -A
git status
```

Wait for user approval, then commit with this format:

```
[Phase X / Task Y.Z] <one-line summary>

What changed:
- <file>: <change>

Why:
<rationale>

Verification:
<what was tested and result>
```

Capture commit SHA: `git rev-parse --short HEAD`

## 3. Append to progress.txt

Append (do NOT edit existing entries):

```
[YYYY-MM-DD HH:MM] [Phase X / Task Y.Z] <commit-sha>
What: <one-line summary>
Why: <one-line rationale, optional if obvious from What>
Next: <what next session should do, INCLUDING any traps or context the next session needs>
Issues: <decisions made, blockers encountered, technical debt noted, optional>
```

**Critical**: The `Next` field should be self-sufficient. A new session should be able to start work from progress.txt's last block + PLAN.md without reading anything else.

## 4. Update PLAN.md

- Mark current task as ✅ if complete (add commit SHA next to status)
- If task partial: leave ⏳, but update task body with current progress note
- If next task should become active: change its marking from 📋 to ⏳
- Update "Current State" section at top of PLAN.md (Phase, Active Task, Last Session, Last Commit)

## 5. Print summary

```
✅ Session complete
Commit: <SHA>
Files changed: <count>
Task status: <complete/partial>
Next active task: <Task ID>
```

Do NOT push to remote unless user explicitly asks.
