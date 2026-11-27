---
type: llm
---

Evaluate the HTTP client API redesign against `stepped-complexity`.

PASS if all of these hold:
- Tier 0: `fetch(url)` works with zero mandatory extra arguments and sensible defaults.
- Tier 1: callers can pass optional `timeout` and plain `dict` `headers` without wrapper ceremony classes.
- Tier 2: callers can compose optional custom `transport` and `retry` policy onto the same `fetch` interface without rewriting from scratch.
- Removes unnecessary mandatory ceremony objects from the `fetch` signature and covers all three tiers in `./repo/tests/test_http_client.py`.

FAIL otherwise.
