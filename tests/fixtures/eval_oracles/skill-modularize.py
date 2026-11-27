"""Separated offline oracle for `skill-modularize`."""
from __future__ import annotations

from pathlib import Path

PARSER_PY = '''"""Raw pipe-delimited batch record parser."""
from __future__ import annotations

from typing import Any

FIELD_COUNT = 6


class ParseError(ValueError):
    """Raised when a raw input line cannot be parsed."""


def _parse_int_field(raw_value: str, field_name: str, line_no: int) -> int:
    cleaned = raw_value.strip()
    if not cleaned:
        raise ParseError(f"line {line_no}: missing {field_name}")
    try:
        return int(cleaned)
    except ValueError as exc:
        raise ParseError(f"line {line_no}: invalid integer for {field_name}: {cleaned!r}") from exc


def parse_line(raw_line: str, line_no: int) -> dict[str, Any] | None:
    """Parse one non-comment pipe-delimited ledger record line."""
    text = raw_line.strip()
    if not text or text.startswith("#"):
        return None
    parts = [part.strip() for part in text.split("|")]
    if len(parts) != FIELD_COUNT:
        raise ParseError(f"line {line_no}: expected {FIELD_COUNT} pipe-separated fields, got {len(parts)}")
    record_id, sku, raw_qty, raw_unit_cents, currency, raw_date = parts
    if not record_id:
        raise ParseError(f"line {line_no}: empty record_id")
    return {
        "record_id": record_id,
        "sku": sku.upper(),
        "qty": _parse_int_field(raw_qty, "qty", line_no),
        "unit_cents": _parse_int_field(raw_unit_cents, "unit_cents", line_no),
        "currency": currency.upper(),
        "booked_date": raw_date,
        "line_no": line_no,
    }


def parse_batch(raw_text: str) -> list[dict[str, Any]]:
    """Parse multi-line pipe-delimited batch text into raw record dicts."""
    if not isinstance(raw_text, str):
        raise ParseError("raw_text must be a string")
    records: list[dict[str, Any]] = []
    for idx, raw_line in enumerate(raw_text.splitlines(), start=1):
        parsed = parse_line(raw_line, idx)
        if parsed is not None:
            records.append(parsed)
    return records
'''

VALIDATOR_PY = '''"""Domain validation and currency aggregation for ledger records."""
from __future__ import annotations

from datetime import date
import re
from typing import Any

ALLOWED_CURRENCIES: frozenset[str] = frozenset({"USD", "EUR", "GBP"})
SKU_PATTERN = re.compile(r"^[A-Z]{2,4}-\\d{3,6}$")
MAX_BATCH_RECORDS = 500


class ValidationError(ValueError):
    """Raised when a parsed record violates domain invariants."""


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
    return {
        "record_id": record_id,
        "sku": sku,
        "qty": qty,
        "unit_cents": unit_cents,
        "line_total_cents": qty * unit_cents,
        "currency": currency,
        "booked_date": booked_date,
    }


def validate_batch(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate every record in a batch, rejecting duplicates and oversized batches."""
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
'''

STORAGE_PY = '''"""Storage formatters for validated ledger batches."""
from __future__ import annotations

import json
from typing import Any


class StorageFormatError(ValueError):
    """Raised when an unsupported storage output format is requested."""


def format_ndjson(records: list[dict[str, Any]]) -> str:
    """Serialize validated records as deterministic sorted-key NDJSON lines."""
    ordered = sorted(records, key=lambda r: (str(r["booked_date"]), str(r["record_id"])))
    lines = [json.dumps(rec, sort_keys=True, separators=(",", ":")) for rec in ordered]
    return "\\n".join(lines) + ("\\n" if lines else "")


def format_summary_tsv(records: list[dict[str, Any]]) -> str:
    """Serialize per-currency count and total_cents summary as TSV with header."""
    counts: dict[str, int] = {}
    totals: dict[str, int] = {}
    for rec in records:
        cur = str(rec["currency"])
        counts[cur] = counts.get(cur, 0) + 1
        totals[cur] = totals.get(cur, 0) + int(rec["line_total_cents"])
    rows = ["currency\\tcount\\ttotal_cents"]
    for cur in sorted(totals):
        rows.append(f"{cur}\\t{counts[cur]}\\t{totals[cur]}")
    return "\\n".join(rows) + "\\n"


def serialize_batch(records: list[dict[str, Any]], output_format: str = "ndjson") -> str:
    """Dispatch storage serialization by requested output format."""
    fmt = output_format.strip().lower()
    if fmt == "ndjson":
        return format_ndjson(records)
    if fmt == "tsv":
        return format_summary_tsv(records)
    raise StorageFormatError(f"unsupported output format: {output_format!r}")
'''

SLIM_MONOLITH_PY = '''"""Public batch-ingestion pipeline coordinating parser, validator, and storage modules."""
from __future__ import annotations

from typing import Any

from src.parser import ParseError, parse_batch, parse_line
from src.storage import StorageFormatError, format_ndjson, format_summary_tsv, serialize_batch
from src.validator import ValidationError, compute_currency_totals, validate_batch, validate_record

__all__ = [
    "ParseError",
    "StorageFormatError",
    "ValidationError",
    "compute_currency_totals",
    "format_ndjson",
    "format_summary_tsv",
    "parse_batch",
    "parse_line",
    "process_batch",
    "serialize_batch",
    "validate_batch",
    "validate_record",
]


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
'''


def apply(ws: Path) -> dict[str, object]:
    """Extract parser.py, validator.py, storage.py and trim monolith.py while keeping public API green."""
    src_dir = ws / "repo" / "src"
    (src_dir / "parser.py").write_text(PARSER_PY, encoding="utf-8")
    (src_dir / "validator.py").write_text(VALIDATOR_PY, encoding="utf-8")
    (src_dir / "storage.py").write_text(STORAGE_PY, encoding="utf-8")
    (src_dir / "monolith.py").write_text(SLIM_MONOLITH_PY, encoding="utf-8")
    return {
        "final_text": (
            "Extracted `src/parser.py`, `src/validator.py`, and `src/storage.py` from `src/monolith.py` "
            "and reduced `src/monolith.py` to a 36-line public facade. All pinning tests in `tests/test_monolith.py` pass unchanged.\n\n"
            "```mermaid\n"
            "flowchart LR\n"
            "  monolith --> parser\n"
            "  monolith --> validator\n"
            "  monolith --> storage\n"
            "```"
        ),
    }
