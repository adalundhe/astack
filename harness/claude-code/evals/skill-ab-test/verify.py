#!/usr/bin/env python3
"""Executable verifier for `skill-ab-test`."""
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


def _parse_variants(data: Any) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "ab_results.json is not a JSON object"
    raw = data.get("variants")
    entries: list[tuple[str, dict[str, Any]]] = []
    if isinstance(raw, list):
        for idx, item in enumerate(raw):
            if isinstance(item, dict):
                name = str(item.get("name", f"variant_{idx}"))
                entries.append((name, item))
    elif isinstance(raw, dict):
        for name, item in raw.items():
            if isinstance(item, dict):
                entries.append((str(name), item))
    else:
        return False, "ab_results.json missing 'variants' list or dict"

    non_base: list[str] = []
    for name, item in entries:
        med = item.get("median_ms", item.get("p50_ms", item.get("mean_ms")))
        if not isinstance(med, (int, float)) or isinstance(med, bool) or float(med) <= 0:
            return False, f"variant {name!r} missing positive timing (got {med!r})"
        if item.get("parity_verified") is not True:
            return False, f"variant {name!r} parity_verified is not true"
        if name.lower() not in ("baseline", "base", "original"):
            non_base.append(name)

    if len(non_base) < 2:
        return False, f"expected >= 2 non-baseline variants in ab_results.json, found {non_base}"

    winner = data.get("winner")
    if not isinstance(winner, str) or not winner.strip():
        return False, "ab_results.json missing non-empty 'winner'"

    return True, f"variants={non_base}, winner={winner!r}, all parity_verified=True"


def _verify_parity_and_speedup(repo: Path, base_src: str, queries_path: Path) -> tuple[bool, str]:
    probe = r'''
import json, statistics, sys, time, types
from pathlib import Path

repo = Path(sys.argv[1])
queries_data = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
base_src = sys.stdin.read()

base_mod = types.ModuleType("matcher_base")
exec(compile(base_src, "<base:src/matcher.py>", "exec"), base_mod.__dict__)

sys.path.insert(0, str(repo / "src"))
import matcher as curr_mod

words = queries_data["words"]
queries = queries_data["queries"]

# Edge cases + full workload parity
edge_words = ["", "a", "ab", "abc", "ab", "b", "ba"]
b_edge = base_mod.PrefixMatcher(edge_words)
c_edge = curr_mod.PrefixMatcher(edge_words)
for pfx in ("", "a", "ab", "abc", "b", "z"):
    for lim in (0, 1, 2, 10):
        got_b = b_edge.find_prefix(pfx, limit=lim)
        got_c = c_edge.find_prefix(pfx, limit=lim)
        assert got_c == got_b, f"edge mismatch for ({pfx!r}, {lim}): {got_c} != {got_b}"

bm = base_mod.PrefixMatcher(words)
cm = curr_mod.PrefixMatcher(words)

base_outs = [bm.find_prefix(q["prefix"], q["limit"]) for q in queries]
curr_outs = [cm.find_prefix(q["prefix"], q["limit"]) for q in queries]
assert curr_outs == base_outs, "workload parity mismatch against baseline"

# Alternating relative timing (warmup 1 + 3 measured rounds)
for _ in range(1):
    for q in queries:
        bm.find_prefix(q["prefix"], q["limit"])
        cm.find_prefix(q["prefix"], q["limit"])

base_ms, curr_ms = [], []
for r in range(3):
    order = ("base", "curr") if r % 2 == 0 else ("curr", "base")
    for side in order:
        inst = bm if side == "base" else cm
        t0 = time.perf_counter()
        for q in queries:
            inst.find_prefix(q["prefix"], q["limit"])
        dt = (time.perf_counter() - t0) * 1000.0
        (base_ms if side == "base" else curr_ms).append(dt)

b_med = statistics.median(base_ms)
c_med = statistics.median(curr_ms)
print(json.dumps({"base_ms": b_med, "curr_ms": c_med, "speedup": b_med / c_med}))
'''
    proc = subprocess.run(
        [sys.executable, "-B", "-c", probe, str(repo), str(queries_path)],
        input=base_src,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        err = (proc.stderr.strip() or proc.stdout.strip())[:240]
        return False, f"parity/speedup probe failed: {err}"
    info = json.loads(proc.stdout.strip())
    speedup = float(info["speedup"])
    ok = speedup >= 2.0
    return ok, (
        f"parity verified; baseline={info['base_ms']:.2f}ms -> current={info['curr_ms']:.2f}ms "
        f"({speedup:.1f}x speedup, need >= 2.0x)"
    )


def _break_matcher(src: str) -> str:
    return (
        src
        + "\n\n_OrigPrefixMatcher = PrefixMatcher\n"
        + "class PrefixMatcher(_OrigPrefixMatcher):\n"
        + "    def find_prefix(self, prefix: str, limit: int = 10) -> list[str]:\n"
        + "        return []\n"
    )


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    queries = ws / "program" / "queries.json"
    ab_results = ws / "program" / "ab_results.json"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir() or not queries.is_file():
        checks.append(("workspace-intact", False, "missing ./repo or program/queries.json"))
        return _eval_kit.report_and_exit(checks)

    base_sha = _root_commit(repo)
    base_src = subprocess.run(
        ["git", "-C", str(repo), "show", f"{base_sha}:src/matcher.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    raw_results = ""
    if ab_results.is_file():
        raw_results = ab_results.read_text(encoding="utf-8", errors="replace")
        try:
            parsed = json.loads(raw_results)
        except json.JSONDecodeError as exc:
            checks.append(("ab-results-valid", False, f"invalid JSON: {exc}"))
        else:
            ok_v, v_detail = _parse_variants(parsed)
            checks.append(("ab-results-valid", ok_v, v_detail))
    else:
        checks.append(("ab-results-valid", False, "missing program/ab_results.json"))

    scope_ok, scope_detail = _eval_kit.check_scoped_writes(
        repo, ["src/matcher.py", "tests/*"], base_ref=base_sha
    )
    checks.append(("no-losing-variants-left-in-repo", scope_ok, scope_detail))

    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    perf_ok, perf_detail = _verify_parity_and_speedup(repo, base_src, queries)
    checks.append(("parity-and-relative-speedup", perf_ok, perf_detail))

    mut_ok, mut_detail = _eval_kit.check_mutation_caught(repo, "src/matcher.py", _break_matcher)
    checks.append(("mutation-caught", mut_ok, mut_detail))

    gates_ok, gates_detail = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", gates_ok, gates_detail))

    texts = [final_text, raw_results]
    sec_hits = _eval_kit.check_no_secrets(texts)
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks(texts)
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
