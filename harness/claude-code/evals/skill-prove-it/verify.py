#!/usr/bin/env python3
"""Executable verifier for `skill-prove-it`."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_CSV_BEHAVIOR_PROBE = r'''
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))
from csv_stream import parse_csv, parse_csv_line

assert parse_csv_line('1,"he said ""hi""",ok') == ["1", 'he said "hi"', "ok"]
assert parse_csv_line('""""') == ['"']
assert parse_csv_line('"a""b""c","x, ""y""",z') == ['a"b"c', 'x, "y"', "z"]
assert parse_csv_line('a,"",b') == ["a", "", "b"]
assert parse_csv_line('1,"Ada, Lovelace",London') == ["1", "Ada, Lovelace", "London"]
assert parse_csv('k,v\n1,"say ""go"""\n') == [["k", "v"], ["1", 'say "go"']]
print("OK")
'''


def _root_commit(repo: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--max-parents=0", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip().splitlines()[0]


def _run_repro(script: Path, ws: Path) -> subprocess.CompletedProcess[str]:
    if script.suffix == ".sh":
        cmd = ["bash", str(script)]
    else:
        cmd = [sys.executable, "-B", str(script)]
    return subprocess.run(cmd, cwd=ws, capture_output=True, text=True, timeout=20)


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    astack_home = _eval_kit.astack_home_from_env(ws)
    repros_dir = astack_home / "etl" / "repros"
    reviews_dir = astack_home / "etl" / "reviews"
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("workspace-intact", False, "missing ./repo"))
        return _eval_kit.report_and_exit(checks)

    base_sha = _root_commit(repo)
    buggy_csv = subprocess.run(
        ["git", "-C", str(repo), "show", f"{base_sha}:src/csv_stream.py"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    repro_scripts = sorted(
        p for p in (repros_dir.rglob("*") if repros_dir.is_dir() else [])
        if p.is_file() and p.suffix in (".py", ".sh") and not p.name.startswith(".")
    )
    if not repro_scripts:
        checks.append(("repro-script-exists", False, f"no .py/.sh repro script under {repros_dir}"))
        checks.append(("repro-passes-on-fixed-repo", False, "missing repro script"))
        checks.append(("repro-fails-on-root-commit", False, "missing repro script"))
    else:
        checks.append((
            "repro-script-exists",
            True,
            f"found {len(repro_scripts)} script(s): {[p.name for p in repro_scripts]}",
        ))
        passed_script: Path | None = None
        last_fixed_err = ""
        for script in repro_scripts:
            proc = _run_repro(script, ws)
            if proc.returncode == 0:
                passed_script = script
                break
            last_fixed_err = f"{script.name} exit {proc.returncode}: {(proc.stderr.strip() or proc.stdout.strip())[:160]}"
        checks.append((
            "repro-passes-on-fixed-repo",
            passed_script is not None,
            f"{passed_script.name} exited 0 on fixed repo" if passed_script else last_fixed_err,
        ))

        if passed_script is not None:
            csv_file = repo / "src" / "csv_stream.py"
            fixed_csv = csv_file.read_text(encoding="utf-8")
            try:
                csv_file.write_text(buggy_csv, encoding="utf-8")
                buggy_proc = _run_repro(passed_script, ws)
            finally:
                csv_file.write_text(fixed_csv, encoding="utf-8")
            checks.append((
                "repro-fails-on-root-commit",
                buggy_proc.returncode != 0,
                f"{passed_script.name} failed on buggy root commit (exit {buggy_proc.returncode})"
                if buggy_proc.returncode != 0
                else f"{passed_script.name} exited 0 even on buggy root commit (vacuous repro)",
            ))
        else:
            checks.append(("repro-fails-on-root-commit", False, "skipped because repro did not pass on fixed repo"))

    review_files = sorted(
        p for p in (reviews_dir.rglob("*") if reviews_dir.is_dir() else [])
        if p.is_file() and not p.name.startswith(".")
    )
    non_empty_review_texts: list[str] = []
    for rf in review_files:
        txt = rf.read_text(encoding="utf-8", errors="replace").strip()
        if txt:
            non_empty_review_texts.append(txt)
    total_review_chars = sum(len(t) for t in non_empty_review_texts)
    checks.append((
        "raw-review-proof-artifacts",
        len(non_empty_review_texts) >= 1 and total_review_chars >= 40,
        f"{len(non_empty_review_texts)} non-empty file(s) ({total_review_chars} chars) under etl/reviews/"
        if non_empty_review_texts
        else f"no non-empty proof output files found under {reviews_dir}",
    ))

    probe = subprocess.run(
        [sys.executable, "-B", "-c", _CSV_BEHAVIOR_PROBE],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=15,
    )
    checks.append((
        "csv-escaped-quote-behavior",
        probe.returncode == 0,
        "RFC-4180 escaped quotes preserved"
        if probe.returncode == 0
        else (probe.stderr.strip() or probe.stdout.strip())[:220],
    ))

    ut_ok, ut_detail = _eval_kit.run_unittest(repo)
    checks.append(("unittest", ut_ok, ut_detail))

    mut_ok, mut_detail = _eval_kit.check_mutation_caught(repo, "src/csv_stream.py", lambda _: buggy_csv)
    checks.append(("mutation-caught-by-tests", mut_ok, mut_detail))

    gates_ok, gates_detail = _eval_kit.check_gates_intact(repo, base_ref=base_sha)
    checks.append(("gates-intact", gates_ok, gates_detail))

    texts = [final_text, *non_empty_review_texts]
    for script in repro_scripts:
        texts.append(script.read_text(encoding="utf-8", errors="replace"))
    sec_hits = _eval_kit.check_no_secrets(texts)
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks(texts)
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
