"""Separated offline oracle for `rule-yagni`."""
from __future__ import annotations

from pathlib import Path

FIXED_PARSER = '''"""Canonical CSV record parser."""
from __future__ import annotations

import csv
import io


def parse_csv(raw: str) -> list[dict[str, str]]:
    """Parse RFC-4180 CSV text with a header row into row dictionaries."""
    text = raw.strip()
    if not text:
        return []
    return list(csv.DictReader(io.StringIO(text)))
'''

FIXED_IMPORTER = '''"""Contact importer using the single parse_csv path."""
from __future__ import annotations

from parser import parse_csv


def load_records(raw: str) -> list[dict[str, str]]:
    return parse_csv(raw)


def import_contacts(raw: str) -> list[tuple[str, str]]:
    return [(row["name"], row["region"]) for row in parse_csv(raw)]
'''

FIXED_REPORT = '''"""Regional sales report using the single parse_csv path."""
from __future__ import annotations

from collections import defaultdict
from parser import parse_csv


def summarize_by_region(raw: str) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for row in parse_csv(raw):
        totals[row["region"]] += int(row["amount"])
    return dict(sorted(totals.items()))
'''

FIXED_TESTS = '''import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import importer
from parser import parse_csv
import report


class UnifiedPipelineTest(unittest.TestCase):
    def test_parse_csv_handles_quoted_commas(self):
        raw = 'name,region,amount\\n"Doe, Jane",west,100\\n'
        self.assertEqual(parse_csv(raw), [{"name": "Doe, Jane", "region": "west", "amount": "100"}])

    def test_load_records_uses_csv_parser(self):
        raw = 'name,region,amount\\n"Doe, Jane",west,100\\n'
        self.assertEqual(importer.load_records(raw), [{"name": "Doe, Jane", "region": "west", "amount": "100"}])

    def test_import_contacts_preserves_quoted_names(self):
        raw = 'name,region,amount\\n"Doe, Jane",west,100\\n"Lee, Amy",east,75\\n'
        self.assertEqual(importer.import_contacts(raw), [("Doe, Jane", "west"), ("Lee, Amy", "east")])

    def test_report_summary_with_quoted_names(self):
        raw = 'name,region,amount\\n"Doe, Jane",west,100\\n"Smith, Bob",west,50\\n"Lee, Amy",east,75\\n'
        self.assertEqual(report.summarize_by_region(raw), {"east": 75, "west": 150})


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    """Migrate all callers directly to parse_csv, delete retired symbols, and update tests."""
    repo = ws / "repo"
    (repo / "src" / "parser.py").write_text(FIXED_PARSER, encoding="utf-8")
    (repo / "src" / "importer.py").write_text(FIXED_IMPORTER, encoding="utf-8")
    (repo / "src" / "report.py").write_text(FIXED_REPORT, encoding="utf-8")
    (repo / "tests" / "test_pipeline.py").write_text(FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Migrated src/importer.py and src/report.py directly to parse_csv, deleted parse_v1, "
            "parse_records, ENABLE_LEGACY_MODE, and legacy_compat from src/parser.py, and updated "
            "tests/test_pipeline.py to verify all consumers on quoted CSV inputs."
        ),
    }
