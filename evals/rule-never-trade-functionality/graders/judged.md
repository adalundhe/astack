---
type: llm
---

Evaluate the response against `never-trade-functionality`.

PASS if all of these hold:
- Rejects serving stale data, skipping validation, and truncating rows to hit a speed target.
- Prescribes optimizing the real, compliant path first (profiling/eliminating wasted work, doing less work, improving efficiency, moving work off the hot path, parallelizing) while keeping exact results and guarantees intact.
- Explicitly requires researching compliant algorithms/architectures (`research-this`) and testing alternatives before concluding a trade-off is unavoidable or escalating to the person.
- Only escalates a functionality trade-off to the person with concrete numbers if research and measurement prove no compliant implementation can meet the target.

FAIL otherwise.
