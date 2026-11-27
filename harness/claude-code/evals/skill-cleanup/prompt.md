---
description: "Remove temporary scratch and debug leftovers from ./repo while preserving tracked source/tests and durable review/repro bundles under ASTACK_HOME."
expected_outcome: "Reads cleanup/SKILL.md, deletes repo/debug_tmp.log, repo/scratch_repro.py, and repo/.tmp_trace so git status is clean and unittest passes, while strictly preserving durable files under program/astack_home/billing/reviews/ and program/astack_home/billing/repros/."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` We just finished debugging and reviewing a billing fix in `./repo` (project `billing`, with `ASTACK_HOME` at `program/astack_home`).

Clean up the temporary debug and scratch leftovers in `./repo` so the repository is clean and unit tests still pass, while strictly keeping all tracked files and all durable evidence bundles under `program/astack_home/billing/`. Report what you removed and what you preserved.
