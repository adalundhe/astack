---
name: safe-to-rerun
description: "Make state-changing operations idempotent and crash-recoverable so rerunning or stopping halfway still ends in the right state. Use when writing or reviewing commands, migrations, deploy steps, jobs, or retries."
---

# Safe to rerun

Make state-changing operations end in the right state regardless of how many times they run or where a previous run crashed. For keeping live workloads and rollbacks working across deploy steps and breaking cutovers, also apply **safe-to-deploy**.

## Start with

1. **Converge from current state,** not what a previous run was supposed to do: inspect current state, diff against the target, and apply only what's missing.
2. **Make leftovers detectable as stale.** Any artifact a run leaves behind (lock file, temp file, partial record, claimed job) must include enough metadata (owner, PID, lease/expiry, checksum) for the next run to recognize and clean up crashed state.
3. **Write atomically:** write to a temporary file then rename into place so readers never see partial files. Commit multi-step changes in a transaction or all-or-nothing step.
4. **Give retried requests an identity** (e.g. an idempotency key) so retries are deduplicated instead of applied twice.
5. **Test crash recovery:** run the operation twice, kill it at each intermediate step, rerun, and assert the final state (**full-spectrum-testing**). If outcome depends on crash point, add reconciliation.

## Watch for

- steps assuming a clean slate (creating without checking existence, blindly appending duplicates, untracked migrations);
- in-place file rewrites or multi-step updates lacking transactions;
- unrecognizable leftovers (lock files without owner/expiry, orphaned temp files, claimed jobs without leases);
- retried side-effecting requests with no idempotency key (double charges, duplicate emails/rows);
- progress tracked only in volatile memory.

**The test:** what happens if this runs twice, or gets killed at any line and run again?

## When it doesn't fit

- read-only operations;
- operations intentionally creating distinct actions per call (each with its own unique request identity, e.g. placing a separate order);
- an alternative backed by measurements (**ab-test**), with the trade-off documented.

**Showing it:** run it twice, or kill it mid-run and rerun, and show the corrupted result (duplicate row, half-written file, stuck lock, double charge).

Referenced skills: `safe-to-deploy` (`../safe-to-deploy/SKILL.md`), `full-spectrum-testing` (`../full-spectrum-testing/SKILL.md`), `ab-test` (`../ab-test/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's make-operations-idempotent principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
