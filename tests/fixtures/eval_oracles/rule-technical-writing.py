"""Separated offline oracle for `rule-technical-writing`."""
from __future__ import annotations

from pathlib import Path

FIXED_CLI = r'''#!/usr/bin/env python3
"""Export rows from a CSV file to JSON Lines, JSON, or CSV."""
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


def serialize_rows(rows: list[dict[str, str]], output_fmt: str) -> str:
    if output_fmt == "jsonl":
        return "".join(json.dumps(row) + "\n" for row in rows)
    if output_fmt == "json":
        return json.dumps(rows, indent=2) + "\n"
    if output_fmt == "csv":
        if not rows:
            return ""
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()
    raise ValueError(f"unsupported output format: {output_fmt}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert a CSV file into JSONL, JSON, or CSV.")
    parser.add_argument("--input", required=True, help="Path to the input CSV file.")
    parser.add_argument(
        "--output",
        choices=("jsonl", "json", "csv"),
        default="jsonl",
        help="Output serialization format (default: jsonl).",
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
    sys.stdout.write(serialize_rows(rows, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

FIXED_README = r'''# Report Exporter

Converts CSV files into JSON Lines (`jsonl`), JSON arrays (`json`), or CSV (`csv`) on stdout.

## Usage

Run with an input CSV file (defaults to `jsonl`, one JSON object per line):

```bash
python3 src/export_cli.py --input sales.csv
python3 src/export_cli.py --input sales.csv --output json
python3 src/export_cli.py --input sales.csv --output csv
```

## Reference

See `docs/cli.md` for flags, defaults, exit codes, and examples.
'''

FIXED_CLI_DOC = r'''# CLI Reference

`src/export_cli.py` reads a UTF-8 CSV file with a header row and writes serialized records to stdout.

## Flags

| Flag | Required | Default | Values | Description |
| --- | --- | --- | --- | --- |
| `--input` | Yes | — | file path | Path to the input CSV file. |
| `--output` | No | `jsonl` | `jsonl`, `json`, `csv` | Output serialization format. |

## Exit codes

- `0`: export succeeded.
- `1`: input file does not exist.
- `2`: invalid or missing CLI arguments.

## Examples

Export as JSON Lines (default):

```bash
python3 src/export_cli.py --input data.csv
python3 src/export_cli.py --input data.csv --output jsonl
```

Export as JSON array:

```bash
python3 src/export_cli.py --input data.csv --output json
```

Export as CSV:

```bash
python3 src/export_cli.py --input data.csv --output csv
```
'''

FIXED_TESTS = r'''import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "src" / "export_cli.py"


class ExportCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="export-cli-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.sample = self.tmp / "data.csv"
        self.sample.write_text("id,name\n1,Alice\n2,Bob\n", encoding="utf-8")

    def _run_cli(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(CLI), "--input", str(self.sample), *extra],
            capture_output=True,
            text=True,
        )

    def test_default_output_is_jsonl(self):
        res = self._run_cli()
        rows = [json.loads(line) for line in res.stdout.strip().splitlines()]
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(rows, [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}])

    def test_explicit_json_output(self):
        res = self._run_cli("--output", "json")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(json.loads(res.stdout), [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}])

    def test_csv_output(self):
        res = self._run_cli("--output", "csv")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(res.stdout, "id,name\n1,Alice\n2,Bob\n")

    def test_old_format_flag_rejected(self):
        res = self._run_cli("--format", "json")
        self.assertEqual(res.returncode, 2)


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    """Update export_cli.py, tests, README.md, and docs/cli.md in sync."""
    repo = ws / "repo"
    (repo / "src" / "export_cli.py").write_text(FIXED_CLI, encoding="utf-8")
    (repo / "README.md").write_text(FIXED_README, encoding="utf-8")
    (repo / "docs" / "cli.md").write_text(FIXED_CLI_DOC, encoding="utf-8")
    (repo / "tests" / "test_export_cli.py").write_text(FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Renamed --format to --output with default jsonl in src/export_cli.py, updated "
            "tests/test_export_cli.py, and synced both README.md and docs/cli.md with concrete "
            "flags, defaults, exit codes, and verified examples."
        ),
    }
