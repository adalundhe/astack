---
type: llm
---

Evaluate the workspace state and adversarial challenge against `challenge/SKILL.md`.

PASS if all of these hold:
- Leaves `./repo` untouched.
- Pins down the disk-I/O hypothesis and LRU file-cache proposal from `program/hypothesis.md` and exposes its false assumption directly against `src/search.py` (which performs zero disk, file, or network I/O).
- Identifies the true bottleneck: an O(n^2) / quadratic in-memory nested loop over `queries` and `catalog` (plus linear `any(...)` deduplication over `matches`).
- Proposes a concrete alternative (building a `dict` inverted index by lowercase SKU/tag plus a `set` of seen SKUs for O(n + m) execution) and closes with an explicit `Rejected` verdict / `decided:` record.

FAIL otherwise.
