---
description: "Atomic outcome eval for rearchitect: walks git churn history in ./repo to surface repeated co-change bugfixes across tightly coupled src/sync.py and src/state.py, diagnoses bidirectional circular imports and shared global dict _SHARED_STATE, designs decoupled target module boundaries with a Mermaid diagram and incremental migration plan in program/REARCHITECT.md, and leaves ./repo clean."
expected_outcome: "Reads rearchitect/SKILL.md, inspects git log churn across ./repo (identifying src/sync.py and src/state.py as high-churn hotspots vs low-churn src/metrics.py), diagnoses bidirectional circular imports and shared mutable _SHARED_STATE coupling, writes program/REARCHITECT.md with a ranked card, Mermaid before/after boundary diagram, and incremental migration plan while keeping ./repo clean."
timeout_seconds: 480
---

`/astack:go` Bug fixes in `./repo` keep causing regressions across modules, and changes are getting harder to test in isolation. Run an architectural discovery pass over `./repo` without modifying `./repo`: walk git history to identify the highest-churn hotspots, diagnose the concrete structural friction, and write a restructuring proposal to `program/REARCHITECT.md` with ranked candidate card(s), target decoupled module boundaries illustrated with a Mermaid diagram, and an incremental migration plan.
