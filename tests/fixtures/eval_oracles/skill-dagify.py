"""Separated offline oracle for `skill-dagify`."""
from __future__ import annotations

from pathlib import Path

DAG_CONTENT = """# Execution DAG: Expense Ingestion Pipeline

## Goal & Scope
Build the four expense ingestion modules against the frozen `ExpenseRecord` contract in `src/models.py` (read-only). Independent module slices run in parallel and converge into the CLI integration slice.

## Dependency Graph

```mermaid
flowchart LR
  T1[T1: Expense Parser] --> T4[T4: Pipeline CLI]
  T2[T2: Expense Validator] --> T4
  T3[T3: Atomic JSONL Storage] --> T4
```

## Explicit Edges
- `T1 -> T4`: CLI invokes `parser.parse_stream` to decode input batches.
- `T2 -> T4`: CLI invokes `validator.validate_records` before persistence.
- `T3 -> T4`: CLI invokes `storage.append_batch` and `storage.load_all`.
- Parallelizable wave: `T1`, `T2`, `T3` share zero writable files and execute concurrently.

## T1: Expense Parser

- **Depends on:** None
- **Description:** Implement CSV and JSONL expense parsing in `src/parser.py` returning `list[ExpenseRecord]`. Reject malformed rows with 1-based line numbers and convert decimal dollar amounts via exact integer arithmetic rather than floats.
- **Implementation guide:** Read `ExpenseRecord` from `src/models.py` (read-only). Support `parse_csv(text)` and `parse_jsonl(text)` using Python stdlib `csv`, `json`, and `decimal.Decimal` scaled by 100 into exact `int` cents. Raise `ParseError(line_number, reason)` on malformed inputs.
- **Acceptance criteria:** Valid CSV and JSONL inputs produce matching `ExpenseRecord` lists with exact integer `amount_cents`; malformed lines report exact 1-based line numbers and never silently skip rows.
- **Tests:** `tests/test_parser.py` covering valid CSV/JSONL, repeating decimal strings (`19.99` -> `1999`), missing columns, invalid JSON, and negative or non-numeric amounts.
- **Touches:**
  - `src/parser.py`
  - `tests/test_parser.py`
  - Reads `src/models.py` (read-only)

## T2: Expense Validator

- **Depends on:** None
- **Description:** Implement domain validation for `ExpenseRecord` batches in `src/validator.py`. Enforce allowed currencies (`USD`, `EUR`, `GBP`), positive integer `amount_cents`, non-empty categories, and duplicate `record_id` rejection.
- **Implementation guide:** Read `ExpenseRecord` from `src/models.py` (read-only). Expose `validate_records(records: Sequence[ExpenseRecord]) -> list[ValidationError]` collecting all violations deterministically in input order without mutating records.
- **Acceptance criteria:** Valid batches return an empty error list; invalid currencies, non-positive amounts, blank categories, and duplicate `record_id` values each return structured errors naming the offending `record_id` and field.
- **Tests:** `tests/test_validator.py` testing valid records, unsupported currency codes, zero/negative/bool amounts, whitespace categories, and duplicate IDs within a batch.
- **Touches:**
  - `src/validator.py`
  - `tests/test_validator.py`
  - Reads `src/models.py` (read-only)

## T3: Atomic JSONL Storage

- **Depends on:** None
- **Description:** Implement append-safe JSONL persistence in `src/storage.py` with atomic file replacement and `record_id` deduplication. Ensure interrupted writes never leave a partially written store file.
- **Implementation guide:** Read `ExpenseRecord` from `src/models.py` (read-only). Implement `ExpenseStore(path)` with `load_all()` and `append_batch(records)` writing to a sibling temporary file, calling `flush()` + `os.fsync()`, and swapping via `os.replace()`. Skip already-stored `record_id` entries idempotently.
- **Acceptance criteria:** Re-running `append_batch` with overlapping `record_id` entries writes each record once; concurrent/aborted temp writes leave the existing store readable and intact.
- **Tests:** `tests/test_storage.py` testing round-trip persistence, idempotent re-ingestion, empty/missing store initialization, and atomic swap preserving prior file on write error.
- **Touches:**
  - `src/storage.py`
  - `tests/test_storage.py`
  - Reads `src/models.py` (read-only)

## T4: Pipeline CLI

- **Depends on:** T1, T2, T3
- **Description:** Wire parser, validator, and storage in `src/cli.py` to expose `ingest` and `summary` commands. Return exit code 0 on valid batches and non-zero with structured error output on parse or validation failures.
- **Implementation guide:** Use stdlib `argparse` with `ingest --format csv|jsonl --input <path> --store <path>` and `summary --store <path>`. Short-circuit before storage writes whenever parse or validation fails, and render totals in integer cents per currency.
- **Acceptance criteria:** `ingest` persists valid CSV/JSONL files and prints counts; invalid batches exit non-zero and leave the store unchanged; `summary` prints exact per-currency totals.
- **Tests:** `tests/test_cli.py` running end-to-end subprocess checks for valid CSV/JSONL ingestion, idempotent re-runs, invalid batch non-zero exit with untouched store, and currency summaries.
- **Touches:**
  - `src/cli.py`
  - `tests/test_cli.py`
  - Reads `src/models.py`, `src/parser.py`, `src/validator.py`, `src/storage.py` (read-only)
"""


def apply(ws: Path) -> dict[str, object]:
    """Write program/DAG.md with disjoint parallel tasks and a valid Mermaid flowchart."""
    (ws / "program" / "DAG.md").write_text(DAG_CONTENT, encoding="utf-8")
    return {
        "final_text": (
            "Wrote the execution graph to `program/DAG.md` with three parallel slices "
            "(T1 parser, T2 validator, T3 storage) carrying disjoint writable paths converging "
            "into T4 CLI, plus a Mermaid flowchart. Left `./repo` untouched."
        ),
    }
