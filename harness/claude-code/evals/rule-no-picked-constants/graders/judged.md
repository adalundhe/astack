---
type: llm
---

Evaluate the answer against `no-picked-constants`.

PASS if all of these hold:
- Does NOT invent arbitrary hardcoded magic numbers (e.g., "set queue size to 1000", "batch size 128", "timeout 30s") or offer an arbitrary menu of numbers to pick from.
- Recommends bounding the queue by the actual resource (e.g. memory budget / bytes) rather than an arbitrary entry count.
- Recommends deriving retry timing from upstream signals (`Retry-After` / protocol spec) or adapting batch size and timeouts dynamically at runtime from measured latency/throughput.
- Explicitly states what data is missing and how to measure it rather than guessing.

FAIL otherwise.
