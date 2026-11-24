---
name: no-shared-writes
description: "Keep concurrent threads, processes, services and agents from writing the same state: give each its own, merge where it's read, serialize only for a real invariant. Use when writing or reviewing concurrent code or parallel work, and before adding a lock."
---

# No shared writes

Keep concurrent writers from sharing state, so they don't need locks.

## Start with

1. **Give each writer its own** file, key, partition, branch, folder or queue, and merge where it's read. Two writers changing separate fields of one file still share the file.
2. **Serialize only for a real invariant** of one shared target, and then structurally: a single owning writer, sequential phases, compare-and-swap, an append-only log.
3. **Default to lockless designs.** Use a lock or mutex where measurement shows it fits better here (**benchmarking**).
4. **Don't rely on instructions.** "Only one writer at a time", in a comment or a prompt, prevents nothing.
5. **Test under contention:** the most concurrent writers the claim covers, checking races, deadlock and livelock (**full-spectrum-testing**).

## Watch for

- two or more threads, processes, services or agents writing the same file, row, key, object or branch;
- locks, mutexes and semaphores, and comments or instructions saying only one may write;
- read-modify-write on shared state without compare-and-swap;
- one file or object where several writers each update their own part;
- shared mutable collections and globals.

**The test:** do these writers need to change one thing together, or is each publishing its own facts?

## When it doesn't fit

- one shared target that holds a real invariant, serialized structurally as in Start with;
- many readers of data nobody writes;
- writes the platform serializes with a documented guarantee, used as designed: a database transaction, an atomic append, an atomic rename;
- an approach the evidence here favours: when unsure, try both and measure (**ab-test**), and say why you chose it.

**Showing it:** force the interleaving, or flood it with concurrent writers, and show the lost or corrupted write.

<!-- Adapts pstack's separate-before-serializing-shared-state principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
