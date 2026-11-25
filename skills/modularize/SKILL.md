---
name: modularize
description: "Split monolithic packages, files, or functions into single-purpose modules behind narrow interfaces via a reviewed smallest-behavior proof of concept, dagify-batched parallel migration, and simplify-me/yagni scope reduction—validated at every stage with vectored review. Use when code is too large or tangled to change safely."
disable-model-invocation: true
---

# Modularize

Split monolithic code into single-purpose modules that can be tested and swapped independently—proving the pattern on the smallest working slice first, migrating in reviewed batches, and trimming down to the minimum implementation that preserves parity.

## Design the seams

1. **Map responsibilities** (**how-it-works**): list each job, the data it owns, call graph, and where state lives (**show-the-states**).
2. **Pin behavior first:** add external behavior tests that pass before the split and must stay green unchanged afterward (**tests-assert-behaviour**).
3. **Cut along domain seams, not technical layers.** Group code by job and owned data. Untangle shared mutable state and hidden state machines first (**minimize-state-stores**, **no-shared-writes**, **no-implicit-states**).
4. **Keep each module tight:** one job, owned data, a narrow explicit interface, hidden internals, acyclic one-way dependencies, and core logic separated from outer I/O (**check-your-boundaries**). Only introduce formal traits/interfaces at real boundaries, and match existing repo conventions.

## Execute in three reviewed stages

5. **Prove the pattern on the smallest working slice:** migrate the smallest cohesive unit of working behavior end to end (proof of concept), run pinning tests and checks, and validate functional and behavioral parity with vectored **review** before scaling out.
6. **Swarm-migrate in large **dagify** batches:** plan the remaining migration as non-overlapping **dagify** batches run in parallel (**lead**)—workers in isolated **slates** in-memory VFS volumes (`https://github.com/hyper-light/slates`, preferred when available) or git worktrees, reviewers verifying worker-submitted batches read-only in **slates** volumes or review worktrees (sending fixes back to workers to implement and resubmit), under **lead**'s watch/swap clocks (`LANES.md` + `astack-status` every `check_in_minutes`, wind-down reminder, fresh successor on overdue runs). Update callers per batch, separate moves from behavior changes, and validate parity and **blast-radius** seams via vectored **review** after each batch.
7. **Trim scope with **simplify-me** and **yagni**:** once all batches land, run **simplify-me** and **yagni** to delete legacy paths, dead shims, and scaffolding, cutting implementation size to the minimum that meets requirements, correctness, and parity—confirmed with a final vectored **review** (and **benchmarking** where latency or throughput matters). Include a Mermaid dependency diagram for review.

**Don't split:**
- purely by line count (a long single-purpose file like a lookup or transition table belongs together);
- one cohesive idea across multiple files where splitting hurts readability;
- just to introduce a single-implementation interface with no real boundary behind it.
