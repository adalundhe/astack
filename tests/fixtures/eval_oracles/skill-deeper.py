"""Separated offline oracle for `skill-deeper`."""
from __future__ import annotations

from pathlib import Path

REWRITTEN_BRIEF = """# Worker Brief: Fix `TTLCache` Eviction, Capacity Bound, and Monotonic Expiry

## Deliverable
Fix `TTLCache` in `repo/src/cache.py` so it enforces `max_entries` with O(1) LRU eviction, uses a monotonic clock for TTL expiry, and reports accurate live counts in `__len__`, backed by unit and reference-model tests in `repo/tests/test_cache.py`.

## Primary Material
- `repo/src/cache.py` (`TTLCache`): currently has five defects:
  1. `put()` never enforces `max_entries`, allowing unbounded memory growth.
  2. `evict_one()` calls `dict.popitem()` (LIFO: drops the newest entry instead of the least-recently-used oldest entry).
  3. `get()` does not refresh LRU recency order on hits.
  4. `put()` and `get()` use wall-clock `time.time()` instead of `time.monotonic()`, breaking TTLs across NTP/DST jumps.
  5. `__len__()` counts already-expired entries instead of purging/excluding them.
- `repo/tests/test_cache.py`: currently contains only one smoke test (`test_put_and_get`) that misses every defect above.

## Domain Methods and Tools
- Replace raw `dict` storage with `collections.OrderedDict` (`move_to_end(key)` on `get()`/`put()` updates, `popitem(last=False)` for O(1) LRU eviction).
- Inject a monotonic clock callable (`clock: Callable[[], float] = time.monotonic`) into `TTLCache.__init__` so expiry never depends on wall-clock time or real `time.sleep()` waits.
- Validate constructor and method boundaries (`max_entries >= 1`, `ttl_seconds > 0`, rejecting non-positive bounds with `ValueError`).

## Edge Cases (Expert Bar)
- Updating an existing key at full capacity (`len == max_entries`) overwrites and refreshes recency without evicting another key.
- Reading a key (`get()`) refreshes its recency so the untouched older key is evicted first when a new key arrives.
- Expired entries are purged before evicting live entries when at capacity, so a live entry is never evicted unnecessarily.
- Values equal to `None`, `0`, `False`, or `""` are stored and returned accurately (never confused with cache misses).
- `max_entries == 1`, zero/negative `max_entries` or `ttl_seconds`, and exact boundary expiry (`now >= expires_at`).

## External Proof
- Differential / reference-model check in `repo/tests/test_cache.py`: run a seeded randomized operation sequence (`put`, `get`, `evict_one`, `len`, clock advances via fake injected clock) against a simple brute-force reference oracle dictionary and assert identical return values, live membership, and sizes after every step.

## Flagged Unknowns (Resolve During Execution)
- Confirm whether `evict_one()` should purge expired keys before returning an evicted live key or return the oldest evicted key directly; document the chosen invariant in docstring and tests.

## Non-goals
- Do not add disk persistence, thread-locking, async APIs, external packages, or distributed cache backends.
- Do not change the public method names (`put`, `get`, `evict_one`, `__len__`).

## Writable paths
- `repo/src/cache.py`
- `repo/tests/test_cache.py`

## Done when
- `python3 -B -m unittest discover -s tests` exits 0 inside `./repo` with tests covering LRU eviction, `max_entries` enforcement, monotonic clock expiry, falsy values, boundary validation, and the seeded randomized reference-model comparison.
- `git -C repo diff --name-only` touches only `src/cache.py` and `tests/test_cache.py`.
"""


def apply(ws: Path) -> dict[str, object]:
    """Rewrite program/brief.md from primary inspection of ./repo/src/cache.py without editing ./repo."""
    (ws / "program" / "brief.md").write_text(REWRITTEN_BRIEF, encoding="utf-8")
    return {
        "final_text": (
            "Inspected `./repo/src/cache.py` and `./repo/tests/test_cache.py` and rewrote `program/brief.md` "
            "with concrete defects (`max_entries` bound, LIFO `popitem()` eviction, missing recency refresh, "
            "wall-clock `time.time()`, stale `__len__`), scoped writable paths, edge cases, non-goals, "
            "reference-model verification, and executable done-when checks. Left `./repo` untouched."
        ),
    }
