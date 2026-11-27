---
type: llm
---

Evaluate the changes in `./repo` and the final summary against `no-shared-writes`.

PASS if all of these hold:
- Removes shared mutable dict updates across worker threads and removes concurrent writes to one shared `summary.json` file.
- Isolates each worker into its own local aggregation and unique persisted partition file, merging outputs in `read_summary()` without introducing mutexes/locks.
- Repeated `process_batches` runs accumulate totals without clobbering earlier worker outputs.
- Concurrent stress tests prove zero lost updates or file corruption and pass.

FAIL otherwise.
