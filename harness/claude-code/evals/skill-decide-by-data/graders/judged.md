---
type: llm
---

Evaluate the empirical decision artifact, repository state, and final reply against `decide-by-data`.

PASS if all of these hold:
- Refuses to guess from intuition and instead measures both `algo_a` and `algo_b` on `program/dataset.json`.
- Leaves `./repo` clean (`git status` clean) as requested.
- Verifies exact output parity between `algo_a` and `algo_b`.
- Records `"winner": "algo_b"`, `"parity_verified": true`, measured timings for both algorithms, and clear rationale in `program/decision.json`, and states the `decided:` pick backed by measured numbers.

FAIL otherwise.
