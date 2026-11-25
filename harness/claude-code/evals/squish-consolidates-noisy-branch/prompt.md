---
description: "Zero-hint outcome eval for squish: consolidates a 6-commit noisy feature branch into clean logical commit(s) while preserving exact tree equivalence and a second contributor's authorship credit."
expected_outcome: "Reads squish/SKILL.md, squashes the 6 noisy commits to <=2 commits on the feature branch, preserves identical final tree contents, keeps Bob's authorship credit (passing authorship-check), and leaves tests green."
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Bash]
---

`/astack:go` The feature branch `feat/retry-jitter` in `repo/` finished work and review, but its commit history has 6 noisy fixup/revert commits (including a commit from Bob). Clean up and consolidate the branch history before we open a PR without losing any changes or contributor credit.
