---
description: "In Go mode, redesigning a tangled tuple/parallel-array route scheduler in ./repo routes to data-structures-first, introduces typed domain records and consistent index invariants before control flow, fixes exact integer cost accounting, and adds invariant tests."
expected_outcome: "Reads data-structures-first/SKILL.md, replaces nested dict-of-lists-of-tuples, parallel arrays, and float costs in ./repo/src/router.py with typed dataclasses, canonical ownership, and consistent indexes, fixes O(n^2) scans and invariants, and adds correctness and invariant tests."
timeout_seconds: 360
---

`/astack:go` Redesign `RouteScheduler` in `./repo/src/router.py` (see `./repo/README.md` for the contract). The current implementation spreads state across nested dicts of raw tuples and parallel lists (`_worker_names`, `_worker_capacities`, `_worker_loads`) and stores costs as floats. As a result, reassignments leak worker load counts, duplicate route IDs sneak into other regions, unregistering workers shifts parallel lists out of sync, cost totals suffer float rounding drift, and lookups degrade to slow scans. Replace the underlying representation with typed domain records, integer cents, canonical ownership, and consistent indexes, and add tests in `./repo/tests/` proving correctness and invariants.
