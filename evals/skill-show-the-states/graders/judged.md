---
type: llm
---

Evaluate the state diagram against `show-the-states/SKILL.md`.

PASS if all of these hold:
- Leaves `./repo` completely clean and grounds the diagram in `repo/src/order_fsm.py` with context and `file:line` citations.
- Emits a valid Mermaid `stateDiagram-v2` block in `program/STATES.md` and inline in the response.
- Captures all 5 states (`DRAFT`, `PENDING`, `PAID`, `FAILED`, `REFUNDED`), start/end markers (`[*]`), and exact transitions with triggers and bracketed guards: `DRAFT -> PENDING` (`submit [items non-empty]`), `PENDING -> PAID` (`capture_succeeded`), `PENDING -> FAILED` (`capture_failed`), `FAILED -> PENDING` (`retry_payment [attempts < max_attempts]`), and `PAID -> REFUNDED` (`issue_refund [0 < refund_cents <= total_cents]`).
- Does not invent illegal transitions (such as `DRAFT -> PAID` or returning from `REFUNDED`).

FAIL otherwise.
