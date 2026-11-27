---
type: llm
---

Evaluate the rewritten `program/brief.md` against `deeper`.

PASS if all of these hold:
- Leaves `./repo` completely untouched.
- Starts from primary repo inspection (`./repo/src/cache.py` and `./repo/tests/test_cache.py`) and identifies the real defects: unenforced `max_entries` size bound, LIFO `popitem()` eviction and missing LRU recency refresh in `get()`, wall-clock `time.time()` expiry, and `__len__` counting expired keys.
- Rewrites `program/brief.md` with concrete `Deliverable`, executable `Done when` command(s), scoped `Writable paths`, `Edge cases`, `Non-goals`, named domain methods/tools (e.g. `OrderedDict`, `time.monotonic`, injectable clock), and external/differential proof without expanding scope into distributed caching or unrequested features.

FAIL otherwise.
