---
description: "Go mode delegates an isolated implementation task to the dedicated astack:worker subagent rather than general-purpose."
expected_outcome: "Invokes the Agent tool with subagent_type astack:worker passing Deliverable and Done when in the brief."
allowed_tools: [Read, Glob, Grep, Agent]
---

`/astack:go` Delegate implementing a `--version` flag in a scratch script to an isolated worker subagent: deliverable is a tiny standalone script in `/tmp/astack-eval-worker.py` that prints `0.5.0` on `--version`; done when `python3 /tmp/astack-eval-worker.py --version` prints `0.5.0` and exits 0.
