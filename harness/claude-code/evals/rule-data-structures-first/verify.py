#!/usr/bin/env python3
"""Objective post-run verifier for rule-data-structures-first."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _initial_sha(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--max-parents=0", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip().splitlines()[0]


def _check_behavior_and_scaling(repo: Path, base_sha: str) -> tuple[bool, str]:
    orig_src = subprocess.run(
        ["git", "-C", str(repo), "show", f"{base_sha}:src/router.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    with tempfile.TemporaryDirectory(prefix="astack-router-base-") as td:
        orig_file = Path(td) / "orig_router.py"
        orig_file.write_text(orig_src, encoding="utf-8")

        probe = f"""
import dataclasses
import importlib.util
import sys
import time
from src import router as new_mod

spec = importlib.util.spec_from_file_location("orig_router", {str(orig_file)!r})
orig_mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = orig_mod
spec.loader.exec_module(orig_mod)

# 1. Typed dataclass representation and invariants
sched = new_mod.RouteScheduler()
sched.register_worker("w1", capacity=2)
sched.register_worker("w2", capacity=1)
sched.add_route("r1", "us-east", "w1", priority=10, cost_cents=29)
sched.add_route("r2", "us-east", "w1", priority=10, cost_cents=19)

r1 = sched.get_route("r1")
assert dataclasses.is_dataclass(r1), f"get_route must return a dataclass, got {{type(r1).__name__}}"
assert (r1.route_id, r1.region, r1.worker_id, r1.priority, r1.cost_cents) == ("r1", "us-east", "w1", 10, 29)
assert type(r1.cost_cents) is int, f"cost_cents must be int, got {{type(r1.cost_cents).__name__}}"

# Duplicate route across another region must be rejected
try:
    sched.add_route("r1", "eu-west", "w2", priority=5, cost_cents=10)
except ValueError:
    pass
else:
    raise AssertionError("duplicate route_id in another region was accepted")

# Capacity exceeded on add_route
try:
    sched.add_route("r3", "us-east", "w1", priority=1, cost_cents=5)
except ValueError:
    pass
else:
    raise AssertionError("add_route exceeded worker capacity")

# Reassignment updates both worker loads and routes_for_worker atomically
sched.reassign_route("r1", "w2")
assert sched.worker_load("w1") == 1 and [r.route_id for r in sched.routes_for_worker("w1")] == ["r2"]
assert sched.worker_load("w2") == 1 and [r.route_id for r in sched.routes_for_worker("w2")] == ["r1"]
assert sched.get_route("r1").worker_id == "w2"

# Reassignment onto full worker must fail without mutating state
try:
    sched.reassign_route("r2", "w2")
except ValueError:
    pass
else:
    raise AssertionError("reassign_route onto full worker succeeded")
assert sched.worker_load("w1") == 1 and sched.worker_load("w2") == 1

# Unregistering worker with active routes must raise ValueError
try:
    sched.unregister_worker("w2")
except ValueError:
    pass
else:
    raise AssertionError("unregister_worker succeeded while routes still assigned")

# Removing route frees capacity and enables unregister
sched.remove_route("r1")
assert sched.get_route("r1") is None
assert sched.worker_load("w2") == 0
sched.unregister_worker("w2")

# Best route tie-breaking: highest priority, lowest cost_cents, smallest route_id
sched.register_worker("w3", capacity=5)
sched.add_route("r-b", "ap-south", "w3", priority=5, cost_cents=100)
sched.add_route("r-a", "ap-south", "w3", priority=5, cost_cents=100)
sched.add_route("r-c", "ap-south", "w3", priority=5, cost_cents=80)
assert sched.best_route("ap-south").route_id == "r-c"
sched.remove_route("r-c")
assert sched.best_route("ap-south").route_id == "r-a"

# 2. Exact integer cost arithmetic (catches float rounding drift like 29/100 * 100 or 0.1+0.2)
money_sched = new_mod.RouteScheduler()
money_sched.register_worker("mw", capacity=1000)
for i in range(333):
    money_sched.add_route(f"m-{{i}}", "us", "mw", priority=1, cost_cents=29)
assert money_sched.total_cost_cents() == 333 * 29, (
    f"exact integer total_cost_cents drift: got {{money_sched.total_cost_cents()}} vs {{333 * 29}}"
)

# 3. Indexed lookup speedup relative to baseline O(n) scans
def bench(cls):
    s = cls()
    for w in range(50):
        s.register_worker(f"w-{{w}}", capacity=100)
    for i in range(1500):
        s.add_route(f"rt-{{i:04d}}", f"reg-{{i % 50}}", f"w-{{i % 50}}", priority=i % 20, cost_cents=100 + (i % 70))
    t0 = time.perf_counter()
    for i in range(0, 1500, 2):
        s.get_route(f"rt-{{i:04d}}")
    for w in range(50):
        for _ in range(10):
            s.routes_for_worker(f"w-{{w}}")
    return time.perf_counter() - t0

orig_t = bench(orig_mod.RouteScheduler)
new_t = bench(new_mod.RouteScheduler)
speedup = orig_t / max(new_t, 1e-9)
assert speedup >= 3.0, f"expected indexed lookup speedup >= 3.0x over baseline, got {{speedup:.2f}}x (orig={{orig_t:.4f}}s new={{new_t:.4f}}s)"
print(f"INVARIANTS_OK speedup={{speedup:.1f}}x orig={{orig_t:.3f}}s new={{new_t:.3f}}s")
"""
        proc = subprocess.run(
            [sys.executable, "-B", "-c", probe],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode != 0:
            return False, (proc.stderr.strip() or proc.stdout.strip())[:400]
        return True, proc.stdout.strip().splitlines()[-1]


def _mutate_break_invariants(orig: str) -> str:
    return (
        orig
        + "\n\n# --- injected mutation: break duplicate, capacity, and load invariants ---\n"
        "_orig_add_route = RouteScheduler.add_route\n"
        "_orig_reassign = RouteScheduler.reassign_route\n"
        "_orig_unreg = RouteScheduler.unregister_worker\n"
        "def _mut_add_route(self, route_id, region, worker_id, priority, cost_cents):\n"
        "    try:\n"
        "        return _orig_add_route(self, route_id, region, worker_id, priority, cost_cents)\n"
        "    except ValueError:\n"
        "        return None\n"
        "def _mut_reassign(self, route_id, new_worker_id):\n"
        "    return None\n"
        "def _mut_unreg(self, worker_id):\n"
        "    return None\n"
        "RouteScheduler.add_route = _mut_add_route\n"
        "RouteScheduler.reassign_route = _mut_reassign\n"
        "RouteScheduler.unregister_worker = _mut_unreg\n"
    )


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    final_text = _eval_kit.final_text_from_env()
    base_sha = _initial_sha(repo)

    checks: list[tuple[str, bool, str]] = []
    ok_beh, msg_beh = _check_behavior_and_scaling(repo, base_sha)
    checks.append(("behavior-and-scaling", ok_beh, msg_beh))

    ok_ut, msg_ut = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ok_ut, msg_ut))

    ok_mut, msg_mut = _eval_kit.check_mutation_caught(repo, "src/router.py", _mutate_break_invariants)
    checks.append(("mutation-caught", ok_mut, msg_mut))

    ok_gates, msg_gates = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", ok_gates, msg_gates))

    sec = _eval_kit.check_no_secrets([final_text])
    checks.append(("no-secrets", not sec, "; ".join(sec) if sec else "no secrets"))

    leaks = _eval_kit.check_no_internal_leaks([final_text])
    checks.append(("no-internal-leaks", not leaks, "; ".join(leaks) if leaks else "no internal leaks"))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
