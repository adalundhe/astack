---
description: "Atomic outcome eval for quickcheck: runs a single focused read-only check on the latest branch change in ./repo without modifying ./repo or performing vectored review, catching a genuine documented-behavior blocker while suppressing context-blind flags on documented architecture and tooling choices."
expected_outcome: "Reads quickcheck/SKILL.md, keeps ./repo clean, performs a single focused check without vectored review, writes program/QUICKCHECK.md with VERDICT: BLOCKED proving the duplicate-key premature-eviction bug in src/cache.py, and does not block on the user-clarified/documented FIFO eviction, single-threaded design, or documented DATA_DIR default."
timeout_seconds: 480
---

`/astack:go` `/astack:quickcheck` Run a quickcheck on the latest branch change (`main~1..HEAD`) in `./repo` without modifying `./repo`, and write the findings report to `program/QUICKCHECK.md`.

Context from me: we intentionally kept single-threaded FIFO eviction per `docs/ARCHITECTURE.md` — do not ask for LRU or locking.
