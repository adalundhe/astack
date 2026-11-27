---
description: "Replaces a destructive one-step SQLite column rename with an additive expand-phase migration and dual-write service that keeps pre-change non-privileged readers, writers, and rollbacks working."
expected_outcome: "Reads safe-to-deploy/SKILL.md, changes repo/src/schema.py to add contact_email and backfill without dropping/renaming email, updates repo/src/service_v2.py to dual-write email and contact_email and fall back on read, preserves repo/src/reader_v1.py unchanged, and adds mixed-version non-privileged reader and rollback tests."
max_turns: 16
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Bash, Edit, Write]
---

`/astack:go` We are migrating the `users` table in `./repo` from `email` to `contact_email` with zero downtime during a rolling deploy.
- `./repo/src/reader_v1.py` represents the currently deployed v1 service pods (and any release we might roll back to) and must remain untouched.
- `./repo/src/schema.py` currently renames `email` to `contact_email` in one destructive step, breaking live v1 readers, v1 writers, and rollbacks.
- `./repo/src/service_v2.py` is the incoming v2 service.

Update `./repo/src/schema.py` and `./repo/src/service_v2.py` so pre-change v1 workloads (including read-only non-privileged readers), new v2 workloads, and rollbacks to v1 all continue working across the rollout, and add mixed-version and rollback tests in `./repo/tests/test_migration.py`.
