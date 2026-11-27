---
description: "Atomic outcome eval for blast-radius: audits a proposed return-type change to src/pricing.py:total_cents beyond direct grep hits, naming all 3 indirect callers (src/invoices.py, src/exports.py, and dynamically wired src/webhooks.py) with exact file:line citations and concrete failure modes while keeping ./repo clean."
expected_outcome: "Reads blast-radius/SKILL.md, evaluates program/proposed_change.patch against ./repo without editing ./repo, explicitly challenges the core safety assumption that only direct grep callers are impacted, identifies all 3 indirect callers (src/invoices.py, src/exports.py, src/webhooks.py including the dynamic registry lookup) with exact file:line citations and concrete TypeError/wire-schema failure modes in program/BLAST_RADIUS.md, and leaves ./repo clean."
timeout_seconds: 360
---

`/astack:go` A teammate proposed the change in `program/proposed_change.patch` to `./repo/src/pricing.py` (changing `total_cents` to return a breakdown dictionary instead of an integer), asserting that only direct callers matching `total_cents(` are affected. Audit the real blast radius across `./repo` without modifying `./repo`, and write your findings—including exact `file:line` citations and concrete failure modes for every indirect consumer—to `program/BLAST_RADIUS.md`.
