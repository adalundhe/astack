---
name: minimize-state-stores
description: "Keep one source of truth per datum; add caches or extra state only when measurements justify them. Use when writing or reviewing caching, denormalization, or stateful code."
disable-model-invocation: true
---

# Minimize state stores

Keep one source of truth for every piece of data, because every extra copy drifts stale. Introduce caches, copies, or long-lived state only when measurements prove they're needed.

## Start with

1. **Keep one source of truth** and compute derived values on demand.
2. **Keep state as narrow as possible:** local variable before request scope, request before process, process before shared state. Avoid mutable globals.
3. **Optimize the slow path before caching around it** (**benchmarking**).
4. **Build justified caches properly:** when measurements prove a cache is needed, enforce every requirement below:
   - give it a single owner and explicit invalidation on source updates;
   - bound its size with eviction, preserve freshness via invalidation (allow bounded staleness only when explicitly approved per `never-trade-functionality`), and track hit rate;
   - test it empty, stale, full, under miss bursts, and across restarts.

## Watch for

- unmeasured caches (memoization, in-memory maps/LRUs, Redis, HTTP/CDN or query caches);
- duplicated data (denormalized columns, materialized views, local mirrors of another service's data);
- stored summaries (counts, totals, flags) that could be computed directly;
- overly broad state (globals, module-level mutables, stateful singletons);
- scratch files, temp tables, or local stores quietly turning into sources of truth.

**The test:** if you deleted this store, what would users measurably lose?

## When it doesn't fit

- a measurement-justified cache built per `Start with`;
- the primary store of record or inherent runtime state (e.g. an active session or streaming buffer);
- an explicit product copy (backups, availability replicas, requested exports) with documented sync semantics;
- a pure-function memo scoped strictly to a single computation that cannot go stale;
- an alternative backed by measurements (**ab-test**), with the trade-off documented.

**Showing it:** mutate the source of truth and read stale data from the copy, or run under load and show unbounded memory/storage growth.

Referenced skills: `benchmarking` (`${CLAUDE_SKILL_DIR}/../benchmarking/SKILL.md`), `ab-test` (`${CLAUDE_SKILL_DIR}/../ab-test/SKILL.md`). Read any cited skill file before acting when its trigger applies.
