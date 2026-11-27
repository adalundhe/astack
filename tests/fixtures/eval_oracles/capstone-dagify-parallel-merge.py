"""Separated offline oracle for `capstone-dagify-parallel-merge`."""
from __future__ import annotations

import subprocess
from pathlib import Path

_DAG_MD = """# Reports Parallel Integration DAG

```mermaid
flowchart TD
    T1[T1: Consolidate parser lane] --> T3[T3: Integrate lanes and wire pipeline]
    T2[T2: Verify formatter lane] --> T3
```

## T1: Consolidate parser lane
- **Description:** Consolidate the 4 noisy WIP commits on `lane/parser` into 1 clean commit while preserving Alice's authorship attribution and exact tree contents.
- **Implementation guide:** Soft-reset `lane/parser` to `main`, commit once with a `Co-authored-by: Alice <alice@example.invalid>` trailer, and verify `lane/parser^{tree}` is unchanged.
- **Acceptance criteria:** `lane/parser` has 1–2 commits ahead of `main`, exact pre-squish tree hash, and preserves `Alice <alice@example.invalid>`.
- **Tests:** `python3 -B -m unittest discover -s tests -p "test_parser.py"` passes.
- **Touches:** `src/parser.py`, `tests/test_parser.py`

## T2: Verify formatter lane
- **Description:** Review and verify the clean 2-commit `lane/formatter` branch before merging to `main`.
- **Implementation guide:** Verify `src/formatter.py` escapes pipe characters and renders right-aligned latency columns without touching parser files.
- **Acceptance criteria:** `lane/formatter` passes unit tests and remains disjoint from `lane/parser`.
- **Tests:** `python3 -B -m unittest discover -s tests -p "test_formatter.py"` passes.
- **Touches:** `src/formatter.py`, `tests/test_formatter.py`

## T3: Integrate lanes and wire pipeline
- **Depends on:** T1, T2
- **Description:** Merge `lane/parser` and `lane/formatter` onto `main`, wire `src/pipeline.py:build_report`, and add end-to-end pipeline tests.
- **Implementation guide:** Merge both branches onto `main` cleanly, import `parse_rows` and `format_table` inside `src/pipeline.py`, and add `tests/test_pipeline.py`.
- **Acceptance criteria:** Both feature modules and `build_report` pass full test discovery on a clean `main` branch.
- **Tests:** `python3 -B -m unittest discover -s tests` passes.
- **Touches:** `src/pipeline.py`, `tests/test_pipeline.py`
"""

_WIRED_PIPELINE = '''"""Report pipeline entrypoint integrating parser and formatter."""
from __future__ import annotations

from formatter import format_table
from parser import parse_rows


def build_report(raw_csv: str) -> str:
    """Parse raw CSV rows and render a markdown summary table."""
    rows = parse_rows(raw_csv)
    return format_table(rows)
'''

_PIPELINE_TESTS = r'''"""End-to-end integration tests for the reports pipeline."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pipeline import build_report


class PipelineTests(unittest.TestCase):
    def test_build_report_parses_and_formats(self) -> None:
        raw = 'service,status,latency_ms\n"pay,core",ok,120\nedge|gw,degraded,340\n'
        report = build_report(raw)
        self.assertIn("| Service | Status | Latency (ms) |", report)
        self.assertIn("| pay,core | ok | 120 |", report)
        self.assertIn("| edge\\|gw | degraded | 340 |", report)


if __name__ == "__main__":
    unittest.main()
'''

_LESSON_MD = """---
lesson: parallel-lane-squish-and-merge
project: reports
related_projects: []
keywords: [git, squish, co-authored-by, dag, parallel-merge]
status: active
created: 2026-11-26T09:40Z
updated: 2026-11-26T09:40Z
---

# Preserve Co-Author Attribution When Consolidating Parallel Feature Lanes

## Overview
Consolidating noisy WIP feature branches before integrating parallel lanes onto `main` keeps history reviewable without losing contributor credit or introducing merge conflicts.
- **Applies when:** Consolidating multi-author WIP branches prior to merging disjoint parallel feature lanes into `main`.
- **Does not apply when:** Branches already have clean atomic commits or shared history has already been published on a protected branch.

## Skills and tools used
- **Skills:** `dagify`, `lead`, `review`, `squish`, `lookback`
- **Tools / environments:** `git`, Python 3.12 `unittest`

## Details
`lane/parser` accumulated 4 WIP/fixup commits including a critical CSV-quoting fix authored by `Alice <alice@example.invalid>`, while `lane/formatter` had 2 clean commits on disjoint files. Verifying `lane/parser^{tree}` before and after soft-reset consolidation proved zero code drift while retaining `Co-authored-by: Alice <alice@example.invalid>` in both the branch and `main` merge history.

## Successes
- Disjoint file ownership in `program/DAG.md` allowed conflict-free integration of `lane/parser` and `lane/formatter` before wiring `src/pipeline.py`.
- Checking tree hashes before and after consolidation guaranteed exact patch equivalence.

## Issues
- Naive `git merge --squash` without inspecting commit authors would have dropped Alice's attribution on `lane/parser`.

## Best path & guards
- **Next time:** Run author and tree-hash verification before and after consolidating any multi-commit branch, and add `Co-authored-by:` trailers for every non-primary author.
- **Structural guards:** End-to-end `tests/test_pipeline.py` guards parser + formatter contract compatibility on `main`.

## References
- `program/DAG.md`
- `program/LANES.md`
- `repo/src/pipeline.py`
"""


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    base_sha = (ws / "program" / "base_sha.txt").read_text(encoding="utf-8").strip()

    (ws / "program" / "DAG.md").write_text(_DAG_MD, encoding="utf-8")

    # 1. Squish lane/parser from 4 WIP commits into 1 clean commit preserving Alice's credit and exact tree
    _git(repo, "checkout", "lane/parser")
    _git(repo, "reset", "--soft", base_sha)
    _git(
        repo,
        "commit",
        "-m",
        "feat: add CSV report parser with quoting and validation\n\n"
        "Co-authored-by: Alice <alice@example.invalid>",
    )

    # 2. Merge both lanes cleanly onto main and wire src/pipeline.py
    _git(repo, "checkout", "main")
    _git(repo, "merge", "--no-ff", "lane/parser", "-m", "merge: integrate lane/parser")
    _git(repo, "merge", "--no-ff", "lane/formatter", "-m", "merge: integrate lane/formatter")

    (repo / "src" / "pipeline.py").write_text(_WIRED_PIPELINE, encoding="utf-8")
    (repo / "tests" / "test_pipeline.py").write_text(_PIPELINE_TESTS, encoding="utf-8")
    _git(repo, "add", "src/pipeline.py", "tests/test_pipeline.py")
    _git(repo, "commit", "-m", "feat: wire parser and formatter in report pipeline")

    # 3. Record active closing lesson strictly under program/astack_home/reports/lessons/
    lesson_dir = ws / "program" / "astack_home" / "reports" / "lessons" / "parallel-lane-squish-and-merge"
    lesson_dir.mkdir(parents=True, exist_ok=True)
    (lesson_dir / "LESSON.md").write_text(_LESSON_MD, encoding="utf-8")

    return {
        "final_text": (
            "Planned parallel integration in `program/DAG.md`, consolidated `lane/parser` from 4 WIP commits into 1 commit "
            "with identical tree and preserved `Co-authored-by: Alice <alice@example.invalid>`, merged `lane/parser` and "
            "`lane/formatter` onto `main`, wired `src/pipeline.py` with passing unit tests, and saved the closing lesson at "
            "`program/astack_home/reports/lessons/parallel-lane-squish-and-merge/LESSON.md`."
        ),
    }
