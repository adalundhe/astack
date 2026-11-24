---
type: llm
---

Evaluate the refactored TypeScript code against `no-implicit-states`.

PASS if all of these hold:
- Replaces the separate boolean flags (`isIdle`, `isUploading`, `isDone`) and loose nullable fields (`url`, `error`, `progress`) with a single explicit discriminated/tagged union or enum state type where state-specific fields live only inside their matching variant.
- Routes state transitions through a centralized transition function or table that explicitly handles or rejects invalid events in each state.
- Handles states exhaustively without a silent catch-all default absorbing new states.
- Includes transition tests covering both valid transitions and rejected/invalid events.

FAIL otherwise.
