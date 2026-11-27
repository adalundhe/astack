#!/usr/bin/env python3
"""Verifier for rule-yagni."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit as kit

RETIRED_SYMBOLS = ("parse_v1", "ENABLE_LEGACY_MODE", "parse_records", "legacy_compat")


def _base_ref(ws: Path, repo: Path) -> str:
    sha_file = ws / "program" / "base_sha.txt"
    if not sha_file.is_file():
        return "HEAD"
    base = sha_file.read_text(encoding="utf-8").strip()
    cur = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True)
    if cur.returncode == 0 and cur.stdout.strip() != base:
        return base
    return "HEAD"


BEHAVIOR_PROBE = """
import inspect, sys
sys.path.insert(0, "src")
import parser as record_parser
import importer
import report

for sym in ("parse_v1", "ENABLE_LEGACY_MODE", "parse_records"):
    assert not hasattr(record_parser, sym), f"retired symbol {sym} still exported on parser"

sig = inspect.signature(record_parser.parse_csv)
assert "legacy_compat" not in sig.parameters, f"unused legacy_compat param remains: {sig}"

sample = 'name,region,amount\\n"Doe, Jane",west,100\\n"Smith, Bob",west,50\\n"Lee, Amy",east,75\\n'
rows = record_parser.parse_csv(sample)
assert len(rows) == 3 and rows[0]["name"] == "Doe, Jane" and rows[0]["region"] == "west", rows
assert importer.load_records(sample) == rows
assert importer.import_contacts(sample) == [
    ("Doe, Jane", "west"),
    ("Smith, Bob", "west"),
    ("Lee, Amy", "east"),
]
assert report.summarize_by_region(sample) == {"east": 75, "west": 150}
print("yagni-behavior-ok")
"""


def _mutate_naive_split(src: str) -> str:
    return (
        src
        + "\ndef parse_csv(raw):\n"
        + "    lines = [ln for ln in raw.strip().splitlines() if ln.strip()]\n"
        + "    if not lines: return []\n"
        + "    hdr = [h.strip() for h in lines[0].split(',')]\n"
        + "    return [dict(zip(hdr, [p.strip() for p in ln.split(',')])) for ln in lines[1:]]\n"
    )


def main() -> int:
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    repo = ws / "repo"
    checks: list[tuple[str, bool, str]] = []

    # 1. Zero retired symbols anywhere in src/ or tests/
    leftovers: list[str] = []
    for folder in (repo / "src", repo / "tests"):
        for py_file in sorted(folder.glob("*.py")):
            text = py_file.read_text(encoding="utf-8")
            for sym in RETIRED_SYMBOLS:
                if re.search(rf"\b{re.escape(sym)}\b", text):
                    leftovers.append(f"{py_file.relative_to(repo)}:{sym}")
    checks.append((
        "zero_legacy_symbols",
        not leftovers,
        "none remaining" if not leftovers else f"retired symbols left behind: {', '.join(leftovers)}",
    ))

    # 2. All consumers work on unified parse_csv path including quoted commas
    probe = subprocess.run(
        [sys.executable, "-B", "-c", BEHAVIOR_PROBE],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    checks.append((
        "unified_path_behavior",
        probe.returncode == 0 and "yagni-behavior-ok" in probe.stdout,
        probe.stdout.strip() or probe.stderr.strip(),
    ))

    ok_ut, msg_ut = kit.run_unittest(repo)
    checks.append(("unittest", ok_ut, msg_ut))

    # 3. Reverting parse_csv to naive split must fail tests
    ok_mut, msg_mut = kit.check_mutation_caught(repo, "src/parser.py", _mutate_naive_split)
    checks.append(("mutation_caught", ok_mut, msg_mut))

    ok_gates, msg_gates = kit.check_gates_intact(repo, base_ref=_base_ref(ws, repo))
    checks.append(("gates_intact", ok_gates, msg_gates))

    final_text = kit.final_text_from_env()
    sec = kit.check_no_secrets([final_text])
    checks.append(("no_secrets", not sec, "; ".join(sec) if sec else "ok"))
    leaks = kit.check_no_internal_leaks([final_text])
    checks.append(("no_internal_leaks", not leaks, "; ".join(leaks) if leaks else "ok"))

    return kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
