"""Separated offline oracle for `skill-challenge`."""
from __future__ import annotations

from pathlib import Path

_CHALLENGE = """# Adversarial Challenge: Search Latency Diagnosis

## 1. Claim & Load-Bearing Assumptions
- **Claim:** `find_matching_items` slows down from 4 ms (200 items) to 1.4 s (4,000 items) due to slow disk I/O, so adding a 5-minute TTL LRU file cache in front of `src/search.py` will fix it.
- **Assumptions required:** (a) `src/search.py` reads files from disk during query execution; (b) caching catalog files in memory removes the quadratic latency jump.

## 2. Falsification & Evidence (Trust-Ladder Rung 4/5)
- Direct inspection of `repo/src/search.py` (`find_matching_items`, lines 7-20) shows **zero disk I/O, zero `open()` calls, and zero network calls** — the function operates strictly on in-memory Python lists and dicts.
- Adding an LRU file cache cannot speed up `find_matching_items` because there is no file I/O to cache, while adding stale-TTL complexity.

## 3. Actual Root Cause (Rival Hypothesis)
- `repo/src/search.py` runs an **O(n^2) in-memory nested loop**: for every query in `queries`, it linearly scans every item in `catalog`, rebuilds lowercased tag lists on every iteration, and performs an O(k) linear deduplication scan (`any(existing["sku"] == item["sku"] for existing in matches)`).
- Scaling input size 20x (200 -> 4,000) scales work ~400x, directly matching the observed 4 ms -> 1.4 s jump.

## 4. Concrete Alternative
- Build a pre-indexed `dict[str, list[dict]]` mapping lowercased SKUs and tags to catalog items in one O(catalog) pass, then resolve queries with O(1) dictionary lookups and a `seen_skus: set[str]` for O(1) deduplication — reducing total runtime to O(n + m).

## 5. Verdict
- **Verdict:** Rejected.
- `decided:` Reject the LRU file cache proposal; optimize `repo/src/search.py` with an in-memory `dict`/`set` inverted index after benchmark confirmation. `./repo` left untouched.
"""


def apply(ws: Path) -> dict[str, object]:
    out = ws / "program" / "CHALLENGE.md"
    out.write_text(_CHALLENGE, encoding="utf-8")
    return {"final_text": _CHALLENGE}
