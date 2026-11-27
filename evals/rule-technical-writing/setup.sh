#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests repo/docs

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Report Exporter

A blazing fast, seamless, robust CLI utility for converting CSV files into JSON or CSV reports.

## Usage

```bash
python3 src/export_cli.py --input sales.csv --format json
python3 src/export_cli.py --input sales.csv --format csv
```

By default, `--format` outputs `json`. See `docs/cli.md` for the full flag reference.
EOF

cat > repo/docs/cli.md <<'EOF'
# CLI Reference

`src/export_cli.py` provides a seamless, robust export workflow.

## Flags

| Flag | Required | Default | Values | Description |
| --- | --- | --- | --- | --- |
| `--input` | Yes | — | file path | Path to the input CSV file. |
| `--format` | No | `json` | `json`, `csv` | Output serialization format. |

## Examples

Export as JSON (default):

```bash
python3 src/export_cli.py --input data.csv
python3 src/export_cli.py --input data.csv --format json
```

Export as CSV:

```bash
python3 src/export_cli.py --input data.csv --format csv
```
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/export_cli.py <<'EOF'
#!/usr/bin/env python3
"""Export rows from a CSV file to JSON or CSV."""
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
import sys


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def serialize_rows(rows: list[dict[str, str]], fmt: str) -> str:
    if fmt == "json":
        return json.dumps(rows, indent=2) + "\n"
    if fmt == "csv":
        if not rows:
            return ""
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()
    raise ValueError(f"unsupported format: {fmt}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert a CSV file into JSON or CSV.")
    parser.add_argument("--input", required=True, help="Path to the input CSV file.")
    parser.add_argument(
        "--format",
        choices=("json", "csv"),
        default="json",
        help="Output serialization format (default: json).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    path = Path(args.input)
    if not path.is_file():
        print(f"error: input file not found: {path}", file=sys.stderr)
        return 1
    rows = load_rows(path)
    sys.stdout.write(serialize_rows(rows, args.format))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
EOF
chmod +x repo/src/export_cli.py

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_export_cli.py <<'EOF'
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "src" / "export_cli.py"


class ExportCliBaselineTest(unittest.TestCase):
    def test_default_json_output(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "data.csv"
            src.write_text("id,name\n1,Alice\n2,Bob\n", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "-B", str(CLI), "--input", str(src), "--format", "json"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            parsed = json.loads(proc.stdout)
            self.assertEqual(parsed, [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}])

    def test_csv_output(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "data.csv"
            src.write_text("id,name\n1,Alice\n", encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "-B", str(CLI), "--input", str(src), "--format", "csv"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout, "id,name\n1,Alice\n")


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial report exporter with --format"
git -C repo rev-parse HEAD > program/base_sha.txt
