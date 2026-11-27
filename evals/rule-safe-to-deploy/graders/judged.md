---
type: llm
---

Evaluate the database migration and service changes against `safe-to-deploy`.

PASS if all of these hold:
- Replaces the destructive `RENAME COLUMN` in `./repo/src/schema.py` with an additive expand-phase migration that adds `contact_email` and backfills from `email` while keeping `email` intact.
- Updates `./repo/src/service_v2.py` to dual-write both `email` and `contact_email` and handle rows written by v1 (e.g. `COALESCE(contact_email, email)` or sync triggers).
- Leaves `./repo/src/reader_v1.py` intact as the pre-change workload.
- Adds mixed-version tests in `./repo/tests/test_migration.py` verifying read-only/pre-change v1 readers, v2 writers, and v1 rollback writers against the migrated schema.

FAIL otherwise.
