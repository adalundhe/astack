---
name: modularize
description: "Break monolithic code (a codebase, package, file or function) into modules that each do one job, test alone and swap behind a small explicit interface, without needless abstraction and in the codebase's own style. Use when code is too big to change safely, or when asked to split it up."
---

# Modularize

Split monolithic code into modules that each do one job and can be tested and replaced alone, with no more structure than that needs.

1. **Map what it does** (**how-it-works**): its jobs, the data each one owns, who calls what, and where state lives (**show-the-states**).
2. **Pin its behaviour first:** tests from the outside that pass before the split and must pass, unchanged, after it (**tests-assert-behaviour**).
3. **Find the seams.** Group code by the job it does and the data it owns, not by technical layer. Where data crosses between groups is an interface. Shared mutable state and hidden states between groups are coupling to remove first (**minimize-state-stores**, **no-shared-writes**, **no-implicit-states**).
4. **Cut each module to do one job:** it owns its data, exposes a small explicit interface of functions and types, and hides the rest. Dependencies point one way, with no cycles. Logic stays in plain functions; I/O stays in a thin shell (**check-your-boundaries**).
5. **Make modules swappable through their interface,** not through layers. A replacement implements the same functions and types. Add a formal interface, trait or protocol only at a real boundary (I/O, another service, a second implementation that exists), and prefer composition to inheritance.
6. **Keep the codebase coherent:** follow its existing layout, naming, error handling and patterns, and name each module for its job in the domain's words. Don't introduce a new architectural style for one corner of it.
7. **Move in steps,** one module at a time, each ending green, with callers moved in the same change and no compatibility shims (**yagni**). Keep behaviour changes out of the moves. Where speed matters, show it unchanged (**benchmarking**).
8. **Check the result:** the pinning tests pass unchanged, each module has its own tests through its interface, the dependency graph has no cycles, and the total code shrank or held. Draw the modules and their dependencies in Mermaid for the review.

For anything larger than one module's move, plan the moves as a graph first (**dagify**).

**Don't split:**

- by size alone: a long file that does one job, such as a table, a generated file or a transition table, stays whole;
- one idea across several files, which makes it harder to follow;
- to add an interface with a single implementation and no boundary behind it.
