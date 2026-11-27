#!/usr/bin/env python3
"""Executable verifier for `capstone-tlc-statechart-livelock`."""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_FORBIDDEN_BOOL_FIELDS = frozenset({"claiming", "running", "retrying", "timed_out"})
_REQUIRED_STATES = ("queued", "claimed", "running", "retry_wait", "completed", "dead_letter")

_BEHAVIOR_PROBE = r'''
import enum
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))
import coordinator as mod

# Verify Enum exists with DEAD_LETTER
enum_classes = [
    obj for obj in vars(mod).values()
    if isinstance(obj, type) and issubclass(obj, enum.Enum) and obj is not enum.Enum
]
assert enum_classes, "coordinator.py must define an explicit Enum state class"
all_member_names = {m.name.upper() for cls in enum_classes for m in cls}
assert "DEAD_LETTER" in all_member_names, f"Enum missing DEAD_LETTER: {all_member_names}"
assert "COMPLETED" in all_member_names, f"Enum missing COMPLETED: {all_member_names}"

# 1. Safety: timeout revokes w1 ownership; w2 cannot overlap with w1
c = mod.JobCoordinator(max_retries=3)
c.submit("j1")
assert c.claim("j1", "w1") is True
assert c.claim("j1", "w2") is False, "w2 must not claim while w1 holds CLAIMED"
assert c.start("j1", "w1") is True
assert len(c.active_workers("j1")) == 1
assert c.timeout("j1") is True
assert len(c.active_workers("j1")) == 0, f"timeout must revoke active workers, got {c.active_workers('j1')}"
assert c.retry("j1") is True
assert c.claim("j1", "w2") is True
assert c.start("j1", "w2") is True
assert c.active_workers("j1") == {"w2"}, f"expected only w2 active, got {c.active_workers('j1')}"
assert c.complete("j1", "w1") is False, "stale worker w1 must not complete w2's job"
assert c.fail("j1", "w1") is False, "stale worker w1 must not fail w2's job"
assert c.complete("j1", "w2") is True
assert len(c.active_workers("j1")) == 0
# Terminal state COMPLETED rejects all transitions
assert c.claim("j1", "w1") is False
assert c.timeout("j1") is False
assert c.retry("j1") is False

# 2. Liveness: repeated timeouts exhaust max_retries and reach DEAD_LETTER
c2 = mod.JobCoordinator(max_retries=2)
c2.submit("j2")
for attempt in range(2):
    assert c2.claim("j2", "w1") is True, f"claim failed on attempt {attempt + 1}"
    assert c2.start("j2", "w1") is True, f"start failed on attempt {attempt + 1}"
    assert c2.timeout("j2") is True, f"timeout failed on attempt {attempt + 1}"
    if attempt == 0:
        assert c2.retry("j2") is True, "first timeout should allow retry"

state_val = c2.get_state("j2")
state_name = state_val.name if isinstance(state_val, enum.Enum) else str(state_val)
assert "DEAD_LETTER" in state_name.upper(), f"expected DEAD_LETTER after exhausting max_retries, got {state_val!r}"
assert c2.retry("j2") is False, "DEAD_LETTER must not retry"
assert c2.claim("j2", "w2") is False, "DEAD_LETTER must not be claimed"
assert len(c2.active_workers("j2")) == 0

print("coordinator-ok")
'''


def _check_enum_and_no_booleans(coord_path: Path) -> tuple[bool, str]:
    if not coord_path.is_file():
        return False, "missing src/coordinator.py"
    text = coord_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename="src/coordinator.py")
    except SyntaxError as exc:
        return False, f"syntax error: {exc}"

    has_enum = False
    bool_hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if (isinstance(base, ast.Name) and "Enum" in base.id) or (
                    isinstance(base, ast.Attribute) and "Enum" in base.attr
                ):
                    has_enum = True
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id in _FORBIDDEN_BOOL_FIELDS:
                bool_hits.append(f"line {node.lineno}: {node.target.id}")
        elif isinstance(node, ast.Attribute) and node.attr in _FORBIDDEN_BOOL_FIELDS:
            bool_hits.append(f"line {node.lineno}: .{node.attr}")

    if not has_enum:
        return False, "src/coordinator.py missing explicit Enum subclass"
    if bool_hits:
        return False, f"overlapping boolean flag(s) still present: {', '.join(bool_hits[:6])}"
    return True, "explicit Enum state machine with zero overlapping boolean flags"


def _validate_counterexample(data: Any) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "counterexample.json must be a JSON object"
    raw = json.dumps(data).lower()

    # Accept either top-level safety/livelock sub-objects or a list of counterexamples/traces
    step_counts: list[int] = []
    for key in ("safety", "livelock", "liveness", "counterexamples", "traces", "steps", "trace"):
        val = data.get(key)
        if isinstance(val, list):
            if val and all(isinstance(x, dict) and isinstance(x.get("steps", x.get("trace")), list) for x in val):
                for entry in val:
                    step_counts.append(len(entry.get("steps", entry.get("trace"))))
            else:
                step_counts.append(len(val))
        elif isinstance(val, dict):
            sub_steps = val.get("steps", val.get("trace"))
            if isinstance(sub_steps, list):
                step_counts.append(len(sub_steps))

    has_safety = any(tok in raw for tok in ("dual", "two worker", "active_workers", "w1", "w2", "safety", "mutual"))
    has_livelock = any(tok in raw for tok in ("livelock", "liveness", "cycle", "dead_letter", "unbounded", "retry"))
    has_steps = any(n >= 3 for n in step_counts)

    if not (has_steps and has_safety and has_livelock):
        return (
            False,
            f"counterexample.json incomplete: has_steps(>=3)={has_steps} (counts={step_counts}), "
            f"has_safety={has_safety}, has_livelock={has_livelock}",
        )
    return True, f"counterexample.json captures safety + livelock traces (step counts={step_counts})"


def _validate_statechart(md_path: Path) -> tuple[bool, str]:
    if not md_path.is_file():
        return False, "missing program/STATES.md"
    text = md_path.read_text(encoding="utf-8", errors="replace")
    blocks = re.findall(r"```mermaid\s*\n(.*?)```", text, re.S | re.I)
    state_blocks = [b for b in blocks if re.search(r"^\s*stateDiagram-v2\b", b, re.M)]
    if not state_blocks:
        return False, "program/STATES.md missing fenced ```mermaid stateDiagram-v2 block"

    joined = "\n".join(state_blocks)
    low = joined.lower()
    missing = [s for s in _REQUIRED_STATES if s not in low]
    if missing:
        return False, f"stateDiagram-v2 missing state(s): {', '.join(missing)}"

    # Terminal states must not have outgoing edges to non-[*] states
    illegal: list[str] = []
    for line in joined.splitlines():
        s = line.strip()
        m = re.match(r"^([A-Za-z0-9_]+)\s*-->\s*(\[\*\]|[A-Za-z0-9_]+)", s)
        if m:
            src, dst = m.group(1).lower(), m.group(2).lower()
            if src in ("completed", "dead_letter") and dst != "[*]":
                illegal.append(f"{src} -> {dst}")
    if illegal:
        return False, f"illegal outgoing edge(s) from terminal state: {', '.join(illegal)}"

    edge_count = len(re.findall(r"-->", joined))
    if edge_count < 6:
        return False, f"stateDiagram-v2 has too few transitions ({edge_count} < 6)"
    return True, f"valid stateDiagram-v2 with all 6 states and {edge_count} transition(s)"


def _reinject_safety_bug(src: str) -> str:
    return (
        src
        + "\n\n_OrigJobCoordinatorSafety = JobCoordinator\n"
        + "class JobCoordinator(_OrigJobCoordinatorSafety):\n"
        + "    def __init__(self, *args, **kwargs):\n"
        + "        super().__init__(*args, **kwargs)\n"
        + "        self._mut_extra = {}\n"
        + "    def claim(self, job_id, worker_id):\n"
        + "        ok = super().claim(job_id, worker_id)\n"
        + "        if not ok:\n"
        + "            self._mut_extra.setdefault(job_id, set()).add(worker_id)\n"
        + "            return True\n"
        + "        return ok\n"
        + "    def active_workers(self, job_id):\n"
        + "        return set(super().active_workers(job_id)) | set(self._mut_extra.get(job_id, set()))\n"
    )


def _reinject_livelock_bug(src: str) -> str:
    return (
        src
        + "\n\n_OrigJobCoordinatorLivelock = JobCoordinator\n"
        + "class JobCoordinator(_OrigJobCoordinatorLivelock):\n"
        + "    def __init__(self, max_retries=3):\n"
        + "        super().__init__(max_retries=1000000)\n"
    )


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    checker = ws / "program" / "check_protocol.py"
    ce_path = ws / "program" / "counterexample.json"
    states_md = ws / "program" / "STATES.md"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("workspace-intact", False, f"missing ./repo at {repo}"))
        return _eval_kit.report_and_exit(checks)

    base_sha = (ws / "program" / "base_sha.txt").read_text(encoding="utf-8").strip()
    buggy_coord = subprocess.run(
        ["git", "-C", str(repo), "show", f"{base_sha}:src/coordinator.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    # 1. Explicit Enum + zero overlapping booleans
    enum_ok, enum_detail = _check_enum_and_no_booleans(repo / "src" / "coordinator.py")
    checks.append(("explicit-enum-no-booleans", enum_ok, enum_detail))

    # 2. Counterexample JSON
    raw_ce = ""
    if ce_path.is_file():
        raw_ce = ce_path.read_text(encoding="utf-8", errors="replace")
        try:
            ce_obj = json.loads(raw_ce)
        except json.JSONDecodeError as exc:
            checks.append(("counterexample-valid", False, f"invalid JSON: {exc}"))
        else:
            ok_ce, msg_ce = _validate_counterexample(ce_obj)
            checks.append(("counterexample-valid", ok_ce, msg_ce))
    else:
        checks.append(("counterexample-valid", False, "missing program/counterexample.json"))

    # 3. Mermaid stateDiagram-v2 in program/STATES.md
    sc_ok, sc_detail = _validate_statechart(states_md)
    checks.append(("mermaid-statechart-valid", sc_ok, sc_detail))

    # 4. Exhaustive BFS checker passes fixed code AND catches buggy root commit
    checker_text = ""
    if checker.is_file():
        checker_text = checker.read_text(encoding="utf-8", errors="replace")
        fixed_run = subprocess.run(
            [sys.executable, "-B", str(checker)],
            cwd=ws,
            capture_output=True,
            text=True,
            timeout=25,
        )
        checks.append((
            "protocol-checker-passes-fixed",
            fixed_run.returncode == 0,
            (fixed_run.stdout.strip().splitlines()[-1] if fixed_run.stdout.strip() else "exit 0")
            if fixed_run.returncode == 0
            else f"exit {fixed_run.returncode}: {(fixed_run.stderr.strip() or fixed_run.stdout.strip())[:220]}",
        ))

        coord_file = repo / "src" / "coordinator.py"
        fixed_src = coord_file.read_text(encoding="utf-8")
        try:
            coord_file.write_text(buggy_coord, encoding="utf-8")
            try:
                buggy_run = subprocess.run(
                    [sys.executable, "-B", str(checker)],
                    cwd=ws,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                buggy_caught = buggy_run.returncode != 0
                buggy_detail = (
                    f"buggy root model caught (exit {buggy_run.returncode})"
                    if buggy_caught
                    else "check_protocol.py exited 0 on buggy root commit (vacuous checker)"
                )
            except subprocess.TimeoutExpired:
                buggy_caught = True
                buggy_detail = "buggy root model caught via unbounded exploration timeout"
        finally:
            coord_file.write_text(fixed_src, encoding="utf-8")
        checks.append(("protocol-checker-catches-buggy-root", buggy_caught, buggy_detail))
    else:
        checks.append(("protocol-checker-passes-fixed", False, "missing program/check_protocol.py"))
        checks.append(("protocol-checker-catches-buggy-root", False, "missing program/check_protocol.py"))

    # 5. Direct safety + liveness probe
    probe = subprocess.run(
        [sys.executable, "-B", "-c", _BEHAVIOR_PROBE],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=15,
    )
    checks.append((
        "behavior-safety-and-liveness",
        probe.returncode == 0 and "coordinator-ok" in probe.stdout,
        "safety (<=1 active worker, terminal immutability) and liveness (DEAD_LETTER) verified"
        if (probe.returncode == 0 and "coordinator-ok" in probe.stdout)
        else (probe.stderr.strip() or probe.stdout.strip())[:240],
    ))

    # 6. Unit tests + 2 resilient mutations
    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    mut_s_ok, mut_s_detail = _eval_kit.check_mutation_caught(repo, "src/coordinator.py", _reinject_safety_bug)
    checks.append(("mutation-safety-caught", mut_s_ok, mut_s_detail))

    mut_l_ok, mut_l_detail = _eval_kit.check_mutation_caught(repo, "src/coordinator.py", _reinject_livelock_bug)
    checks.append(("mutation-livelock-caught", mut_l_ok, mut_l_detail))

    # 7. Gates + secrets + internal leaks
    gates_ok, gates_detail = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", gates_ok, gates_detail))

    states_text = states_md.read_text(encoding="utf-8", errors="replace") if states_md.is_file() else ""
    all_texts = [final_text, raw_ce, checker_text, states_text]
    sec_hits = _eval_kit.check_no_secrets(all_texts)
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks(all_texts)
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
