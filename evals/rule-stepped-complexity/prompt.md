---
description: "Redesigns a 6-required-object HTTP client call into progressive tiers where Tier 0 needs only url, Tier 1 adds optional timeout/headers, and Tier 2 composes custom transport and retry policy."
expected_outcome: "Reads stepped-complexity/SKILL.md, simplifies repo/src/http_client.py so fetch(url) works with zero extra arguments, optional timeout and plain headers dict cover Tier 1, and optional transport and retry policy cover Tier 2, with tests for all three tiers."
max_turns: 16
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Bash, Edit, Write]
---

`/astack:go` Callers of `./repo/src/http_client.py` have to construct six mandatory configuration objects just to call `fetch(url)`. Redesign `fetch` in `./repo/src/http_client.py` into progressive tiers that build on one another without forcing simple callers to pay ceremony costs:
- Base tier: `fetch(url)` works with sensible defaults and no extra arguments.
- Middle tier: optional `timeout` (float) and `headers` (plain `dict[str, str]`) work directly on `fetch`.
- Advanced tier: optional `transport` callable (`(url, headers, timeout) -> Response`) and `retry` policy (`RetryPolicy`) compose onto the same `fetch` interface.

Update `./repo/tests/test_http_client.py` to test all three usage tiers.
