---
type: llm
---

Evaluate the refactored `JobProcessor` in `./repo` against `no-implicit-states`.

PASS if all of these hold:
- Replaces the overlapping boolean flags (`is_started`, `is_paused`, `is_failed`, `is_done`) with a single explicit `Enum` state type (`JobState`).
- Routes all lifecycle events through a centralized transition table or function that explicitly handles valid pairs and rejects illegal transitions with `ValueError` without mutating state.
- Adds unit tests covering both valid lifecycle paths and rejected invalid transitions.

FAIL otherwise.
