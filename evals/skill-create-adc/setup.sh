#!/bin/bash
set -euo pipefail
mkdir -p program/astack_home/payments/architecture repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/src/ledger.py <<'EOF'
"""In-memory payment charge ledger (loses idempotency keys on restart)."""
from __future__ import annotations


class PaymentLedger:
    def __init__(self) -> None:
        self._seen_keys: set[str] = set()
        self._charges: list[tuple[str, int]] = []

    def record_charge(self, idempotency_key: str, amount_cents: int) -> bool:
        if idempotency_key in self._seen_keys:
            return False
        self._seen_keys.add(idempotency_key)
        self._charges.append((idempotency_key, amount_cents))
        return True
EOF

cat > repo/tests/test_ledger.py <<'EOF'
import unittest
from src.ledger import PaymentLedger


class LedgerTest(unittest.TestCase):
    def test_deduplicates_within_process(self):
        ledger = PaymentLedger()
        self.assertTrue(ledger.record_charge("k1", 1500))
        self.assertFalse(ledger.record_charge("k1", 1500))


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial payment ledger"

cat > program/astack_home/payments/architecture/AD_1.md <<'EOF'
---
ad_number: 1
name: Integer-cent money representation
description: Store and compute all payment amounts as signed 64-bit integer cents rather than floating-point dollars.
---

# AD-1: Integer-cent money representation

## Status

Accepted (2026-01-15). Built (2026-01-20).

## Context

Floating-point summation across 10,000 daily invoice lines drifted by $0.03 per settlement batch.

## Decision

Represent every amount as integer `amount_cents: int` across storage and API boundaries.

## Non-goals

Multi-currency FX conversion rounding rules.

## Costs accepted

Formatters must divide by minor-unit scale at display boundaries.

## Alternatives considered

Python `Decimal` everywhere was rejected due to 4x serialization overhead in hot settlement loops.

## Acceptance criteria

Sum of 333 charges of 29 cents equals exactly 9657 cents with zero rounding error.

## Tests

`test_exact_integer_sum` asserts exact integer arithmetic across repeating prime cent values.

## Evidence

Benchmark in `repo/src/ledger.py` settlement profile (2026-01-14).
EOF

python3 -c 'import hashlib, pathlib; p = pathlib.Path("program/astack_home/payments/architecture/AD_1.md"); pathlib.Path("program/ad1_sha256.txt").write_text(hashlib.sha256(p.read_bytes()).hexdigest() + "\n")'

cat > program/decision-brief.md <<'EOF'
# Settled Architecture Decision Brief (project: payments)

**Confirmation:** Settled and user-confirmed on 2026-11-26 — publish now as the next AD document.

- **Name:** Durable Postgres idempotency keys
- **One-line decision:** Replace the process-local `_seen_keys` set in `repo/src/ledger.py` with a Postgres `idempotency_keys` table enforcing a unique `(tenant_id, idempotency_key)` constraint with a 24-hour TTL.
- **Related:** AD-1 (charge amounts recorded alongside idempotency entries remain integer `amount_cents`).
- **Context:** During a rolling restart on 2026-11-18 at 120 req/s peak load, `PaymentLedger._seen_keys` in `repo/src/ledger.py` dropped 412 in-flight keys, causing 3 duplicate customer charges when webhook retries hit fresh pods.
- **Decision mechanisms:**
  - Table `idempotency_keys(tenant_id TEXT, idempotency_key TEXT, payload_hash TEXT, response_body JSONB, created_at TIMESTAMPTZ, PRIMARY KEY (tenant_id, idempotency_key))`.
  - Write path uses `INSERT ... ON CONFLICT (tenant_id, idempotency_key) DO NOTHING` inside the same Postgres transaction as the ledger debit.
  - Payload hash mismatch on an existing key returns HTTP 409 Conflict instead of replaying a mismatched charge.
  - Daily batched delete removes rows older than 24 hours.
- **Non-goals:** Cross-region active-active deduplication; extending idempotency windows beyond 24 hours.
- **Costs accepted:** +2.4 ms p95 write latency on charge creation; ~18 MB/day table growth before 24-hour TTL pruning; scheduled daily purge job.
- **Alternatives considered:**
  - **Redis `SETNX` with 24h TTL:** Rejected because async replica failover can drop acknowledged keys within the replication lag window, reproducing duplicate charges.
  - **Client-generated sequence numbers only:** Rejected because third-party payment webhooks cannot guarantee monotonic client sequence tracking.
- **Acceptance criteria:**
  - Duplicate `(tenant_id, idempotency_key)` with identical payload returns the original recorded result without creating a second charge, including across process restarts.
  - Same key with a different `payload_hash` fails with conflict error.
  - Keys older than 24 hours are purged without blocking active writes.
- **Tests:**
  - `test_restart_dedup`: simulates pod restart and verifies retry with same key charges once.
  - `test_payload_conflict`: verifies same key with altered `amount_cents` raises conflict.
  - `test_concurrent_insert_race`: two threads racing on the same key produce exactly one charge row.
- **Evidence:**
  - Incident postmortem from 2026-11-18 (412 lost keys, 3 duplicate charges).
  - Staging pgbench run showing +2.4 ms p95 overhead at 120 req/s.
  - Current code path: `repo/src/ledger.py` (`PaymentLedger.record_charge`).
EOF
