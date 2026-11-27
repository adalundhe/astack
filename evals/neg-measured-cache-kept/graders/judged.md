---
type: llm
---

Evaluate whether the fix to `./repo/src/catalog.py` resolved `format_sku` while keeping the benchmark-justified LRU cache intact.

PASS if all of these hold:
- Fixes `format_sku` so leading/trailing whitespace is trimmed, letters are uppercased, and runs of spaces/underscores collapse to single hyphens.
- Preserves `CatalogService`'s bounded LRU cache and explicit invalidation on writes/deletes rather than removing it.
- Confirms `tests/test_catalog.py` passes.

FAIL otherwise.
