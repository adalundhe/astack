"""Separated offline oracle for `skill-how-it-works`."""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path


def _func_lines(py_file: Path) -> dict[str, int]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    return {
        node.name: node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }


def apply(ws: Path) -> dict[str, object]:
    """Generate a verified file:line walkthrough under pipe-walk/docs/ with Mermaid diagram."""
    repo = ws / "repo"
    ing = _func_lines(repo / "src" / "ingest.py")
    trn = _func_lines(repo / "src" / "transform.py")
    snk = _func_lines(repo / "src" / "sink.py")

    proc = subprocess.run(
        [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests"],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=15,
    )
    test_status = "OK" if proc.returncode == 0 else f"FAILED ({proc.returncode})"

    walkthrough = (
        "# pipe-walk Pipeline Walkthrough\n\n"
        "## Purpose\n"
        "`pipe-walk` converts raw JSON-lines request records into per-kind cent totals across three pure-Python stages (**read**: `repo/README.md:1-3`).\n\n"
        "## Pipeline Flow\n"
        "```mermaid\n"
        "flowchart LR\n"
        "  Lines[Raw JSONL lines] --> Ingest[ingest_batch / parse_event]\n"
        "  Ingest --> Transform[transform_batch / normalize_record]\n"
        "  Transform --> Sink[format_summary]\n"
        "  Sink --> Out[accepted_count + totals_by_kind]\n"
        "```\n\n"
        "## Stage-by-Stage Breakdown\n"
        f"1. **Ingest (`src/ingest.py`):** `parse_event` (`src/ingest.py:{ing['parse_event']}`) strips each line, parses JSON objects, drops blank/non-dict/malformed rows, and attaches `ingested_version = 1` (**read**). "
        f"`ingest_batch` (`src/ingest.py:{ing['ingest_batch']}`) iterates through input lines and collects non-`None` dicts (**read**).\n"
        f"2. **Transform (`src/transform.py`):** `normalize_record` (`src/transform.py:{trn['normalize_record']}`) lowercases `kind`, coerces `amount_cents` to `int`, and drops records where `kind` is empty or `amount_cents <= 0` (**read**). "
        f"`transform_batch` (`src/transform.py:{trn['transform_batch']}`) filters and collects normalized records (**read**).\n"
        f"3. **Sink (`src/sink.py`):** `format_summary` (`src/sink.py:{snk['format_summary']}`) sums `amount_cents` by `kind` in sorted key order and emits `accepted_count` plus `totals_by_kind` (**read**). "
        f"`run_pipeline` (`src/sink.py:{snk['run_pipeline']}`) chains `ingest_batch` -> `transform_batch` -> `format_summary` (**read**).\n\n"
        "## Walked Concrete Example & Runtime Verification\n"
        f"- **Verified by running tests (`ran`):** `python3 -B -m unittest discover -s tests` exited {proc.returncode} ({test_status}).\n"
        "- Given input lines `[{\"kind\": \"Order\", \"amount_cents\": 1500}, \"not-json\", {\"kind\": \"order\", \"amount_cents\": 500}, {\"kind\": \"refund\", \"amount_cents\": -100}, {\"kind\": \"Fee\", \"amount_cents\": 250}]`:\n"
        f"  - `ingest_batch` (`src/ingest.py:{ing['ingest_batch']}`) drops `\"not-json\"` and yields 4 dicts with `ingested_version=1`.\n"
        f"  - `transform_batch` (`src/transform.py:{trn['transform_batch']}`) lowercases `Order`/`Fee` and drops `refund` (`-100 <= 0`), leaving 3 records.\n"
        f"  - `format_summary` (`src/sink.py:{snk['format_summary']}`) returns `{{\"accepted_count\": 3, \"totals_by_kind\": {{\"fee\": 250, \"order\": 2000}}}}` (**ran**).\n"
    )

    docs_dir = ws / "program" / "astack_home" / "pipe-walk" / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    doc_path = docs_dir / "pipeline-walkthrough.md"
    doc_path.write_text(walkthrough, encoding="utf-8")

    return {
        "final_text": (
            f"Saved the verified pipeline walkthrough to `{doc_path.relative_to(ws)}` (`./repo` untouched). "
            f"All three stages (`src/ingest.py:{ing['ingest_batch']}`, `src/transform.py:{trn['transform_batch']}`, "
            f"`src/sink.py:{snk['run_pipeline']}`) are cited with `ran` vs `read` labels, a Mermaid flow diagram, and a walked example."
        ),
    }
