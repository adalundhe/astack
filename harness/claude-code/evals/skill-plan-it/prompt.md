---
description: "Atomic outcome eval for plan-it: inspects an unshaped feature request with conflicting requirements and a spec-vs-code contradiction, leaves ./repo untouched, surfaces the contradiction, and presents one focused decision with concrete trade-offs and a recommendation."
expected_outcome: "Reads plan-it/SKILL.md, inspects ./repo/docs/spec.md and ./repo/src/billing.py without modifying ./repo, surfaces the 72h vs 24h contradiction and request conflicts, presents one focused high-impact decision with walked trade-offs and a pick, and saves GRILLING.md under ASTACK_HOME/billing/architecture/ if pausing."
timeout_seconds: 360
---

`/astack:go` We want to shape the feature request in `program/request.md` for project `billing` before writing any code. Inspect `./repo` first, surface any contradictions between our docs, code, and request, and walk me through the highest-impact open decision with concrete trade-offs and your recommendation. Do not edit `./repo` yet; save the open decision tree and cost ledger snapshot outside the repo under `ASTACK_HOME` (`program/astack_home`) so we can resume after my answer.
