#!/usr/bin/env python3
"""Verifier for rule-technical-writing."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit as kit

FLUFF_RE = re.compile(r"\b(blazing fast|seamless|robust)\b", re.I)


def _base_ref(ws: Path, repo: Path) -> str:
    sha_file = ws / "program" / "base_sha.txt"
    if not sha_file.is_file():
        return "HEAD"
    base = sha_file.read_text(encoding="utf-8").strip()
    cur = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True)
    if cur.returncode == 0 and cur.stdout.strip() != base:
        return base
    return "HEAD"


def _run_cli(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(repo / "src" / "export_cli.py"), *args],
        cwd=repo,
        capture_output=True,
        text=True,
    )


def _audit_doc(label: str, text: str) -> tuple[bool, str]:
    issues: list[str] = []
    if "--format" in text:
        issues.append("stale --format reference remains")
    if "--output" not in text:
        issues.append("missing --output documentation")
    if "jsonl" not in text.lower():
        issues.append("missing jsonl default/value documentation")
    fluff = FLUFF_RE.findall(text)
    if fluff:
        issues.append(f"marketing fluff remains: {sorted(set(f.lower() for f in fluff))}")
    if issues:
        return False, f"{label}: {'; '.join(issues)}"
    return True, f"{label}: synced to --output/jsonl with zero stale flags or fluff"


def main() -> int:
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    repo = ws / "repo"
    checks: list[tuple[str, bool, str]] = []

    with tempfile.TemporaryDirectory(prefix="astack-techwrite-") as td:
        sample = Path(td) / "sample.csv"
        sample.write_text("id,name\n1,Alice\n2,Bob\n", encoding="utf-8")

        # 1. Default output is jsonl
        p_def = _run_cli(repo, "--input", str(sample))
        def_rows = []
        def_ok = False
        if p_def.returncode == 0:
            lines = [ln for ln in p_def.stdout.splitlines() if ln.strip()]
            try:
                def_rows = [json.loads(ln) for ln in lines]
                def_ok = def_rows == [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]
            except json.JSONDecodeError:
                def_ok = False
        checks.append(("cli_default_jsonl", def_ok, f"rc={p_def.returncode} rows={def_rows!r}"))

        # 2. Explicit --output json and --output csv work
        p_json = _run_cli(repo, "--input", str(sample), "--output", "json")
        json_ok = False
        if p_json.returncode == 0:
            try:
                json_ok = json.loads(p_json.stdout) == [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]
            except json.JSONDecodeError:
                json_ok = False
        checks.append(("cli_output_json", json_ok, f"rc={p_json.returncode}"))

        p_csv = _run_cli(repo, "--input", str(sample), "--output", "csv")
        csv_ok = p_csv.returncode == 0 and p_csv.stdout.strip().splitlines() == ["id,name", "1,Alice", "2,Bob"]
        checks.append(("cli_output_csv", csv_ok, f"rc={p_csv.returncode}"))

        # 3. Old --format flag rejected and absent from --help
        p_old = _run_cli(repo, "--input", str(sample), "--format", "json")
        p_help = _run_cli(repo, "--help")
        flag_ok = (
            p_old.returncode != 0
            and p_help.returncode == 0
            and "--output" in p_help.stdout
            and "--format" not in p_help.stdout
        )
        checks.append(("cli_retired_format_flag", flag_ok, f"old_rc={p_old.returncode}"))

    # 4. All repo docs synced (README.md + docs/cli.md)
    readme_text = (repo / "README.md").read_text(encoding="utf-8")
    cli_doc_text = (repo / "docs" / "cli.md").read_text(encoding="utf-8")
    ok_rm, msg_rm = _audit_doc("README.md", readme_text)
    ok_cd, msg_cd = _audit_doc("docs/cli.md", cli_doc_text)
    checks.append(("doc_sync_readme", ok_rm, msg_rm))
    checks.append(("doc_sync_cli_md", ok_cd, msg_cd))

    # Strict doc-drift invariant check
    ok_drift, _ = _audit_doc("docs/cli.md", cli_doc_text + "\nUse --format json\n")
    checks.append((
        "doc_drift_detected",
        not ok_drift,
        "stale --format injection rejected by doc audit" if not ok_drift else "doc audit missed stale flag",
    ))

    ok_ut, msg_ut = kit.run_unittest(repo)
    checks.append(("unittest", ok_ut, msg_ut))

    ok_mut, msg_mut = kit.check_mutation_caught(
        repo,
        "src/export_cli.py",
        lambda s: s.replace("--output", "--format"),
    )
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
