---
description: "Resolve a protocol version contradiction across local sources and repo code, verify exact quotes in place, grade findings A-F using canonical score bands, persist research under ASTACK_HOME, and keep ./repo clean."
expected_outcome: "Reads research-this/SKILL.md, inspects ./repo/src/client.py and ./program/sources/ (official-spec-v2.1.md vs old-blog-2021.md), verifies quotes in place, resolves the contradiction in favor of primary sources (v2.1 + SHA-256 HMAC), flags the 2021 blog as outdated counterclaim, assigns canonical A-F grades and numeric scores without drifted 55-69 or 30-54 bands, persists the report under program/astack_home/proto-check/research/, and leaves ./repo clean."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Read `./program/question.md` and investigate the conflicting protocol sources in `./program/sources/` alongside the implementation in `./repo/src/client.py` for project `proto-check` (`ASTACK_HOME=./program/astack_home`).

Verify every quote at its exact source location, record counterclaims and stale sources explicitly, grade each finding A–F with numeric scores and one-line rationales, and save the finished research report under `$ASTACK_HOME/proto-check/research/`. Leave `./repo` unmodified.
