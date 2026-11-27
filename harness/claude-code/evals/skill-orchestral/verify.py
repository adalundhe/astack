#!/usr/bin/env python3
"""Executable verifier for `skill-orchestral`."""
from __future__ import annotations

import ast
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit


def _astack_tools_path() -> Path:
    return Path(__file__).resolve().parents[2] / "bin" / "astack-tools"


def _inspect_orchestral_source(path: Path) -> tuple[bool, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        return False, f"syntax error: {exc}"

    imports_orchestral = False
    has_dependencies_kw = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "orchestral" or alias.name.startswith("orchestral."):
                    imports_orchestral = True
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if mod == "orchestral" or mod.startswith("orchestral."):
                imports_orchestral = True
        elif isinstance(node, ast.keyword) and node.arg == "dependencies":
            has_dependencies_kw = True

    if not imports_orchestral:
        return False, f"{path.name} does not import orchestral"
    if "Orchestral" not in text:
        return False, f"{path.name} does not reference Orchestral"
    if not has_dependencies_kw:
        return False, f"{path.name} missing multi-wave dependencies=[...] declaration"
    if "execution_order" not in text:
        return False, f"{path.name} missing execution_order() validation"
    return True, f"{path.name} imports orchestral, declares dependencies=[...], and validates execution_order()"


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    astack_home = _eval_kit.astack_home_from_env(ws)
    tools = _astack_tools_path()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("repo-exists", False, f"missing repo directory: {repo}"))
        return _eval_kit.report_and_exit(checks)

    env = {**os.environ, "ASTACK_HOME": str(astack_home), "PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.run(
        [sys.executable, "-B", str(tools), "automations", "list", "--project", "data-sync", "--runner", "orchestral", "--json"],
        capture_output=True,
        text=True,
        env=env,
        timeout=20,
    )
    if proc.returncode != 0:
        checks.append(("astack-tools-list", False, f"exit {proc.returncode}: {proc.stderr.strip()}"))
        return _eval_kit.report_and_exit(checks)

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        checks.append(("astack-tools-json", False, f"invalid JSON: {exc}"))
        return _eval_kit.report_and_exit(checks)

    autos = payload.get("automations") or []
    matching = [a for a in autos if a.get("project") == "data-sync" and a.get("runner") == "orchestral"]
    checks.append((
        "orchestral-automation-discovered",
        bool(matching),
        f"found {len(matching)} orchestral automation(s) for data-sync"
        if matching
        else f"no orchestral automation found under {astack_home}/data-sync/automations/",
    ))

    secret_texts: list[str] = [_eval_kit.final_text_from_env()]
    if matching:
        chosen = matching[0]
        auto_dir = Path(str(chosen["path"]))
        manifest_path = auto_dir / "automation.json"
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                m_ok = isinstance(manifest, dict) and manifest.get("runner") == "orchestral" and bool(manifest.get("entrypoint"))
                checks.append((
                    "manifest-valid",
                    m_ok,
                    f"automation.json runner={manifest.get('runner')!r} entrypoint={manifest.get('entrypoint')!r}"
                    if isinstance(manifest, dict)
                    else "automation.json is not a JSON object",
                ))
            except (OSError, ValueError) as exc:
                checks.append(("manifest-valid", False, f"invalid automation.json: {exc}"))
        else:
            checks.append(("manifest-valid", False, f"missing automation.json in {auto_dir}"))

        entry_name = str(chosen.get("entrypoint") or "")
        entry_path = auto_dir / entry_name if entry_name else auto_dir / "workflow.py"
        if not entry_path.is_file() or entry_path.suffix != ".py":
            checks.append(("py-compile", False, f"missing Python entrypoint: {entry_path}"))
            checks.append(("orchestral-contract", False, "skipped: entrypoint missing"))
        else:
            try:
                py_compile.compile(str(entry_path), doraise=True)
                checks.append(("py-compile", True, f"{entry_path.name} compiled"))
            except py_compile.PyCompileError as exc:
                checks.append(("py-compile", False, f"compile failed: {exc}"))
            c_ok, c_detail = _inspect_orchestral_source(entry_path)
            checks.append(("orchestral-contract", c_ok, c_detail))

        for item in sorted(auto_dir.rglob("*")):
            if item.is_file() and "__pycache__" not in item.parts and item.suffix != ".pyc":
                try:
                    secret_texts.append(item.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    continue
    else:
        checks.append(("manifest-valid", False, "skipped: no orchestral automation discovered"))
        checks.append(("py-compile", False, "skipped: no orchestral automation discovered"))
        checks.append(("orchestral-contract", False, "skipped: no orchestral automation discovered"))

    clean_ok, clean_detail = _eval_kit.check_git_clean(repo)
    checks.append(("repo-git-clean", clean_ok, clean_detail))

    sec_hits = _eval_kit.check_no_secrets(secret_texts)
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([_eval_kit.final_text_from_env()])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
