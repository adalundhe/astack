---
name: minimize-state-stores
description: "Keep each piece of data in one place; add a cache, copy or long-lived state only when a measurement shows you need it. Use when writing or reviewing code that caches, copies or keeps state."
---

# Minimize state stores

Keep each piece of data in one place. Add a cache or a copy only when a measurement shows you need it.

## Start with

1. **Keep one original** for each piece of data, and compute the rest when needed.
2. **Keep state as local as possible:** a function before a request, a request before a process, a process before anything shared. Avoid global mutable state.
3. **Fix slow code before caching around it** (**benchmarking**).
4. **Add a cache only when a measurement shows the need,** and then give it one owner, invalidation when the original changes, a size limit with eviction, only the staleness users accept, and a measured hit rate. Test it empty, stale, full, under a burst of misses, and after a restart.

## Watch for

- caches: memoized functions, in-memory maps and LRUs, Redis and the like, HTTP and CDN caches, cached query results;
- copies: the same data in two places, such as a denormalized column, a materialized view or a local copy of another service's data;
- stored results: counts, totals, flags and summaries that could be computed when needed;
- long-lived state: globals, module-level variables, singletons that collect state, state kept wider than where it's used;
- side stores: temp files, local databases or scratch stores that quietly became the source of truth.

**The test:** if you deleted this store, what would users measurably lose?

## When it doesn't fit

- a cache a measurement justified, built as in Start with;
- the store of record itself, and state the work inherently holds, such as a user's session or a buffer while streaming;
- a copy that is the product, such as a backup, a replica for availability or an export the person asked for, with its sync explicit;
- a memo of a pure function inside one computation, bounded by it and unable to go stale;
- an approach the evidence here favours: when unsure, try both and measure (**ab-test**), and say why you chose it.

**Showing it:** change the original and read the copy, or run it under load and watch the store grow.
