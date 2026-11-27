"""Separated offline oracle for `skill-show-the-states`."""
from __future__ import annotations

from pathlib import Path

DIAGRAM = """```mermaid
stateDiagram-v2
    [*] --> DRAFT : create OrderFSM
    DRAFT --> PENDING : submit [items non-empty and total_cents > 0]
    PENDING --> PAID : capture_succeeded
    PENDING --> FAILED : capture_failed [gateway decline or timeout]
    FAILED --> PENDING : retry_payment [attempts < max_attempts]
    FAILED --> [*] : retry budget exhausted [attempts >= max_attempts]
    PAID --> REFUNDED : issue_refund [0 < refund_cents <= total_cents]
    REFUNDED --> [*]
```"""

STATES_MD = f"""# Order Lifecycle State Chart

## Context & Source Citations
- **System:** Order payment lifecycle (`OrderFSM` in `repo/src/order_fsm.py:8-75`).
- **Question answered:** Which transitions, guards, and failure/retry edges are valid across the 5 order states?
- **State definitions:** `repo/src/order_fsm.py:8-13` (`DRAFT`, `PENDING`, `PAID`, `FAILED`, `REFUNDED`).
- **Transition methods:**
  - `submit` (`repo/src/order_fsm.py:33-41`): `DRAFT -> PENDING`, guarded on non-empty items and `total_cents > 0` (`attempts = 1`).
  - `capture_succeeded` (`repo/src/order_fsm.py:43-48`): `PENDING -> PAID`.
  - `capture_failed` (`repo/src/order_fsm.py:50-55`): `PENDING -> FAILED` (failure path on gateway decline/timeout).
  - `retry_payment` (`repo/src/order_fsm.py:57-65`): `FAILED -> PENDING`, guarded on `attempts < max_attempts` (default `3`); once exhausted, further retries raise `InvalidTransitionError`.
  - `issue_refund` (`repo/src/order_fsm.py:67-75`): `PAID -> REFUNDED`, guarded on `0 < refund_cents <= total_cents`.
- **Disallowed shortcuts:** `DRAFT -> PAID` and any exit from `REFUNDED` raise `InvalidTransitionError`.

## DIAGRAMS

{DIAGRAM}
"""


def apply(ws: Path) -> dict[str, object]:
    """Write program/STATES.md and inline Mermaid stateDiagram-v2 in final_text, keeping ./repo clean."""
    (ws / "program" / "STATES.md").write_text(STATES_MD, encoding="utf-8")
    return {
        "final_text": (
            "Documented the 5-state `OrderFSM` lifecycle from `repo/src/order_fsm.py:8-75` in `program/STATES.md` "
            "(repo untouched).\n\n## DIAGRAMS\n\n" + DIAGRAM
        ),
    }
