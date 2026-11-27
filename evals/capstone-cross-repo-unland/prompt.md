---
description: "Audit cross-repo callers broken by repo-core commit B in program/BLAST_RADIUS.md, revert only commit B in repo-core while preserving commit C and history, pin exact SHAs in order repo-core -> repo-service in program/release-plan.json, and prove both test suites pass."
expected_outcome: "Writes program/BLAST_RADIUS.md citing exact file:line callers in repo-service and the int-to-dict breakage, reverts only breaking commit B in repo-core without rewriting history or dropping commit C docs, updates program/release-plan.json with exact 40-char pinned SHAs ordered repo-core -> repo-service with zero floating refs, and verifies both repo-core and repo-service unit test suites pass."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
timeout_seconds: 1200
---

`/astack:go` Read `program/brief.md` and recover the cross-repository regression between `./repo-core` and `./repo-service`.

Document the downstream callers and concrete failure modes in `program/BLAST_RADIUS.md`, safely revert only the breaking return-shape commit in `./repo-core` while preserving git history and the later documentation commit on top of it, fix `program/release-plan.json` to pin exact commit SHAs in dependency order (`repo-core` before `repo-service`), and prove both `./repo-core` and `./repo-service` test suites pass.
