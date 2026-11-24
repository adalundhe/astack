---
name: no-shared-writes
description: "Keep concurrent threads, processes, services, and agents from mutating the same state: isolate per writer, merge on read, and serialize structurally only for true invariants. Use when writing concurrent/parallel code or adding locks."
---

# No shared writes

Avoid shared mutable state across concurrent writers instead of reaching for locks first.

## Start with

1. **Give each writer isolated state:** its own file, key, partition, branch, directory, or queue, merging at read time. Two writers editing different fields of the same file still share a write target.
2. **Serialize structurally only for a real invariant** on one shared target: a single owning writer, sequential phases, compare-and-swap, or an append-only log.
3. **Default to lock-free designs.** Only introduce a mutex or lock when benchmarks show it wins (**benchmarking**).
4. **Never rely on prose for concurrency control.** Comments or agent prompts saying "only one writer at a time" prevent nothing.
5. **Test under peak contention:** run maximum concurrent writers and check for races, deadlocks, and livelocks (**full-spectrum-testing**).

## Watch for

- multiple threads, processes, services, or agents writing the same file, row, key, object, or git branch;
- locks, mutexes, semaphores, or prose rules instructing single-writer access;
- read-modify-write sequences on shared state without atomic compare-and-swap;
- multiple writers updating separate sections of one shared file or object;
- shared mutable globals or collections.

**The test:** do these writers truly need to coordinate on a single invariant, or can each publish its own output independently?

## When it doesn't fit

- one shared target enforcing a real invariant, serialized structurally per `Start with`;
- concurrent readers of immutable data;
- writes serialized with documented platform guarantees (database transactions, atomic append, atomic rename);
- an alternative backed by measurements (**ab-test**), with the trade-off documented.

**Showing it:** force a bad interleaving or flood the target with concurrent writers and demonstrate lost or corrupted writes.

<!-- Adapts pstack's separate-before-serializing-shared-state principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
