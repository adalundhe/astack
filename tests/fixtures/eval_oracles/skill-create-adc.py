"""Separated offline oracle for `skill-create-adc`."""
from __future__ import annotations

from pathlib import Path

AD_2_CONTENT = """---
ad_number: 2
name: Durable Postgres idempotency keys
description: Replace the in-memory idempotency key set in PaymentLedger with a transactional Postgres idempotency_keys table enforcing a 24-hour TTL.
---

# AD-2: Durable Postgres idempotency keys

## Status

Accepted (2026-11-26).

**Related:** AD-1 (charge amounts stored alongside idempotency entries remain integer `amount_cents`).

## Context

During a rolling restart on 2026-11-18 under 120 req/s peak load, `PaymentLedger._seen_keys` in `repo/src/ledger.py` dropped 412 in-flight idempotency keys. Webhook retries landing on fresh pods executed 3 duplicate customer charges because key history lived only in process memory.

## Decision

Replace `PaymentLedger._seen_keys` with a Postgres table committed in the same transaction as the ledger debit:

```sql
CREATE TABLE idempotency_keys (
  tenant_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  payload_hash TEXT NOT NULL,
  response_body JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, idempotency_key)
);
```

- On charge creation, execute `INSERT INTO idempotency_keys ... ON CONFLICT (tenant_id, idempotency_key) DO NOTHING`.
- If a row already exists with the same `payload_hash`, return the stored `response_body` without debiting again.
- If a row already exists with a different `payload_hash`, reject the request with HTTP 409 Conflict.
- Run a daily batched purge deleting rows older than 24 hours.

## Non-goals

- Cross-region active-active deduplication.
- Retaining idempotency keys beyond the 24-hour window.

## Costs accepted

- +2.4 ms p95 write latency on charge creation at 120 req/s.
- ~18 MB/day table growth prior to daily 24-hour TTL pruning.
- Operational upkeep of one scheduled daily purge job.

## Alternatives considered

- **Redis `SETNX` with 24-hour TTL:** Diverges by storing deduplication state outside the ledger transaction; rejected because async replica failover can drop acknowledged keys during replication lag and still produce duplicate charges.
- **Client-generated sequence numbers:** Diverges by shifting state tracking to callers; rejected because third-party webhook providers cannot guarantee monotonic client sequences.

## Acceptance criteria

- Repeating `(tenant_id, idempotency_key)` with an identical payload returns the original recorded result without creating a second charge, including across process restarts.
- Repeating a key with a different `payload_hash` returns HTTP 409 Conflict and performs zero writes.
- Rows older than 24 hours are purged in batches without blocking active inserts.

## Tests

- `test_restart_dedup`: persists a charge, restarts the ledger instance, retries the same key, and asserts a single recorded charge.
- `test_payload_conflict`: submits the same key with a modified `amount_cents` and asserts HTTP 409 Conflict.
- `test_concurrent_insert_race`: dispatches concurrent writers with the same key and asserts exactly one charge row commits.

## Evidence

- 2026-11-18 rolling-restart incident postmortem (412 lost keys, 3 duplicate charges).
- Staging `pgbench` profile at 120 req/s (+2.4 ms p95 write overhead).
- Existing implementation: `repo/src/ledger.py` (`PaymentLedger.record_charge`).
"""


def apply(ws: Path) -> dict[str, object]:
    """Publish AD_2.md under program/astack_home/payments/architecture/ without touching AD_1.md or repo/."""
    ad2 = ws / "program" / "astack_home" / "payments" / "architecture" / "AD_2.md"
    ad2.write_text(AD_2_CONTENT, encoding="utf-8")
    return {
        "final_text": (
            "Published AD-2 (Durable Postgres idempotency keys) to "
            "`program/astack_home/payments/architecture/AD_2.md`. Preserved `AD_1.md` and left `./repo` untouched."
        ),
    }
