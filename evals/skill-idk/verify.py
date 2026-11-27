#!/usr/bin/env python3
"""Executable verifier for `skill-idk`."""
from __future__ import annotations

import json
import os
import py_compile
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_ASTACK_TOOLS = Path(__file__).resolve().parents[2] / "bin" / "astack-tools"


def _find_demo_script(demo_dir: Path) -> Path | None:
    if not demo_dir.is_dir():
        return None
    py_files = sorted(
        p for p in demo_dir.rglob("*.py")
        if p.is_file() and "__pycache__" not in p.parts and p.name != "__init__.py" and not p.name.startswith("test_")
    )
    return py_files[0].resolve() if py_files else None


def main() -> int:
    ws = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    repo = ws / "repo"
    astack_home = _eval_kit.astack_home_from_env(ws).resolve()
    final_text = _eval_kit.final_text_from_env()
    checks: list[tuple[str, bool, str]] = []

    if not repo.is_dir():
        checks.append(("repo-exists", False, f"missing repo directory: {repo}"))
        return _eval_kit.report_and_exit(checks)

    clean_ok, clean_detail = _eval_kit.check_git_clean(repo)
    checks.append(("repo-git-clean", clean_ok, clean_detail))

    env = {**os.environ, "ASTACK_HOME": str(astack_home), "PYTHONDONTWRITEBYTECODE": "1"}
    res_proc = subprocess.run(
        [sys.executable, "-B", str(_ASTACK_TOOLS), "research", "list", "--project", "rate-demo", "--json"],
        cwd=ws,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    res_entries: list[dict[str, object]] = []
    if res_proc.returncode == 0:
        try:
            payload = json.loads(res_proc.stdout)
            raw = payload.get("research")
            if isinstance(raw, list):
                res_entries = raw
        except json.JSONDecodeError:
            res_entries = []

    research_dir = astack_home / "rate-demo" / "research"
    research_texts = [
        p.read_text(encoding="utf-8", errors="replace")
        for p in (sorted(research_dir.rglob("*")) if research_dir.is_dir() else [])
        if p.is_file() and not p.name.startswith(".")
    ]
    joined_research = "\n".join(research_texts).lower()
    research_ok = (
        res_proc.returncode == 0
        and len(res_entries) >= 1
        and "token" in joined_research
        and "leaky" in joined_research
    )
    checks.append((
        "research-notes-saved",
        research_ok,
        f"astack-tools research list returned {len(res_entries)} entry/entries covering token and leaky buckets"
        if research_ok
        else f"rc={res_proc.returncode}, count={len(res_entries)}",
    ))

    demo_script = _find_demo_script(ws / "program" / "demo")
    demo_src = ""
    demo_stdout = ""
    if demo_script is None:
        checks.append(("demo-script-exists", False, "no runnable Python demo found under program/demo/"))
        checks.append(("demo-executes-limiter", False, "skipped (missing demo script)"))
    else:
        rel_demo = str(demo_script.relative_to(ws)) if demo_script.is_relative_to(ws) else str(demo_script)
        checks.append(("demo-script-exists", True, rel_demo))
        demo_src = demo_script.read_text(encoding="utf-8", errors="replace")
        try:
            py_compile.compile(str(demo_script), doraise=True)
            compiled = True
            compile_err = ""
        except py_compile.PyCompileError as exc:
            compiled = False
            compile_err = str(exc)

        imports_limiter = "limiter" in demo_src and ("TokenBucket" in demo_src or "LeakyBucket" in demo_src)
        run_proc = (
            subprocess.run(
                [sys.executable, "-B", str(demo_script)],
                cwd=ws,
                env=env,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=20,
            )
            if compiled
            else None
        )
        demo_stdout = run_proc.stdout if run_proc else ""
        out_low = demo_stdout.lower()
        demo_ok = (
            compiled
            and imports_limiter
            and run_proc is not None
            and run_proc.returncode == 0
            and "token" in out_low
            and "leaky" in out_low
            and len(demo_stdout.strip()) >= 40
        )
        checks.append((
            "demo-executes-limiter",
            demo_ok,
            f"demo exited 0 exercising TokenBucket and LeakyBucket ({len(demo_stdout.splitlines())} lines)"
            if demo_ok
            else f"compiled={compiled} ({compile_err}), imports_limiter={imports_limiter}, rc={run_proc.returncode if run_proc else 'n/a'}, stderr={(run_proc.stderr.strip()[:120] if run_proc else '')}",
        ))

    explainer_path = ws / "program" / "EXPLAINER.md"
    explainer_text = explainer_path.read_text(encoding="utf-8", errors="replace") if explainer_path.is_file() else ""
    combined_guide = "\n".join([final_text, explainer_text])
    has_mermaid = bool(
        re.search(r"```mermaid\s+.*?(?:flowchart|graph|sequenceDiagram|stateDiagram)", combined_guide, re.S)
    )
    guide_low = combined_guide.lower()
    has_comparison = (
        "token" in guide_low
        and "leaky" in guide_low
        and "burst" in guide_low
        and ("limiter.py" in guide_low or "tokenbucket" in guide_low)
    )
    checks.append((
        "mermaid-and-plain-explainer",
        has_mermaid and has_comparison,
        "Mermaid diagram and plain token-vs-leaky explanation present"
        if (has_mermaid and has_comparison)
        else f"has_mermaid={has_mermaid}, has_comparison={has_comparison}",
    ))

    sec_hits = _eval_kit.check_no_secrets([*research_texts, demo_src, demo_stdout, explainer_text, final_text])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([*research_texts, explainer_text, final_text])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
