---
type: llm
---

Evaluate the throwaway UX prototype and response against `play-with-me/SKILL.md`.

PASS if all of these hold:
- Places the throwaway CLI prototype strictly outside `./repo` at `program/prototype/demo.py` and leaves `./repo` untouched.
- Supports `--scenario undo` and `--scenario confirm` non-interactively in one command, producing distinct concrete state-transition traces for both flows with zero external or filesystem side effects.
- Explicitly states what is mocked/stubbed (in-memory report list, simulated timer/prompt) and shares the exact commands plus what to try.

FAIL otherwise.
