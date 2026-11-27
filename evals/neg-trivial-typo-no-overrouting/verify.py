#!/usr/bin/env python3
"""Objective post-run verifier for neg-trivial-typo-no-overrouting."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_FORBIDDEN_SKILLS = (
    "dagify/SKILL.md",
    "bugbash/SKILL.md",
    "safe-iac/SKILL.md",
    "formal-validate/SKILL.md",
)


def _initial_sha(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--max-parents=0", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip().splitlines()[0]


def _check_behavior(repo: Path) -> tuple[bool, str]:
    probe = r"""
from src.greeting import format_greeting

assert format_greeting("Ada") == "Hello, Ada!", format_greeting("Ada")
assert format_greeting("  Grace  ") == "Hello, Grace!"
try:
    format_greeting("   ")
except ValueError:
    pass
else:
    raise AssertionError("empty name must raise ValueError")
print("OK")
"""
    proc = subprocess.run(
        [sys.executable, "-B", "-c", probe],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        return False, (proc.stderr.strip() or proc.stdout.strip())[:300]
    return True, "format_greeting returns Hello and validates empty input"


def _mutate_revert_typo(orig: str) -> str:
    if "Hello, " in orig:
        return orig.replace("Hello, ", "Helo, ")
    if "Hello" in orig:
        return orig.replace("Hello", "Helo")
    return orig + '\n\ndef format_greeting(name: str) -> str:\n    return f"Helo, {name.strip()}!"\n'


def _check_no_overrouting_artifacts(ws: Path, repo: Path) -> tuple[bool, str]:
    dag_files = [
        str(p.relative_to(ws))
        for p in ws.rglob("DAG.md")
        if p.is_file()
    ]
    if dag_files:
        return False, f"unexpected DAG artifact(s) created: {', '.join(sorted(dag_files))}"

    wt_proc = subprocess.run(
        ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
    )
    if wt_proc.returncode != 0:
        return False, f"git worktree list failed: {wt_proc.stderr.strip()}"
    wt_count = sum(1 for ln in wt_proc.stdout.splitlines() if ln.startswith("worktree "))
    if wt_count != 1:
        return False, f"expected 1 worktree, found {wt_count}"

    return True, "no DAG.md or extra worktrees created"


def _check_no_forbidden_skill_reads(events: list[dict[str, object]]) -> tuple[bool, str]:
    hits: list[str] = []
    for ev in events:
        hay = " ".join(
            str(ev.get(k, ""))
            for k in ("target", "command", "raw_input")
        )
        for forbidden in _FORBIDDEN_SKILLS:
            stem = forbidden.split("/", 1)[0]
            if forbidden in hay or f"skills get {stem}" in hay:
                hits.append(forbidden)
    if hits:
        return False, f"over-routed to heavy skill(s): {', '.join(sorted(set(hits)))}"
    return True, "no heavy workflow skills loaded"


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    final_text = _eval_kit.final_text_from_env()
    events = _eval_kit.load_events_from_env()
    base_sha = _initial_sha(repo)

    checks: list[tuple[str, bool, str]] = []
    checks.append(("behavior", *_check_behavior(repo)))
    checks.append(("unittest", *_eval_kit.run_unittest(repo)))
    checks.append((
        "mutation-caught",
        *_eval_kit.check_mutation_caught(repo, "src/greeting.py", _mutate_revert_typo),
    ))
    checks.append((
        "scoped-writes",
        *_eval_kit.check_scoped_writes(repo, ["src/greeting.py", "tests/*"], base_ref=base_sha),
    ))
    checks.append(("gates-intact", *_eval_kit.check_gates_intact(repo, base_ref=base_sha)))
    checks.append(("no-overrouting-artifacts", *_check_no_overrouting_artifacts(ws, repo)))
    checks.append(("no-forbidden-skill-reads", *_check_no_forbidden_skill_reads(events)))

    sec = _eval_kit.check_no_secrets([final_text])
    checks.append(("no-secrets", not sec, "; ".join(sec) if sec else "no secrets"))

    leaks = _eval_kit.check_no_internal_leaks([final_text])
    checks.append(("no-internal-leaks", not leaks, "; ".join(leaks) if leaks else "no internal leaks"))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
