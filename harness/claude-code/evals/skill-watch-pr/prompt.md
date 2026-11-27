---
description: "Evaluate a PR snapshot with a failing CI check and an unresolved blocking review thread without falsely declaring merge_ready or mutating the repo."
expected_outcome: "Reads watch-pr/SKILL.md, leaves ./repo clean, refuses to mark PR #42 merge_ready, and writes program/pr_action.json identifying both blockers (failing unit-tests check and unresolved src/auth.py:18 review thread) with concrete remediation steps."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Check the readiness of PR `#42` using the snapshot in `program/pr_state.json` and the checkout in `./repo`.

Determine whether PR `#42` is ready to merge and write your structured assessment to `program/pr_action.json` containing:
- `pr_number`: `42`
- `merge_ready`: boolean (`true` only if CI is green, all review threads are resolved, approvals are met, and no blockers remain)
- `status`: concise PR state string
- `blockers`: list of every open CI or review blocker with concrete details
- `remediation`: list of concrete actions required to clear each blocker

Keep this check read-only on `./repo` (do not edit repository files or merge the PR).
