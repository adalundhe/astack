"""Separated offline oracle for `skill-simplify-me`."""
from __future__ import annotations

from pathlib import Path

SIMPLIFIED_REPORT_PY = '''"""Direct CSV and JSON report formatting."""
from __future__ import annotations

import csv
import io
import json
from typing import Any


def _format_csv(rows: list[dict[str, Any]], include_header: bool) -> str:
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\\n")
    if include_header:
        writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


def render_report(
    rows: list[dict[str, Any]],
    fmt: str = "csv",
    include_header: bool = True,
) -> str:
    """Render tabular dict rows as CSV or JSON."""
    key = fmt.strip().lower()
    if key == "csv":
        return _format_csv(rows, include_header)
    if key == "json":
        return json.dumps(rows, sort_keys=True)
    raise ValueError(f"unsupported report format: {fmt!r}")
'''


def apply(ws: Path) -> dict[str, object]:
    """Strip the 5 unnecessary abstraction layers in repo/src/report.py while keeping tests green."""
    (ws / "repo" / "src" / "report.py").write_text(SIMPLIFIED_REPORT_PY, encoding="utf-8")
    return {
        "final_text": (
            "Simplified `repo/src/report.py` from 7 classes (~110 code lines) down to 2 direct functions (~30 code lines). "
            "Cut: `ConfigAdapter`, `AbstractBaseFormatter`, `CsvConcreteFormatter`, `JsonConcreteFormatter`, `StrategyRegistry`, "
            "`FormatterFactory`, `FormatterProxyWrapper`, and narrating comments. "
            "Kept: exact `render_report(rows, fmt='csv', include_header=True)` signature, RFC-4180 CSV quoting, sorted JSON output, "
            "empty-row behavior, and `ValueError` on unsupported formats. All tests in `tests/test_report.py` pass."
        ),
    }
