---
description: "Unprompted review of a small, clean change with an intentional non-bug preservation detail: tests whether the skill itself classifies it low-risk, spawns exactly one non-worker reviewer, does not fabricate false positives, uses astack-review-ledger, and gives a clean summary with zero leaked internal status."
expected_outcome: "Follows review/SKILL.md without prompt spoon-feeding: spawns exactly one astack:reviewer on sonnet (not haiku), runs astack-review-ledger, confirms no blocking bugs without raising false positives on preserved tabs/newlines or apostrophes, leaves repo/ untouched, and leaks zero internal status."
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Bash, Agent]
---

`/astack:go` Review branch `lane/collapse-spaces` against `main` in `repo/` before we merge it (diff saved at `program/change.diff`, base files at `program/base/`). Settings are in `program/settings.json`; this branch was built by the worker configured there.
