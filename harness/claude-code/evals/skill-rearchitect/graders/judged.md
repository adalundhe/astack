---
type: llm
---

Evaluate the rearchitecture discovery report in `program/REARCHITECT.md` against `rearchitect/SKILL.md`.

PASS if all of these hold:
- Leaves `./repo` completely clean while grounding findings in `./repo` git log and code.
- Identifies `src/sync.py` and `src/state.py` as the high-churn hotspot pair from git history (6 co-change commits vs 1 commit on `src/metrics.py` and `src/cli.py`).
- Diagnoses the exact structural friction: bidirectional circular imports (requiring deferred inline imports inside functions) and shared mutable global dict `_SHARED_STATE` mutated by both modules.
- Proposes concrete decoupled unidirectional module boundaries with a clear Mermaid diagram, strength rating (`strong` / ranked card), and an incremental migration plan starting with behavior-pinning tests.

FAIL otherwise.
