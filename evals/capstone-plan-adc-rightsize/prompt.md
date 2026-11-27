---
description: "Publish AD_2.md preserving AD_1.md, save a contract-reduction catalog under program/astack_home/sdk-v2/docs/contracts/, refactor the 10-arg repo/src/client.py into progressive tiers with actionable errors replacing ERR_9, and sync repo/docs/api.md."
expected_outcome: "Preserves program/astack_home/sdk-v2/architecture/AD_1.md untouched, publishes valid AD_2.md with full AD_FORMAT frontmatter and sections, saves a grounded contract-reduction catalog under program/astack_home/sdk-v2/docs/contracts/, refactors repo/src/client.py so Tier 0 fetch(url) works with defaults while optional timeout/headers/retry/transport remain composable and errors are actionable instead of ERR_9, syncs repo/docs/api.md resolving the timeout contradiction, and passes unittest, mutations, and gate checks."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit, Agent]
timeout_seconds: 1200
---

`/astack:go` Read `program/brief.md` and redesign the client interface for project `sdk-v2` in `./repo`.

Publish the next architecture decision at `program/astack_home/sdk-v2/architecture/AD_2.md` without modifying the existing `AD_1.md`, save a contract-reduction catalog under `program/astack_home/sdk-v2/docs/contracts/`, refactor `./repo/src/client.py` from its 10-argument mandatory interface and cryptic `"ERR_9"` errors into a progressive API where `fetch(url)` works out of the box with clear actionable errors while advanced options remain optional, resolve the timeout-default contradiction in `./repo/docs/api.md`, and expand `./repo/tests/test_client.py`.
