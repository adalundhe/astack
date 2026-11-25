---
description: "Zero-hint outcome eval: tests whether review inspects PR comments, linked issues, ADRs, and git history before asking questions, enforces astack coding rules, and states contradictions plainly with both sides and concrete actions rather than cryptic fragments."
expected_outcome: "Catches silent exception swallowing contradicting issue #42 and no-hidden-flow-control with reproduction, states the README-vs-commit/config contradiction on tools-useast1-prod plainly with both sides and concrete fix, catches magic constants/implicit state violating AD-003 and coding rules, avoids asking lazy questions already answered in PR comments or linked issue #42, and leaks zero internal review status."
max_turns: 20
timeout_seconds: 480
allowed_tools: [Read, Glob, Grep, Bash, Agent]
---

`/astack:go` Review branch `lane/webhook-batching` against `main` in `repo/` before we merge it (diff saved at `program/change.diff`). The PR description, existing PR comments, and linked issue are in `program/`. Settings are in `program/settings.json`; this branch was built by the worker configured there.
