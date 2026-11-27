#!/usr/bin/env python3
"""Executable verifier for `skill-workflow-this`."""
from __future__ import annotations

import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_EXPECTED_STATES = ("waiting", "ready", "running", "done", "failed", "blocked_on_person")


def _astack_tools_path() -> Path:
    return Path(__file__).resolve().parents[2] / "bin" / "astack-tools"


def _run_tools_json(tools: Path, args: list[str], astack_home: Path) -> tuple[bool, dict, str]:
    env = {**os.environ, "ASTACK_HOME": str(astack_home), "PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.run(
        [sys.executable, "-B", str(tools), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=20,
    )
    if proc.returncode != 0:
        return False, {}, f"exit {proc.returncode}: {proc.stderr.strip()}"
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return False, {}, f"invalid JSON: {exc}"
    return True, data, "ok"


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    astack_home = _eval_kit.astack_home_from_env(ws)
    tools = _astack_tools_path()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("repo-exists", False, f"missing repo directory: {repo}"))
        return _eval_kit.report_and_exit(checks)

    ok_a, data_a, err_a = _run_tools_json(
        tools, ["automations", "list", "--project", "nightly-audit", "--json"], astack_home
    )
    if not ok_a:
        checks.append(("automations-list", False, err_a))
        return _eval_kit.report_and_exit(checks)

    autos = [a for a in (data_a.get("automations") or []) if a.get("project") == "nightly-audit"]
    checks.append((
        "automation-discovered",
        bool(autos),
        f"found {len(autos)} automation(s) for nightly-audit"
        if autos
        else f"no automation found under {astack_home}/nightly-audit/automations/",
    ))

    secret_texts: list[str] = [_eval_kit.final_text_from_env()]
    if autos:
        chosen = autos[0]
        auto_dir = Path(str(chosen["path"]))
        entry_name = str(chosen.get("entrypoint") or "")
        entry_path = auto_dir / entry_name if entry_name else None
        if entry_path is None or not entry_path.is_file() or entry_path.suffix != ".py":
            py_files = sorted(
                p for p in auto_dir.glob("*.py")
                if p.name != "__init__.py" and not p.name.startswith("test_")
            )
            entry_path = py_files[0] if py_files else None

        if entry_path is None:
            checks.append(("automation-runnable", False, f"no Python entrypoint found in {auto_dir}"))
            checks.append(("explicit-task-states", False, "skipped: entrypoint missing"))
        else:
            try:
                py_compile.compile(str(entry_path), doraise=True)
            except py_compile.PyCompileError as exc:
                checks.append(("automation-runnable", False, f"compile failed: {exc}"))
            else:
                src_text = entry_path.read_text(encoding="utf-8", errors="replace")
                present_states = [s for s in _EXPECTED_STATES if s in src_text]
                checks.append((
                    "explicit-task-states",
                    len(present_states) >= 5,
                    f"found {len(present_states)}/{len(_EXPECTED_STATES)} states ({', '.join(present_states)})",
                ))
                run_proc = subprocess.run(
                    [sys.executable, "-B", str(entry_path), "--dry-run"],
                    cwd=ws,
                    capture_output=True,
                    text=True,
                    env={**os.environ, "ASTACK_HOME": str(astack_home), "PYTHONDONTWRITEBYTECODE": "1"},
                    timeout=20,
                )
                checks.append((
                    "automation-runnable",
                    run_proc.returncode == 0,
                    f"--dry-run exited 0 ({len(run_proc.stdout.strip().splitlines())} line(s))"
                    if run_proc.returncode == 0
                    else f"--dry-run failed (exit {run_proc.returncode}): {(run_proc.stderr or run_proc.stdout).strip()[:200]}",
                ))
                secret_texts.extend([run_proc.stdout, run_proc.stderr])

        for item in sorted(auto_dir.rglob("*")):
            if item.is_file() and "__pycache__" not in item.parts and item.suffix not in (".pyc", ".db", ".sqlite", ".sqlite3"):
                try:
                    secret_texts.append(item.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    continue
    else:
        checks.append(("explicit-task-states", False, "skipped: no automation discovered"))
        checks.append(("automation-runnable", False, "skipped: no automation discovered"))

    ok_d, data_d, err_d = _run_tools_json(
        tools, ["docs", "list", "--project", "nightly-audit", "--json"], astack_home
    )
    if not ok_d:
        checks.append(("docs-discovered", False, err_d))
    else:
        docs = [d for d in (data_d.get("docs") or []) if d.get("project") == "nightly-audit"]
        doc_texts: list[str] = []
        for entry in docs:
            p = Path(str(entry["path"]))
            if p.is_file():
                doc_texts.append(p.read_text(encoding="utf-8", errors="replace"))
            elif p.is_dir():
                for child in sorted(p.rglob("*")):
                    if child.is_file() and child.suffix in (".md", ".txt", ".rst"):
                        doc_texts.append(child.read_text(encoding="utf-8", errors="replace"))
        combined_docs = "\n".join(doc_texts)
        secret_texts.append(combined_docs)
        doc_low = combined_docs.lower()
        has_usage = bool(combined_docs.strip()) and ("dry-run" in doc_low or "resume" in doc_low) and ("waiting" in doc_low or "failed" in doc_low)
        checks.append((
            "docs-discovered",
            bool(docs) and has_usage,
            f"found {len(docs)} doc entry(s) with usage commands and state reference"
            if (docs and has_usage)
            else f"missing usage doc under {astack_home}/nightly-audit/docs/ documenting run/resume commands and task states",
        ))

    clean_ok, clean_detail = _eval_kit.check_git_clean(repo)
    checks.append(("repo-git-clean", clean_ok, clean_detail))

    sec_hits = _eval_kit.check_no_secrets(secret_texts)
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([_eval_kit.final_text_from_env()])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
