---
description: "Analyze cli-kit's implementation and existing contract catalog to recommend minimal-surface next-step features ordered by user impact relative to surface cost while keeping ./repo clean."
expected_outcome: "Reads next-step/SKILL.md, verifies ./repo/src/cli.py against program/astack_home/cli-kit/docs/contracts/cli-contract.md, audits consumer friction, and writes ranked minimal-surface next-step recommendations in program/NEXT_STEPS.md or final_text citing existing contracts, stepped tier progression with zero regression on Tier 0 callers, and user impact, while leaving ./repo clean."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Recommend the next capability rungs for project `cli-kit` (`./repo/src/cli.py`, existing contract catalog under `ASTACK_HOME=./program/astack_home`).

Inspect `./repo/src/cli.py`, `./repo/docs/user_feedback.md`, and the saved contract catalog for `cli-kit`, then produce ranked minimal-surface next-step recommendations (in `./program/NEXT_STEPS.md` or your final response). For each recommendation, map current rung to next rung, specify the minimal contract delta (preserving simpler callers unchanged), explain the concrete user friction removed, and cite `file:line` evidence. Leave `./repo` unmodified.
