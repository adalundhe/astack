#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval User"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/matcher.py <<'EOF'
"""Prefix matching utility."""
from __future__ import annotations


class PrefixMatcher:
    """Return lexicographically sorted unique words matching a prefix."""

    def __init__(self, words: list[str]) -> None:
        self._words: list[str] = sorted(set(words))

    def find_prefix(self, prefix: str, limit: int = 10) -> list[str]:
        """Return up to `limit` sorted words starting with `prefix`."""
        if limit <= 0:
            return []
        matches = [word for word in self._words if word.startswith(prefix)]
        return matches[:limit]
EOF

cat > repo/tests/test_matcher.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from matcher import PrefixMatcher


class PrefixMatcherTest(unittest.TestCase):
    def setUp(self):
        self.matcher = PrefixMatcher(
            ["apple", "apricot", "application", "banana", "band", "apple", "cat"]
        )

    def test_basic_prefix_and_ordering(self):
        self.assertEqual(self.matcher.find_prefix("ap"), ["apple", "application", "apricot"])

    def test_limit_respected(self):
        self.assertEqual(self.matcher.find_prefix("ap", limit=2), ["apple", "application"])
        self.assertEqual(self.matcher.find_prefix("ap", limit=0), [])

    def test_empty_and_missing_prefix(self):
        self.assertEqual(self.matcher.find_prefix("", limit=3), ["apple", "application", "apricot"])
        self.assertEqual(self.matcher.find_prefix("zzz"), [])

    def test_exact_word_match(self):
        self.assertEqual(self.matcher.find_prefix("banana"), ["banana"])
EOF

python3 -B - <<'EOF'
import json
import random
from pathlib import Path

rng = random.Random(2026)
namespaces = ["auth", "billing", "catalog", "deploy", "events", "ledger", "metrics", "orders", "search", "users"]
actions = ["create", "delete", "fetch", "index", "list", "merge", "patch", "query", "sync", "verify"]
words_set: set[str] = set()
while len(words_set) < 8000:
    ns = rng.choice(namespaces)
    act = rng.choice(actions)
    suffix = rng.randint(0, 99999)
    words_set.add(f"{ns}.{act}.item_{suffix:05d}")
words = sorted(words_set)
rng.shuffle(words)

queries: list[dict[str, object]] = [
    {"prefix": "", "limit": 10},
    {"prefix": "zzz.nomatch", "limit": 10},
    {"prefix": words[0], "limit": 5},
    {"prefix": "auth.create.", "limit": 15},
]
for _ in range(396):
    sample = rng.choice(words)
    cut = rng.choice((4, 8, 12, 16, len(sample)))
    queries.append({"prefix": sample[:cut], "limit": rng.choice((5, 10, 20))})

Path("program/queries.json").write_text(
    json.dumps({"words": words, "queries": queries}, separators=(",", ":")),
    encoding="utf-8",
)
EOF

cat > program/ab_brief.md <<'EOF'
# A/B Test Brief: Prefix Matcher Optimization

`./repo/src/matcher.py` performs an O(N) scan across all words on every `find_prefix` call.

Task:
1. Prototype and benchmark at least two distinct faster implementations (for example, `bisect` binary search over sorted words vs a prefix trie) alongside the baseline on `program/queries.json`.
2. Run alternating rounds with warmup and verify exact output parity across every query (including empty prefix, missing prefix, exact word, and limit=0).
3. Save the comparison in `program/ab_results.json` containing:
   - `variants`: list or dict recording the benchmarked variants (at least 2 candidate variants beyond baseline), each with `name`, `median_ms`, `mean_ms`, and `parity_verified: true`
   - `winner`: name of the fastest verified variant
   - `decided`: short summary with measured numbers
4. Graft only the verified winning implementation into `./repo/src/matcher.py`, remove any losing variant files from `./repo`, and confirm `python3 -B -m unittest discover -s tests` passes.
EOF

git -C repo add .
git -C repo commit -q -m "initial prefix matcher"
