---
description: "Hard multi-file outcome eval (5 files, 5 planted blocking bugs of varying difficulty including a cross-file seam bug and a cache-poisoning bug, plus 1 false-positive decoy and 1 minor nit — all unit tests green, zero prompt hints): tests whether vectored review finds hard bugs across seams, rejects the false-positive decoy, never stops prematurely while bugs remain, and never leaks internal review status."
expected_outcome: "Follows review/SKILL.md without prompt hints: slices and/or adds a seams vector, continues past 2 reviewers via the cautious stopping bound, proves at least 4 of 5 planted blocking bugs (including at least one hard cross-file/cache bug) without falsely flagging the os.replace decoy as blocking, leaves repo/ untouched, and leaks zero internal status."
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Bash, Agent]
---

`/astack:go` Review branch `lane/order-checkout` against `main` in `repo/` before we merge it (diff saved at `program/change.diff`). Settings are in `program/settings.json`; this branch was built by the worker configured there.
