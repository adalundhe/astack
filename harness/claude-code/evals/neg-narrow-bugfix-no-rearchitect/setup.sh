#!/bin/bash
set -euo pipefail
mkdir -p repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/window.py <<'EOF'
from __future__ import annotations


def sliding_windows(items: list[int], size: int) -> list[list[int]]:
    """Return all contiguous sublists of length `size`."""
    if size <= 0:
        raise ValueError("size must be positive")
    if size > len(items):
        return []
    return [items[i : i + size] for i in range(len(items) - size)]
EOF

cat > repo/src/legacy_export.py <<'EOF'
from __future__ import annotations


def export_rows(rows: list[dict[str, object]], fmt: str = "csv") -> str:
    """Export tabular rows in CSV or TSV format."""
    if not rows:
        return ""
    headers = list(rows[0].keys())
    if fmt == "csv":
        sep = ","
    elif fmt == "tsv":
        sep = "\t"
    else:
        raise ValueError(f"unsupported format: {fmt}")

    lines: list[str] = []
    header_parts: list[str] = []
    for col in headers:
        header_parts.append(str(col))
    lines.append(sep.join(header_parts))

    for row in rows:
        row_parts: list[str] = []
        for col in headers:
            val = row.get(col, "")
            if val is None:
                row_parts.append("")
            else:
                row_parts.append(str(val))
        lines.append(sep.join(row_parts))

    return "\n".join(lines)
EOF

cat > repo/src/reporting.py <<'EOF'
from __future__ import annotations


def summarize_metrics(values: list[int]) -> str:
    """Format a plain-text summary of integer metrics."""
    if not values:
        return "count=0 total=0 min=0 max=0"
    count = 0
    total = 0
    low = values[0]
    high = values[0]
    for item in values:
        count += 1
        total += item
        if item < low:
            low = item
        if item > high:
            high = item
    return f"count={count} total={total} min={low} max={high}"
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_window.py <<'EOF'
import unittest

from src.window import sliding_windows


class WindowTest(unittest.TestCase):
    def test_sliding_windows_includes_final_window(self):
        self.assertEqual(sliding_windows([1, 2, 3, 4], 2), [[1, 2], [2, 3], [3, 4]])
        self.assertEqual(sliding_windows([10, 20], 2), [[10, 20]])

    def test_window_edge_cases(self):
        self.assertEqual(sliding_windows([1], 3), [])
        with self.assertRaises(ValueError):
            sliding_windows([1, 2], 0)


if __name__ == "__main__":
    unittest.main()
EOF

cat > repo/tests/test_legacy_and_reporting.py <<'EOF'
import unittest

from src.legacy_export import export_rows
from src.reporting import summarize_metrics


class LegacyAndReportingTest(unittest.TestCase):
    def test_export_rows_csv_and_tsv(self):
        rows = [{"id": 1, "name": "alpha"}, {"id": 2, "name": "beta"}]
        self.assertEqual(export_rows(rows, "csv"), "id,name\n1,alpha\n2,beta")
        self.assertEqual(export_rows(rows, "tsv"), "id\tname\n1\talpha\n2\tbeta")

    def test_summarize_metrics(self):
        self.assertEqual(summarize_metrics([3, 1, 4]), "count=3 total=8 min=1 max=4")
        self.assertEqual(summarize_metrics([]), "count=0 total=0 min=0 max=0")


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add -A
git -C repo commit -q -m "initial"
