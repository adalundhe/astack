#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/monolith.py <<'EOF'
"""Tangled batch-ingestion monolith mixing parsing, domain validation, and storage formatting."""
from __future__ import annotations

from datetime import date
import json
import re
from typing import Any

ALLOWED_CURRENCIES: frozenset[str] = frozenset({"USD", "EUR", "GBP"})
SKU_PATTERN = re.compile(r"^[A-Z]{2,4}-\d{3,6}$")
MAX_BATCH_RECORDS = 500
FIELD_COUNT = 6


class ParseError(ValueError):
    """Raised when a raw input line cannot be parsed."""


class ValidationError(ValueError):
    """Raised when a parsed record violates domain invariants."""


class StorageFormatError(ValueError):
    """Raised when an unsupported storage output format is requested."""


def _strip_inline_comment(raw_line: str) -> str:
    text = raw_line.strip()
    if not text or text.startswith("#"):
        return ""
    return text


def _parse_positive_int_field(raw_value: str, field_name: str, line_no: int) -> int:
    cleaned = raw_value.strip()
    if not cleaned:
        raise ParseError(f"line {line_no}: missing {field_name}")
    try:
        return int(cleaned)
    except ValueError as exc:
        raise ParseError(f"line {line_no}: invalid integer for {field_name}: {cleaned!r}") from exc


def parse_line(raw_line: str, line_no: int) -> dict[str, Any] | None:
    """Parse one pipe-delimited ledger record line into a raw record dict."""
    cleaned = _strip_inline_comment(raw_line)
    if not cleaned:
        return None
    parts = [part.strip() for part in cleaned.split("|")]
    if len(parts) != FIELD_COUNT:
        raise ParseError(
            f"line {line_no}: expected {FIELD_COUNT} pipe-separated fields, got {len(parts)}"
        )
    record_id, sku, raw_qty, raw_unit_cents, currency, raw_date = parts
    if not record_id:
        raise ParseError(f"line {line_no}: empty record_id")
    qty = _parse_positive_int_field(raw_qty, "qty", line_no)
    unit_cents = _parse_positive_int_field(raw_unit_cents, "unit_cents", line_no)
    return {
        "record_id": record_id,
        "sku": sku.upper(),
        "qty": qty,
        "unit_cents": unit_cents,
        "currency": currency.upper(),
        "booked_date": raw_date,
        "line_no": line_no,
    }


def parse_batch(raw_text: str) -> list[dict[str, Any]]:
    """Parse a multi-line pipe-delimited text batch into raw record dictionaries."""
    if not isinstance(raw_text, str):
        raise ParseError("raw_text must be a string")
    records: list[dict[str, Any]] = []
    for idx, raw_line in enumerate(raw_text.splitlines(), start=1):
        parsed = parse_line(raw_line, idx)
        if parsed is not None:
            records.append(parsed)
    return records


def _validate_iso_date(raw_date: str, record_id: str) -> str:
    try:
        parsed = date.fromisoformat(raw_date)
    except ValueError as exc:
        raise ValidationError(f"record {record_id}: invalid ISO date {raw_date!r}") from exc
    if parsed.year < 2020 or parsed.year > 2035:
        raise ValidationError(f"record {record_id}: date {raw_date!r} outside allowed range 2020..2035")
    return parsed.isoformat()


def validate_record(record: dict[str, Any]) -> dict[str, Any]:
    """Validate domain constraints for one parsed record and compute its line total."""
    record_id = str(record.get("record_id", "")).strip()
    if not record_id:
        raise ValidationError("record_id must not be empty")
    sku = str(record.get("sku", "")).strip().upper()
    if not SKU_PATTERN.fullmatch(sku):
        raise ValidationError(f"record {record_id}: invalid SKU {sku!r}")
    qty = record.get("qty")
    if isinstance(qty, bool) or not isinstance(qty, int) or qty <= 0:
        raise ValidationError(f"record {record_id}: qty must be a positive integer")
    unit_cents = record.get("unit_cents")
    if isinstance(unit_cents, bool) or not isinstance(unit_cents, int) or unit_cents <= 0:
        raise ValidationError(f"record {record_id}: unit_cents must be a positive integer")
    currency = str(record.get("currency", "")).strip().upper()
    if currency not in ALLOWED_CURRENCIES:
        raise ValidationError(f"record {record_id}: unsupported currency {currency!r}")
    booked_date = _validate_iso_date(str(record.get("booked_date", "")), record_id)
    line_total_cents = qty * unit_cents
    return {
        "record_id": record_id,
        "sku": sku,
        "qty": qty,
        "unit_cents": unit_cents,
        "line_total_cents": line_total_cents,
        "currency": currency,
        "booked_date": booked_date,
    }


def validate_batch(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate every record in a batch, rejecting duplicate IDs and oversized batches."""
    if len(records) > MAX_BATCH_RECORDS:
        raise ValidationError(f"batch exceeds maximum of {MAX_BATCH_RECORDS} records")
    seen_ids: set[str] = set()
    validated: list[dict[str, Any]] = []
    for raw_record in records:
        clean = validate_record(raw_record)
        rec_id = clean["record_id"]
        if rec_id in seen_ids:
            raise ValidationError(f"duplicate record_id: {rec_id}")
        seen_ids.add(rec_id)
        validated.append(clean)
    return validated


def compute_currency_totals(records: list[dict[str, Any]]) -> dict[str, int]:
    """Aggregate line_total_cents per currency in sorted key order."""
    totals: dict[str, int] = {}
    for rec in records:
        cur = str(rec["currency"])
        totals[cur] = totals.get(cur, 0) + int(rec["line_total_cents"])
    return dict(sorted(totals.items()))


def format_ndjson(records: list[dict[str, Any]]) -> str:
    """Serialize validated records as deterministic sorted-key NDJSON lines."""
    ordered = sorted(records, key=lambda r: (str(r["booked_date"]), str(r["record_id"])))
    lines = [json.dumps(rec, sort_keys=True, separators=(",", ":")) for rec in ordered]
    return "\n".join(lines) + ("\n" if lines else "")


def format_summary_tsv(records: list[dict[str, Any]]) -> str:
    """Serialize per-currency count and total_cents summary as TSV with header."""
    counts: dict[str, int] = {}
    totals: dict[str, int] = {}
    for rec in records:
        cur = str(rec["currency"])
        counts[cur] = counts.get(cur, 0) + 1
        totals[cur] = totals.get(cur, 0) + int(rec["line_total_cents"])
    rows = ["currency\tcount\ttotal_cents"]
    for cur in sorted(totals):
        rows.append(f"{cur}\t{counts[cur]}\t{totals[cur]}")
    return "\n".join(rows) + "\n"


def serialize_batch(records: list[dict[str, Any]], output_format: str = "ndjson") -> str:
    """Dispatch storage serialization by requested output format."""
    fmt = output_format.strip().lower()
    if fmt == "ndjson":
        return format_ndjson(records)
    if fmt == "tsv":
        return format_summary_tsv(records)
    raise StorageFormatError(f"unsupported output format: {output_format!r}")


def process_batch(raw_text: str, output_format: str = "ndjson") -> dict[str, Any]:
    """Run full ingestion pipeline: parse -> validate -> aggregate -> serialize."""
    parsed = parse_batch(raw_text)
    validated = validate_batch(parsed)
    totals = compute_currency_totals(validated)
    payload = serialize_batch(validated, output_format=output_format)
    return {
        "count": len(validated),
        "totals_by_currency": totals,
        "payload": payload,
    }
EOF

cat > repo/tests/test_monolith.py <<'EOF'
import json
import unittest

from src.monolith import (
    ParseError,
    StorageFormatError,
    ValidationError,
    format_ndjson,
    format_summary_tsv,
    parse_batch,
    process_batch,
    validate_batch,
)

SAMPLE_BATCH = """
# Ledger batch export
rec-2 | BK-1002 | 3 | 1200 | eur | 2026-11-20
rec-1 | AP-0042 | 2 | 1500 | usd | 2026-11-19

rec-3 | BK-1009 | 1 | 500 | USD | 2026-11-20
"""


class MonolithBehaviorTest(unittest.TestCase):
    def test_process_batch_ndjson_roundtrip(self):
        result = process_batch(SAMPLE_BATCH, output_format="ndjson")
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["totals_by_currency"], {"EUR": 3600, "USD": 3500})
        lines = [json.loads(ln) for ln in result["payload"].strip().splitlines()]
        self.assertEqual([r["record_id"] for r in lines], ["rec-1", "rec-2", "rec-3"])
        self.assertEqual(lines[0]["line_total_cents"], 3000)

    def test_process_batch_tsv_summary(self):
        result = process_batch(SAMPLE_BATCH, output_format="tsv")
        expected = "currency\tcount\ttotal_cents\nEUR\t1\t3600\nUSD\t2\t3500\n"
        self.assertEqual(result["payload"], expected)

    def test_parse_errors_on_malformed_lines(self):
        with self.assertRaises(ParseError):
            parse_batch("only|three|cols")
        with self.assertRaises(ParseError):
            parse_batch("r1|AB-123|two|100|USD|2026-11-01")

    def test_validation_rejects_bad_sku_currency_qty_and_duplicates(self):
        with self.assertRaises(ValidationError):
            process_batch("r1|badsku|1|100|USD|2026-11-01")
        with self.assertRaises(ValidationError):
            process_batch("r1|AB-123|1|100|JPY|2026-11-01")
        with self.assertRaises(ValidationError):
            process_batch("r1|AB-123|0|100|USD|2026-11-01")
        with self.assertRaises(ValidationError):
            process_batch("r1|AB-123|1|100|USD|2026-11-01\nr1|AB-124|2|200|USD|2026-11-01")

    def test_unknown_output_format_raises(self):
        with self.assertRaises(StorageFormatError):
            process_batch("r1|AB-123|1|100|USD|2026-11-01", output_format="xml")

    def test_direct_stage_helpers_remain_exported(self):
        parsed = parse_batch("r1|AB-123|2|250|GBP|2026-11-02")
        validated = validate_batch(parsed)
        self.assertIn('"line_total_cents":500', format_ndjson(validated))
        self.assertIn("GBP\t1\t500", format_summary_tsv(validated))


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial tangled monolith with pinning tests"
git -C repo rev-parse HEAD > program/base_sha.txt
