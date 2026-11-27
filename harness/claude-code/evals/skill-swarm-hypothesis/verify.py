#!/usr/bin/env python3
"""Executable verifier for `skill-swarm-hypothesis`."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _root_commit(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--max-parents=0", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip().splitlines()[0]


def _validate_swarm_report(data: Any) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "swarm_report.json is not a JSON object"
    raw = data.get("candidates", data.get("variants"))
    entries: list[tuple[str, dict[str, Any]]] = []
    if isinstance(raw, list):
        for idx, item in enumerate(raw):
            if isinstance(item, dict):
                entries.append((str(item.get("name", f"cand_{idx}")), item))
    elif isinstance(raw, dict):
        for name, item in raw.items():
            if isinstance(item, dict):
                entries.append((str(name), item))
    else:
        return False, "swarm_report.json missing 'candidates' list or dict"

    non_base: list[str] = []
    for name, item in entries:
        med = item.get("median_ms", item.get("p50_ms", item.get("mean_ms")))
        if not isinstance(med, (int, float)) or isinstance(med, bool) or float(med) <= 0:
            return False, f"candidate {name!r} missing positive timing (got {med!r})"
        if item.get("parity_verified") is not True:
            return False, f"candidate {name!r} parity_verified is not true"
        if name.lower() not in ("baseline", "base", "original"):
            non_base.append(name)

    if len(non_base) < 2:
        return False, f"expected >= 2 non-baseline candidates in swarm_report.json, got {non_base}"

    winner = data.get("winner")
    if not isinstance(winner, str) or not winner.strip():
        return False, "swarm_report.json missing non-empty 'winner'"

    return True, f"candidates={non_base}, winner={winner!r}, parity_verified=True"


def _verify_candidates_and_winner(
    repo: Path,
    cand_dir: Path,
    base_src: str,
    workload_path: Path,
) -> tuple[bool, str, bool, str]:
    cand_files = sorted(p for p in cand_dir.glob("*.py") if p.is_file() and not p.name.startswith("__"))
    if len(cand_files) < 2:
        cand_ok = False
        cand_msg = f"expected >= 2 candidate .py files in program/candidates/, found {len(cand_files)}"
    else:
        contents = {p.read_text(encoding="utf-8", errors="replace").strip() for p in cand_files}
        if len(contents) < 2:
            cand_ok = False
            cand_msg = "candidate files in program/candidates/ are identical duplicates"
        else:
            cand_ok = True
            cand_msg = f"{len(cand_files)} distinct candidate file(s): {[p.name for p in cand_files]}"

    probe = r'''
import importlib.util, json, statistics, sys, time, types
from pathlib import Path

repo = Path(sys.argv[1])
wl = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
cand_paths = [Path(p) for p in sys.argv[3:]]
base_src = sys.stdin.read()

edges = [(str(u), str(v), int(w)) for u, v, w in wl["edges"]]
pairs = [(str(s), str(d)) for s, d in wl["pairs"]]

base_mod = types.ModuleType("router_base")
exec(compile(base_src, "<base:src/router.py>", "exec"), base_mod.__dict__)

sys.path.insert(0, str(repo / "src"))
import router as curr_mod

base_out = base_mod.shortest_path_cost(edges, pairs)
curr_out = curr_mod.shortest_path_cost(edges, pairs)
assert curr_out == base_out, "landed router.py parity mismatch against baseline"

# Edge cases: zero-weight edge, unreachable, self, duplicate parallel edges
edge_cases_e = [("a", "b", 10), ("a", "b", 3), ("b", "c", 0), ("c", "a", 2)]
edge_cases_p = [("a", "c"), ("c", "b"), ("a", "a"), ("a", "missing")]
assert curr_mod.shortest_path_cost(edge_cases_e, edge_cases_p) == base_mod.shortest_path_cost(edge_cases_e, edge_cases_p)

checked_cands = 0
for cp in cand_paths:
    spec = importlib.util.spec_from_file_location(f"cand_{cp.stem}", cp)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, "shortest_path_cost", None)
    if callable(fn):
        got = fn(edges, pairs)
        assert got == base_out, f"candidate {cp.name} parity mismatch"
        checked_cands += 1

# Relative timing: warmup 1 + 3 alternating rounds
base_mod.shortest_path_cost(edges, pairs)
curr_mod.shortest_path_cost(edges, pairs)

base_ms, curr_ms = [], []
for r in range(3):
    order = ("base", "curr") if r % 2 == 0 else ("curr", "base")
    for side in order:
        fn = base_mod.shortest_path_cost if side == "base" else curr_mod.shortest_path_cost
        t0 = time.perf_counter()
        fn(edges, pairs)
        dt = (time.perf_counter() - t0) * 1000.0
        (base_ms if side == "base" else curr_ms).append(dt)

b_med = statistics.median(base_ms)
c_med = statistics.median(curr_ms)
print(json.dumps({
    "base_ms": b_med,
    "curr_ms": c_med,
    "speedup": b_med / c_med,
    "checked_cands": checked_cands,
}))
'''
    proc = subprocess.run(
        [sys.executable, "-B", "-c", probe, str(repo), str(workload_path), *(str(p) for p in cand_files)],
        input=base_src,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        err = (proc.stderr.strip() or proc.stdout.strip())[:240]
        return cand_ok, cand_msg, False, f"parity/speedup probe failed: {err}"
    info = json.loads(proc.stdout.strip())
    if cand_ok and int(info["checked_cands"]) < 2:
        cand_ok = False
        cand_msg = f"fewer than 2 candidate files defined callable shortest_path_cost (found {info['checked_cands']})"
    speedup = float(info["speedup"])
    perf_ok = speedup >= 2.0
    perf_msg = (
        f"parity verified; baseline={info['base_ms']:.2f}ms -> current={info['curr_ms']:.2f}ms "
        f"({speedup:.1f}x speedup, need >= 2.0x)"
    )
    return cand_ok, cand_msg, perf_ok, perf_msg


def _break_router(src: str) -> str:
    return (
        src
        + "\n\ndef shortest_path_cost(edges, pairs):\n"
        + "    return [None] * len(pairs)\n"
    )


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    cand_dir = ws / "program" / "candidates"
    workload = ws / "program" / "graph_workload.json"
    report_path = ws / "program" / "swarm_report.json"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir() or not workload.is_file():
        checks.append(("workspace-intact", False, "missing ./repo or program/graph_workload.json"))
        return _eval_kit.report_and_exit(checks)

    base_sha = _root_commit(repo)
    base_src = subprocess.run(
        ["git", "-C", str(repo), "show", f"{base_sha}:src/router.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    raw_report = ""
    if report_path.is_file():
        raw_report = report_path.read_text(encoding="utf-8", errors="replace")
        try:
            parsed = json.loads(raw_report)
        except json.JSONDecodeError as exc:
            checks.append(("swarm-report-valid", False, f"invalid JSON: {exc}"))
        else:
            ok_rep, rep_msg = _validate_swarm_report(parsed)
            checks.append(("swarm-report-valid", ok_rep, rep_msg))
    else:
        checks.append(("swarm-report-valid", False, "missing program/swarm_report.json"))

    scope_ok, scope_detail = _eval_kit.check_scoped_writes(
        repo, ["src/router.py", "tests/*"], base_ref=base_sha
    )
    checks.append(("no-extra-candidate-files-in-repo", scope_ok, scope_detail))

    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    cand_dir.mkdir(parents=True, exist_ok=True)
    cand_ok, cand_msg, perf_ok, perf_msg = _verify_candidates_and_winner(repo, cand_dir, base_src, workload)
    checks.append(("distinct-runnable-candidates", cand_ok, cand_msg))
    checks.append(("parity-and-relative-speedup", perf_ok, perf_msg))

    mut_ok, mut_detail = _eval_kit.check_mutation_caught(repo, "src/router.py", _break_router)
    checks.append(("mutation-caught", mut_ok, mut_detail))

    gates_ok, gates_detail = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", gates_ok, gates_detail))

    texts = [final_text, raw_report]
    sec_hits = _eval_kit.check_no_secrets(texts)
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks(texts)
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
