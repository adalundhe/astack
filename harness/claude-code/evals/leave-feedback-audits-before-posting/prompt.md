---
description: "Zero-hint outcome eval: tests whether /astack:go routes PR review comment preparation through leave-feedback, spins up an independent reviewer agent to audit the draft against the PR/comments/linked issue/docs/README, and rewrites cryptic SHAs, lazy questions, inactionable prose, and leaked internal thinking into clear, concise, actionable human feedback."
expected_outcome: "Reads leave-feedback/SKILL.md, spawns an independent astack:reviewer agent to audit program/draft-comment.md against repo/ and program/ context, removes cryptic bare-SHA phrasing, lazy questions already settled in PR comments/issue #42, rambling/stilted wording, and leaked internal thinking, states both sides of the README-vs-commit contradiction and the silent-drop bug with concrete actions, and writes the finalized comment to program/final-comment.md."
max_turns: 16
timeout_seconds: 360
allowed_tools: [Read, Write, Glob, Grep, Bash, Agent]
---

`/astack:go` Turn `program/draft-comment.md` into a final human-ready GitHub PR review comment for PR #87 (`lane/webhook-batching` in `repo/`; the PR description, existing PR comments, and linked issue are in `program/`). Do not run `gh` to post externally—write the final comment to `program/final-comment.md` and return it in your reply.
