---
name: safe-to-rerun
description: "Make every state-changing operation end in the right state however often it runs and wherever a previous run stopped. Use when writing or reviewing commands, migrations, deploy and lifecycle steps, jobs, retries and processing loops."
---

# Safe to rerun

Make operations end in the right state however often they run, and wherever a previous run stopped.

## Start with

1. **Work from the state that exists,** not what the last run meant to do: read it, compare with the goal, apply only the difference.
2. **Make leftovers recognisable.** Whatever a run leaves behind (a lock, a temporary file, a half-written record, a claimed job) lets the next run tell it's stale, wherever the last run stopped.
3. **Write, then rename into place,** so no reader sees half a file. Changes that belong together commit together, or not at all.
4. **Give retried requests an identity,** such as an idempotency key, so a repeat is recognised, not applied twice.
5. **Test it:** run it twice; kill it at every step, rerun, and check the end state (**full-spectrum-testing**). If the end state depends on where it stopped, add a step that reconciles it.

## Watch for

- steps that assume a clean start: creating without checking what exists, appending what a rerun appends again, migrations with no record of what ran;
- files written in place, and multi-step changes with no transaction;
- leftovers nothing can recognise as stale: a lock file with no owner or expiry, a temporary file, a claimed job with no lease;
- retried requests with no identity, which charge, send or create twice;
- progress tracked only in memory.

**The test:** what happens if this runs twice, or stops at any line and runs again?

## When it doesn't fit

- read-only operations;
- operations meant to repeat, where each run is a new request with its own identity, such as placing a new order or sending a message again on purpose;
- an approach the evidence here favours: when unsure, try both and measure (**ab-test**), and say why you chose it.

**Showing it:** run it twice, then kill it at each step and rerun, and show the wrong end state: a duplicate row, a half-written file, a stuck lock, a double charge.

<!-- Adapts pstack's make-operations-idempotent principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
