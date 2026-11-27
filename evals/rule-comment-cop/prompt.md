---
description: "Strips narrating comments, ASCII banners, change history, and commented-out code while preserving license headers and external protocol/bug-tracker constraints."
expected_outcome: "Reads comment-cop/SKILL.md, removes narrating/stale/commented-out comments from repo/src/rate_limiter.py, preserves the SPDX license header and RFC 6585/Envoy constraint comment, and keeps behavior and tests passing."
max_turns: 16
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Bash, Edit, Write]
---

`/astack:go` Clean up the comments in `./repo/src/rate_limiter.py`. The file has accumulated noisy comments, dividers, old history notes, and commented-out code alongside comments that matter for legal compliance and an external proxy quirk. Keep what code cannot express on its own, make the implementation self-explanatory, and keep all behavior and tests in `./repo/tests/` passing.
