"""Separated offline oracle for `skill-swarm-hypothesis`."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_DIJKSTRA_HEAP_SRC = '''"""Candidate 1: Binary-heap Dijkstra with adjacency list and per-source caching."""
from __future__ import annotations

import heapq


def shortest_path_cost(
    edges: list[tuple[str, str, int]],
    pairs: list[tuple[str, str]],
) -> list[int | None]:
    """Compute minimum non-negative path cost for each (src, dst) pair using cached Dijkstra."""
    adj: dict[str, list[tuple[str, int]]] = {}
    nodes: set[str] = set()
    for u, v, w in edges:
        nodes.add(u)
        nodes.add(v)
        adj.setdefault(u, []).append((v, w))

    source_cache: dict[str, dict[str, int]] = {}

    def _run_from(src: str) -> dict[str, int]:
        cached = source_cache.get(src)
        if cached is not None:
            return cached
        dist: dict[str, int] = {src: 0}
        heap: list[tuple[int, str]] = [(0, src)]
        while heap:
            d, u = heapq.heappop(heap)
            if d > dist.get(u, -1):
                continue
            for v, w in adj.get(u, ()):
                nd = d + w
                prev = dist.get(v)
                if prev is None or nd < prev:
                    dist[v] = nd
                    heapq.heappush(heap, (nd, v))
        source_cache[src] = dist
        return dist

    results: list[int | None] = []
    for src, dst in pairs:
        if src == dst:
            results.append(0)
        elif src not in nodes or dst not in nodes:
            results.append(None)
        else:
            results.append(_run_from(src).get(dst))
    return results
'''

_BIDIRECTIONAL_SRC = '''"""Candidate 2: Bidirectional Dijkstra over forward and reverse adjacency lists."""
from __future__ import annotations

import heapq


def shortest_path_cost(
    edges: list[tuple[str, str, int]],
    pairs: list[tuple[str, str]],
) -> list[int | None]:
    """Compute minimum non-negative path cost for each (src, dst) pair using bidirectional Dijkstra."""
    fwd: dict[str, list[tuple[str, int]]] = {}
    rev: dict[str, list[tuple[str, int]]] = {}
    nodes: set[str] = set()
    for u, v, w in edges:
        nodes.add(u)
        nodes.add(v)
        fwd.setdefault(u, []).append((v, w))
        rev.setdefault(v, []).append((u, w))

    def _bidir(src: str, dst: str) -> int | None:
        dist_f: dict[str, int] = {src: 0}
        dist_b: dict[str, int] = {dst: 0}
        heap_f: list[tuple[int, str]] = [(0, src)]
        heap_b: list[tuple[int, str]] = [(0, dst)]
        best: int | None = None

        while heap_f and heap_b:
            if best is not None and heap_f[0][0] + heap_b[0][0] >= best:
                break
            if len(heap_f) <= len(heap_b):
                d, u = heapq.heappop(heap_f)
                if d > dist_f[u]:
                    continue
                for v, w in fwd.get(u, ()):
                    nd = d + w
                    if v not in dist_f or nd < dist_f[v]:
                        dist_f[v] = nd
                        heapq.heappush(heap_f, (nd, v))
                        if v in dist_b:
                            cand = nd + dist_b[v]
                            if best is None or cand < best:
                                best = cand
            else:
                d, u = heapq.heappop(heap_b)
                if d > dist_b[u]:
                    continue
                for v, w in rev.get(u, ()):
                    nd = d + w
                    if v not in dist_b or nd < dist_b[v]:
                        dist_b[v] = nd
                        heapq.heappush(heap_b, (nd, v))
                        if v in dist_f:
                            cand = nd + dist_f[v]
                            if best is None or cand < best:
                                best = cand
        return best

    results: list[int | None] = []
    for src, dst in pairs:
        if src == dst:
            results.append(0)
        elif src not in nodes or dst not in nodes:
            results.append(None)
        else:
            results.append(_bidir(src, dst))
    return results
'''


def apply(ws: Path) -> dict[str, object]:
    """Write two candidate architectures, benchmark with parity, and land winner into repo/src/router.py."""
    cand_dir = ws / "program" / "candidates"
    cand_dir.mkdir(parents=True, exist_ok=True)
    c1 = cand_dir / "dijkstra_heap.py"
    c2 = cand_dir / "bidirectional_dijkstra.py"
    c1.write_text(_DIJKSTRA_HEAP_SRC, encoding="utf-8")
    c2.write_text(_BIDIRECTIONAL_SRC, encoding="utf-8")

    bench = r'''
import importlib.util, json, statistics, sys, time
from pathlib import Path

ws = Path(sys.argv[1])
wl = json.loads((ws / "program" / "graph_workload.json").read_text(encoding="utf-8"))
edges = [(str(u), str(v), int(w)) for u, v, w in wl["edges"]]
pairs = [(str(s), str(d)) for s, d in wl["pairs"]]

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

base = _load("base_router", ws / "repo" / "src" / "router.py")
dijk = _load("dijkstra_heap", ws / "program" / "candidates" / "dijkstra_heap.py")
bidir = _load("bidirectional_dijkstra", ws / "program" / "candidates" / "bidirectional_dijkstra.py")

ref = base.shortest_path_cost(edges, pairs)
assert dijk.shortest_path_cost(edges, pairs) == ref
assert bidir.shortest_path_cost(edges, pairs) == ref

mods = {"baseline": base, "dijkstra_heap": dijk, "bidirectional_dijkstra": bidir}
samples = {k: [] for k in mods}
names = ["baseline", "dijkstra_heap", "bidirectional_dijkstra"]
for r in range(5):
    rot = names[r % 3:] + names[:r % 3]
    for name in rot:
        t0 = time.perf_counter()
        got = mods[name].shortest_path_cost(edges, pairs)
        samples[name].append((time.perf_counter() - t0) * 1000.0)
        assert got == ref

cands = []
for name, rel in (
    ("dijkstra_heap", "program/candidates/dijkstra_heap.py"),
    ("bidirectional_dijkstra", "program/candidates/bidirectional_dijkstra.py"),
):
    vals = samples[name]
    cands.append({
        "name": name,
        "file": rel,
        "median_ms": round(statistics.median(vals), 4),
        "mean_ms": round(statistics.fmean(vals), 4),
        "trials": len(vals),
        "parity_verified": True,
    })

winner_entry = min(cands, key=lambda c: c["median_ms"])
base_med = round(statistics.median(samples["baseline"]), 4)
report = {
    "baseline_median_ms": base_med,
    "candidates": cands,
    "winner": winner_entry["name"],
    "decided": f"{winner_entry['name']} won at {winner_entry['median_ms']}ms median vs baseline {base_med}ms with exact parity.",
}
(ws / "program" / "swarm_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(winner_entry["file"])
'''
    proc = subprocess.run(
        [sys.executable, "-B", "-c", bench, str(ws)],
        capture_output=True,
        text=True,
        check=True,
    )
    winner_rel = proc.stdout.strip().splitlines()[-1]
    winner_src = (ws / winner_rel).read_text(encoding="utf-8")
    (ws / "repo" / "src" / "router.py").write_text(winner_src, encoding="utf-8")

    subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests"],
        cwd=ws / "repo",
        check=True,
        capture_output=True,
    )
    return {
        "final_text": (
            f"Prototyped `dijkstra_heap.py` and `bidirectional_dijkstra.py` in `program/candidates/`, "
            f"benchmarked both with parity against the baseline in `program/swarm_report.json`, "
            f"and landed the faster winner (`{winner_rel}`) into `./repo/src/router.py`. All unit tests pass."
        ),
    }
