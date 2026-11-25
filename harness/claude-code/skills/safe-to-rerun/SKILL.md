---
name: safe-to-rerun
description: "Make state-changing operations idempotent and crash-recoverable so reruns end in the right state. Use when writing or reviewing commands, migrations, deploy steps, jobs, or retries."
disable-model-invocation: true
---

# Safe to rerun

Make state-changing operations end in the right state regardless of reruns or mid-run crashes. For keeping live workloads and rollbacks working across deploy cutovers, also apply **safe-to-deploy**.

## Start with

1. **Converge from current state,** because a prior run may have crashed halfway. Inspect live state, diff against the target, and apply only what's missing.
2. **Make leftovers detectable as stale**. Tag lock files, temp files, partial records, and claimed jobs with owner, PID, lease/expiry, or checksum. That lets the next run identify and clean up crashed state.
3. **Write atomically:** write to a temp file then rename into place so readers never see partial files. Commit multi-step updates in one transaction or all-or-nothing step.
4. **Give retried requests an identity** (e.g. an idempotency key) so retries deduplicate instead of running twice.
5. **Test crash recovery:** run twice, kill at each intermediate step, rerun, and assert final state (**full-spectrum-testing**). If outcome depends on crash point, add reconciliation.

## Watch for

- steps assuming a clean slate (creating without checking existence, blindly appending duplicates, untracked migrations);
- in-place file rewrites or multi-step updates lacking transactions;
- unrecognizable leftovers (lock files without owner/expiry, orphaned temp files, claimed jobs without leases);
- retried side-effecting requests with no idempotency key (double charges, duplicate emails or rows);
- progress tracked only in volatile memory.

**The test:** what happens if this runs twice, or gets killed at any line and run again?

## When it doesn't fit

- read-only operations;
- operations intentionally creating distinct actions per call, each with its own unique request identity.

**Showing it:** run it twice, or kill it mid-run and rerun, and show the corrupted result (duplicate row, half-written file, stuck lock, double charge).

Referenced skills: `safe-to-deploy` (`${CLAUDE_SKILL_DIR}/../safe-to-deploy/SKILL.md`), `full-spectrum-testing` (`${CLAUDE_SKILL_DIR}/../full-spectrum-testing/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's make-operations-idempotent principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
