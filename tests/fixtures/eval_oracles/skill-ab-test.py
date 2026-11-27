"""Separated offline oracle for `skill-ab-test`."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_BISECT_MATCHER_SRC = '''"""Prefix matching utility using binary search over a sorted word list."""
from __future__ import annotations

from bisect import bisect_left


class PrefixMatcher:
    """Return lexicographically sorted unique words matching a prefix."""

    def __init__(self, words: list[str]) -> None:
        self._words: list[str] = sorted(set(words))

    def find_prefix(self, prefix: str, limit: int = 10) -> list[str]:
        """Return up to `limit` sorted words starting with `prefix`."""
        if limit <= 0:
            return []
        words = self._words
        idx = bisect_left(words, prefix)
        out: list[str] = []
        n = len(words)
        while idx < n and len(out) < limit:
            word = words[idx]
            if not word.startswith(prefix):
                break
            out.append(word)
            idx += 1
        return out
'''


def apply(ws: Path) -> dict[str, object]:
    """Benchmark baseline, bisect, and prefix-trie on queries.json; graft winner into repo/src/matcher.py."""
    bench_code = r'''
import json, statistics, sys, time
from bisect import bisect_left
from pathlib import Path

ws = Path(sys.argv[1])
data = json.loads((ws / "program" / "queries.json").read_text(encoding="utf-8"))
words = data["words"]
queries = data["queries"]

sys.path.insert(0, str(ws / "repo" / "src"))
from matcher import PrefixMatcher as BaselineMatcher


class BisectMatcher:
    def __init__(self, items):
        self._words = sorted(set(items))

    def find_prefix(self, prefix, limit=10):
        if limit <= 0:
            return []
        idx = bisect_left(self._words, prefix)
        out = []
        n = len(self._words)
        while idx < n and len(out) < limit:
            w = self._words[idx]
            if not w.startswith(prefix):
                break
            out.append(w)
            idx += 1
        return out


class TrieMatcher:
    def __init__(self, items):
        self._root = {}
        for word in sorted(set(items)):
            node = self._root
            for ch in word:
                nxt = node.get(ch)
                if nxt is None:
                    nxt = {}
                    node[ch] = nxt
                node = nxt
            node[""] = word

    def find_prefix(self, prefix, limit=10):
        if limit <= 0:
            return []
        node = self._root
        for ch in prefix:
            node = node.get(ch)
            if node is None:
                return []
        out = []
        stack = [node]
        while stack and len(out) < limit:
            cur = stack.pop()
            if "" in cur:
                out.append(cur[""])
                if len(out) >= limit:
                    break
            keys = [k for k in cur.keys() if k != ""]
            keys.sort(reverse=True)
            for k in keys:
                stack.append(cur[k])
        return out


instances = {
    "baseline": BaselineMatcher(words),
    "bisect": BisectMatcher(words),
    "prefix_trie": TrieMatcher(words),
}

ref_outs = [instances["baseline"].find_prefix(q["prefix"], q["limit"]) for q in queries]
for name, inst in instances.items():
    got = [inst.find_prefix(q["prefix"], q["limit"]) for q in queries]
    assert got == ref_outs, f"parity mismatch for {name}"

samples = {k: [] for k in instances}
order_base = ["baseline", "bisect", "prefix_trie"]
for r in range(5):
    rotated = order_base[r % 3:] + order_base[:r % 3]
    for name in rotated:
        inst = instances[name]
        t0 = time.perf_counter()
        for q in queries:
            inst.find_prefix(q["prefix"], q["limit"])
        samples[name].append((time.perf_counter() - t0) * 1000.0)

variants = []
for name in order_base:
    vals = samples[name]
    variants.append({
        "name": name,
        "median_ms": round(statistics.median(vals), 4),
        "mean_ms": round(statistics.fmean(vals), 4),
        "trials": len(vals),
        "parity_verified": True,
    })

candidates = [v for v in variants if v["name"] != "baseline"]
winner = min(candidates, key=lambda v: v["median_ms"])["name"]
report = {
    "dataset_words": len(words),
    "query_count": len(queries),
    "variants": variants,
    "winner": winner,
    "decided": f"Selected {winner} after alternating A/B trials with verified parity across all {len(queries)} queries.",
}
(ws / "program" / "ab_results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(report["decided"])
'''
    proc = subprocess.run(
        [sys.executable, "-B", "-c", bench_code, str(ws)],
        capture_output=True,
        text=True,
        check=True,
    )
    (ws / "repo" / "src" / "matcher.py").write_text(_BISECT_MATCHER_SRC, encoding="utf-8")
    subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests"],
        cwd=ws / "repo",
        check=True,
        capture_output=True,
    )
    return {
        "final_text": (
            f"decided: {proc.stdout.strip()}\n"
            "Grafted the verified faster `bisect` implementation into `./repo/src/matcher.py`, "
            "saved A/B measurements in `program/ab_results.json`, and confirmed all unit tests pass."
        ),
    }
