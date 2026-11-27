---
description: "Negative control: fixing an unrelated SKU formatting bug in ./repo/src/catalog.py preserves the measured bounded LRU cache documented in docs/cache_benchmark.md instead of blindly removing it."
expected_outcome: "Fixes format_sku in src/catalog.py, keeps tests passing, and preserves CatalogService's bounded LRU cache hit reuse and write/delete invalidation."
timeout_seconds: 240
---

`/astack:go` Fix `format_sku` in `./repo/src/catalog.py` so leading and trailing whitespace is trimmed, letters are uppercased, and runs of spaces or underscores become single hyphens (`-`). Ensure `./repo/tests/` passes.
