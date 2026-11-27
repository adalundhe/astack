#!/usr/bin/env python3
"""Executable verifier for `skill-how-it-works`."""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _eval_kit

_ASTACK_TOOLS = Path(__file__).resolve().parents[2] / "bin" / "astack-tools"
_PIPELINE_FILES = ("ingest.py", "transform.py", "sink.py")
_CITE_RE = re.compile(r"(?:repo/)?(?:src/)?(ingest\.py|transform\.py|sink\.py):(\d+)(?:-(\d+))?")


def _function_spans(py_file: Path) -> tuple[int, list[tuple[str, int, int]]]:
    text = py_file.read_text(encoding="utf-8")
    total_lines = len(text.splitlines())
    tree = ast.parse(text, filename=str(py_file))
    spans: list[tuple[str, int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_line = getattr(node, "end_lineno", node.lineno) or node.lineno
            spans.append((node.name, node.lineno, end_line))
    return total_lines, spans


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
    docs_proc = subprocess.run(
        [sys.executable, "-B", str(_ASTACK_TOOLS), "docs", "list", "--project", "pipe-walk", "--json"],
        cwd=ws,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    docs_entries: list[dict[str, object]] = []
    if docs_proc.returncode == 0:
        try:
            payload = json.loads(docs_proc.stdout)
            raw = payload.get("docs")
            if isinstance(raw, list):
                docs_entries = raw
        except json.JSONDecodeError:
            docs_entries = []

    docs_dir = astack_home / "pipe-walk" / "docs"
    doc_texts = [
        p.read_text(encoding="utf-8", errors="replace")
        for p in (sorted(docs_dir.rglob("*")) if docs_dir.is_dir() else [])
        if p.is_file() and not p.name.startswith(".")
    ]
    joined_docs = "\n".join(doc_texts)

    docs_saved = docs_proc.returncode == 0 and len(docs_entries) >= 1 and len(joined_docs.strip()) >= 120
    checks.append((
        "walkthrough-saved-in-docs",
        docs_saved,
        f"astack-tools docs list found {len(docs_entries)} doc(s) ({len(joined_docs)} chars)"
        if docs_saved
        else f"rc={docs_proc.returncode}, count={len(docs_entries)}",
    ))

    file_meta = {fname: _function_spans(repo / "src" / fname) for fname in _PIPELINE_FILES}
    cited_by_file: dict[str, list[tuple[int, int]]] = {fname: [] for fname in _PIPELINE_FILES}
    for m in _CITE_RE.finditer(joined_docs):
        fname = m.group(1)
        start = int(m.group(2))
        end = int(m.group(3)) if m.group(3) else start
        cited_by_file[fname].append((start, end))

    out_of_bounds: list[str] = []
    matched_defs: dict[str, list[str]] = {fname: [] for fname in _PIPELINE_FILES}
    for fname, cites in cited_by_file.items():
        total_lines, spans = file_meta[fname]
        for start, end in cites:
            if start < 1 or end > total_lines or end < start:
                out_of_bounds.append(f"{fname}:{start}-{end} (file has {total_lines} lines)")
                continue
            for fn_name, def_start, def_end in spans:
                # Citation either lands on the def line itself or overlaps the function span
                if def_start <= start <= def_end or (start <= def_start <= end):
                    if fn_name not in matched_defs[fname]:
                        matched_defs[fname].append(fn_name)

    all_three_verified = (
        not out_of_bounds
        and all(len(matched_defs[fname]) >= 1 for fname in _PIPELINE_FILES)
    )
    checks.append((
        "verified-file-line-citations-all-3-files",
        all_three_verified,
        f"verified function citations: {matched_defs}"
        if all_three_verified
        else f"matched_defs={matched_defs}, out_of_bounds={out_of_bounds}",
    ))

    has_mermaid = bool(
        re.search(r"```mermaid\s+.*?(?:flowchart|graph|sequenceDiagram|stateDiagram)", joined_docs, re.S)
    )
    checks.append((
        "mermaid-flow-diagram",
        has_mermaid,
        "Mermaid flow diagram present in saved walkthrough" if has_mermaid else "missing Mermaid diagram in saved walkthrough",
    ))

    low = joined_docs.lower()
    has_ran_and_read = bool(re.search(r"\bran\b", low)) and bool(re.search(r"\bread\b", low))
    checks.append((
        "marks-ran-vs-read",
        has_ran_and_read,
        "walkthrough distinguishes ran vs read claims" if has_ran_and_read else "missing explicit ran vs read labels",
    ))

    sec_hits = _eval_kit.check_no_secrets([joined_docs, final_text])
    checks.append(("no-secrets", not sec_hits, "none" if not sec_hits else "; ".join(sec_hits)))

    leak_hits = _eval_kit.check_no_internal_leaks([joined_docs, final_text])
    checks.append(("no-internal-leaks", not leak_hits, "none" if not leak_hits else "; ".join(leak_hits)))

    return _eval_kit.report_and_exit(checks)


if __name__ == "__main__":
    sys.exit(main())
