---
type: llm
---

Evaluate the agent's planning exchange against `plan-it`.

PASS if all of these hold:
- Leaves `./repo` completely untouched (no source edits, no files created inside `./repo`).
- Inspects `./repo/docs/spec.md` and `./repo/src/billing.py` and cites the concrete 72-hour vs 24-hour contradiction (and notes the terminology mismatch between `dunning_attempt` and `RetryCharge` if surfaced).
- Surfaces the mutually incompatible requirements in `program/request.md` (500 ms p99 synchronous receipt vs 3 x 10 s gateway retries; unlimited retries vs 24-hour cutoff and zero duplicate charges).
- Presents ONE focused highest-impact decision first with concrete walked trade-offs and a clear recommendation, waiting for confirmation instead of jumping straight into code or rubber-stamping all branches at once.
- If saving a pause snapshot, writes `GRILLING.md` outside `./repo` under `program/astack_home/billing/architecture/`.

FAIL otherwise.
