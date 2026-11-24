---
name: modularize
description: "Split monolithic packages, files, or functions into single-purpose modules behind narrow interfaces in the repo's style, without needless abstraction. Use when code is too large or tangled to change safely."
disable-model-invocation: true
---

# Modularize

Split monolithic code into single-purpose modules that can be tested and swapped independently, without adding unnecessary layers.

1. **Map current responsibilities** (**how-it-works**): list each job, the data it owns, call graph, and where state lives (**show-the-states**).
2. **Pin behavior first:** add external behavior tests that pass before the split and must stay green unchanged afterward (**tests-assert-behaviour**).
3. **Cut along domain seams, not technical layers.** Group code by the job it performs and the data it owns. Untangle shared mutable state and hidden state machines between groups first (**minimize-state-stores**, **no-shared-writes**, **no-implicit-states**).
4. **Keep each module tight:** one job, owned data, a small explicit interface of functions and types, internals hidden, acyclic one-way dependencies. Keep core logic in plain functions and I/O in a thin outer shell (**check-your-boundaries**).
5. **Swap via clean signatures, not extra wrapper layers.** Only introduce formal traits/interfaces/protocols at real boundaries (I/O, external services, or an existing second implementation), and prefer composition over inheritance.
6. **Match the repo's conventions:** keep existing folder layout, naming, error handling, and domain terminology. Don't introduce a new architectural style in one corner.
7. **Move incrementally,** one module at a time, staying green at each step. Update callers in the same change with no compatibility shims (**yagni**), keep behavior changes separate, and confirm performance hasn't regressed where it matters (**benchmarking**).
8. **Verify the split:** pinning tests pass unchanged, each module has tests through its interface, dependencies are acyclic, and total code stayed flat or shrank. Include a Mermaid dependency diagram for review.

For splits larger than moving one module, plan the sequence as a task graph first (**dagify**).

**Don't split:**
- purely by line count (a long single-purpose file like a lookup or transition table belongs together);
- one cohesive idea across multiple files where splitting hurts readability;
- just to introduce a single-implementation interface with no real boundary behind it.
