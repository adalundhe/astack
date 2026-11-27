#!/usr/bin/env python3
"""Objective post-run verifier for skill-simplify-me."""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_CEREMONY_CLASSES = frozenset({
    "ConfigAdapter",
    "AbstractBaseFormatter",
    "StrategyRegistry",
    "FormatterFactory",
    "FormatterProxyWrapper",
})

_BEHAVIOR_PROBE = r'''
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from src.report import render_report

rows = [
    {"id": 1, "name": "Alpha, Inc.", "total": 1200},
    {"id": 2, "name": 'Beta "Labs"', "total": 3400},
]
assert render_report(rows, fmt="csv", include_header=True) == 'id,name,total\n1,"Alpha, Inc.",1200\n2,"Beta ""Labs""",3400\n'
assert render_report(rows[:1], fmt="CSV", include_header=False) == '1,"Alpha, Inc.",1200\n'
assert render_report([], fmt="csv") == ""
assert render_report([{"z": 1, "a": 2}], fmt="json") == '[{"a": 2, "z": 1}]'
assert render_report([], fmt="json") == "[]"
try:
    render_report(rows, fmt="xml")
    raise AssertionError("expected ValueError for unknown fmt")
except ValueError:
    pass
print("OK")
'''


def _code_metrics(src: str) -> tuple[int, list[str]]:
    nonempty = sum(1 for ln in src.splitlines() if ln.strip() and not ln.strip().startswith("#"))
    tree = ast.parse(src)
    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    return nonempty, classes


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    base_sha_file = ws / "program" / "base_sha.txt"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir() or not base_sha_file.is_file():
        checks.append(("workspace-intact", False, "missing repo or program/base_sha.txt"))
        return _eval_kit.report_and_exit(checks)

    base_sha = base_sha_file.read_text(encoding="utf-8").strip()
    orig_src = subprocess.run(
        ["git", "-C", str(repo), "show", f"{base_sha}:src/report.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    orig_lines, orig_classes = _code_metrics(orig_src)

    report_py = repo / "src" / "report.py"
    if not report_py.is_file():
        checks.append(("report-py-exists", False, "src/report.py missing"))
        return _eval_kit.report_and_exit(checks)

    cur_src = report_py.read_text(encoding="utf-8")
    cur_lines, cur_classes = _code_metrics(cur_src)
    remaining_ceremony = sorted(_CEREMONY_CLASSES & set(cur_classes))

    lines_reduced = cur_lines <= max(50, int(orig_lines * 0.45))
    classes_reduced = len(cur_classes) <= 1 and not remaining_ceremony
    checks.append((
        "measurable-simplification",
        lines_reduced and classes_reduced,
        f"code lines: {orig_lines} -> {cur_lines}, classes: {len(orig_classes)} -> {len(cur_classes)} (remaining ceremony={remaining_ceremony})",
    ))

    probe = subprocess.run(
        [sys.executable, "-B", "-c", _BEHAVIOR_PROBE],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=15,
    )
    checks.append((
        "external-behavior-preserved",
        probe.returncode == 0,
        "render_report CSV/JSON/empty/error edge cases verified"
        if probe.returncode == 0
        else (probe.stderr.strip() or probe.stdout.strip())[:240],
    ))

    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    mut_ok, mut_detail = _eval_kit.check_mutation_caught(
        repo,
        "src/report.py",
        lambda s: s + "\ndef render_report(rows, fmt='csv', include_header=True):\n    return ''\n",
    )
    checks.append(("mutation-caught", mut_ok, mut_detail))

    gates_ok, gates_detail = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", gates_ok, gates_detail))

    sec_hits = _eval_kit.check_no_secrets([final_text])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([final_text])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
