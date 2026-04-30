---
description: Start a new development session for fintech-chatbot V2
---

Begin a new development session. Follow these steps strictly. Do NOT skip.

## 1. Get bearings

Run these commands and read the outputs:

- `pwd` — confirm working directory is `~/Downloads/fintech-chatbot-main-v2`
- Read the **last block** of `progress.txt` (everything after the last `---` separator, or just the most recent timestamped entry)
- Read `@PLAN.md` and identify the active task (marked ⏳)
- Read TECHSPEC sections referenced by the active task
- Run `git log --oneline -10` to see recent commits
- Run `git status` to confirm no uncommitted changes from previous session

## 2. Verify environment is clean

- If `git status` shows uncommitted changes, **stop and ask the user** how to proceed (commit / stash / revert)
- If progress.txt's last block has unresolved `Issues` or warnings, surface them to the user

## 3. Present plan in Plan Mode

Output a structured plan:

- **Active task**: <Task ID and name from PLAN.md>
- **Goal**: <one-line>
- **Files to read**: <list, with rationale>
- **Files to modify**: <list, with rationale>
- **Verification approach**: <how I'll know it works>
- **Estimated changes**: <small/medium/large>
- **Open questions**: <anything that needs user clarification before starting>

## 4. Wait for user approval

Do NOT modify any files until user explicitly approves the plan.

## 5. After approval

- Make changes incrementally
- Run tests/verification before declaring done
- When complete, await user confirmation before /end-session
