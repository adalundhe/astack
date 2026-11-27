#!/bin/bash
set -euo pipefail
mkdir -p program/candidates repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval User"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/router.py <<'EOF'
"""Weighted directed graph shortest-path router."""
from __future__ import annotations


def shortest_path_cost(
    edges: list[tuple[str, str, int]],
    pairs: list[tuple[str, str]],
) -> list[int | None]:
    """Compute minimum non-negative path cost for each (src, dst) pair, or None if unreachable."""
    nodes: set[str] = set()
    for u, v, _ in edges:
        nodes.add(u)
        nodes.add(v)

    results: list[int | None] = []
    for src, dst in pairs:
        if src == dst:
            results.append(0)
            continue
        if src not in nodes or dst not in nodes:
            results.append(None)
            continue
        # Naive Bellman-Ford scanning the entire unindexed edge list per query
        dist: dict[str, int] = {src: 0}
        for _ in range(len(nodes) - 1):
            updated = False
            for u, v, weight in edges:
                if u in dist:
                    cand = dist[u] + weight
                    if v not in dist or cand < dist[v]:
                        dist[v] = cand
                        updated = True
            if not updated:
                break
        results.append(dist.get(dst))
    return results
EOF

cat > repo/tests/test_router.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from router import shortest_path_cost


class RouterTest(unittest.TestCase):
    def test_shortest_path_prefers_lower_weight_multi_hop(self):
        edges = [
            ("a", "b", 10),
            ("a", "c", 2),
            ("c", "d", 3),
            ("d", "b", 2),
            ("b", "a", 1),
        ]
        got = shortest_path_cost(edges, [("a", "b"), ("a", "a"), ("b", "d"), ("a", "z")])
        self.assertEqual(got, [7, 0, 6, None])

    def test_disconnected_components(self):
        edges = [("n1", "n2", 4), ("n3", "n4", 5)]
        self.assertEqual(shortest_path_cost(edges, [("n1", "n2"), ("n1", "n4"), ("n4", "n3")]), [4, None, None])
EOF

python3 -B - <<'EOF'
import json
import random
from pathlib import Path

rng = random.Random(2026)
nodes = [f"n{i:03d}" for i in range(120)]
edges: list[list[object]] = []
# Connected backbone with extra random edges inside components 0..109, plus isolated cluster 110..119
for i in range(109):
    edges.append([nodes[i], nodes[i + 1], rng.randint(1, 20)])
for _ in range(320):
    u = rng.randrange(110)
    v = rng.randrange(110)
    if u != v:
        edges.append([nodes[u], nodes[v], rng.randint(1, 50)])
for i in range(110, 119):
    edges.append([nodes[i], nodes[i + 1], rng.randint(1, 10)])

pairs: list[list[str]] = [
    ["n000", "n109"],
    ["n000", "n115"],
    ["n050", "n050"],
]
sources = [rng.choice(nodes[:110]) for _ in range(10)]
for _ in range(37):
    pairs.append([rng.choice(sources), rng.choice(nodes)])

Path("program/graph_workload.json").write_text(
    json.dumps({"edges": edges, "pairs": pairs}, separators=(",", ":")),
    encoding="utf-8",
)
EOF

cat > program/goal.md <<'EOF'
# Architecture Exploration: Shortest-Path Router

`./repo/src/router.py:shortest_path_cost` currently runs an unindexed Bellman-Ford scan per query and is slow on `program/graph_workload.json`.

Goal:
1. Prototype at least two distinct algorithmic candidate architectures in `program/candidates/` (each as a separate `.py` file implementing `shortest_path_cost(edges, pairs)`), for example:
   - Binary-heap Dijkstra over a prebuilt adjacency list (optionally reusing per-source computations across shared sources)
   - Bidirectional Dijkstra over prebuilt forward and reverse adjacency lists
2. Benchmark the baseline and all candidate architectures on `program/graph_workload.json` using alternating trials with warmup and verify exact output parity across every query.
3. Save the comparison report to `program/swarm_report.json` with:
   - `candidates`: list or dict recording each candidate's `name`, `file`, `median_ms`, `mean_ms`, and `parity_verified: true`
   - `baseline_median_ms`: measured baseline timing
   - `winner`: chosen candidate name
   - `decided`: concise rationale citing the measured numbers
4. Land the winning implementation into `./repo/src/router.py`, keep `./repo` free of extra candidate files, and confirm unit tests pass.
EOF

git -C repo add .
git -C repo commit -q -m "initial naive router"
