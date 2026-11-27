---
description: "Eliminate concurrent lost updates and corrupted summary files in a multi-threaded metrics aggregator by isolating per-worker outputs and merging on read without locks."
expected_outcome: "Reads no-shared-writes/SKILL.md, removes shared mutable dict mutations and shared summary.json overwrites in src/aggregator.py, writes isolated per-worker output files lock-free and merges them on read, and adds concurrent stress tests proving zero lost increments or file corruption."
allowed_tools: [Read, Glob, Grep, Bash, Edit, Write]
---

`/astack:go` The multi-threaded metrics aggregator in `./repo` (`src/aggregator.py`) loses increments and corrupts persisted JSON output whenever multiple batches run concurrently.

Read `./repo/README.md` for the public API and persistence contract. Refactor `./repo/src/aggregator.py` so concurrent worker threads never mutate shared state or overwrite a single shared file—isolate each worker's output and merge on read without introducing locks. Add concurrent stress tests under `./repo/tests/` proving exact totals across multi-batch and repeated runs, and verify all tests pass.
