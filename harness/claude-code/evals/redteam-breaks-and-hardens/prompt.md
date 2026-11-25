---
description: "Zero-hint outcome eval for redteam: proactively attacks and limit-tests a live mini auth/storage service, reproduces planted security and concurrency bugs without modifying code during review, dispatches fixes, re-reviews until clean, and leaves zero debug leftovers."
expected_outcome: "Reads redteam/SKILL.md, actively breaks the path traversal, fail-open token check, and split-lock rate limiter race, fixes all three cleanly with red-first tests that fail on original main, and leaves repo clean."
max_turns: 36
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Bash, Agent]
---

`/astack:go` Proactively red-team and harden the local service in `repo/` (settings in `program/settings.json`). Actively try to break it in local dev execution, fix every issue you prove, re-verify until no proven issues remain, and summarize what you broke and fixed.
