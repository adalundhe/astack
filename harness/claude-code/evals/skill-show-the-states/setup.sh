#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/order_fsm.py <<'EOF'
"""Order lifecycle finite state machine."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class OrderState(str, Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class InvalidTransitionError(ValueError):
    """Raised when an event is not allowed in the current OrderState."""


@dataclass
class OrderFSM:
    order_id: str
    items: list[int] = field(default_factory=list)
    state: OrderState = OrderState.DRAFT
    attempts: int = 0
    max_attempts: int = 3
    refunded_cents: int = 0

    @property
    def total_cents(self) -> int:
        return sum(self.items)

    def submit(self) -> OrderState:
        """Transition DRAFT -> PENDING when at least one line item exists."""
        if self.state != OrderState.DRAFT:
            raise InvalidTransitionError(f"cannot submit from {self.state.value}")
        if not self.items or self.total_cents <= 0:
            raise InvalidTransitionError("cannot submit an empty or zero-total order")
        self.attempts = 1
        self.state = OrderState.PENDING
        return self.state

    def capture_succeeded(self) -> OrderState:
        """Transition PENDING -> PAID on payment capture success."""
        if self.state != OrderState.PENDING:
            raise InvalidTransitionError(f"cannot capture from {self.state.value}")
        self.state = OrderState.PAID
        return self.state

    def capture_failed(self, reason: str = "gateway_decline") -> OrderState:
        """Transition PENDING -> FAILED when payment capture declines or times out."""
        if self.state != OrderState.PENDING:
            raise InvalidTransitionError(f"cannot fail from {self.state.value}")
        self.state = OrderState.FAILED
        return self.state

    def retry_payment(self) -> OrderState:
        """Transition FAILED -> PENDING if retry budget remains (attempts < max_attempts)."""
        if self.state != OrderState.FAILED:
            raise InvalidTransitionError(f"cannot retry from {self.state.value}")
        if self.attempts >= self.max_attempts:
            raise InvalidTransitionError(f"retry budget exhausted ({self.attempts}/{self.max_attempts})")
        self.attempts += 1
        self.state = OrderState.PENDING
        return self.state

    def issue_refund(self, refund_cents: int) -> OrderState:
        """Transition PAID -> REFUNDED for a valid positive refund <= total_cents."""
        if self.state != OrderState.PAID:
            raise InvalidTransitionError(f"cannot refund from {self.state.value}")
        if refund_cents <= 0 or refund_cents > self.total_cents:
            raise InvalidTransitionError(f"invalid refund amount: {refund_cents}")
        self.refunded_cents = refund_cents
        self.state = OrderState.REFUNDED
        return self.state
EOF

cat > repo/tests/test_order_fsm.py <<'EOF'
import unittest
from src.order_fsm import InvalidTransitionError, OrderFSM, OrderState


class OrderFsmTest(unittest.TestCase):
    def test_happy_path_and_refund(self):
        fsm = OrderFSM("ord-1", items=[1500, 500])
        self.assertEqual(fsm.state, OrderState.DRAFT)
        self.assertEqual(fsm.submit(), OrderState.PENDING)
        self.assertEqual(fsm.capture_succeeded(), OrderState.PAID)
        self.assertEqual(fsm.issue_refund(2000), OrderState.REFUNDED)

    def test_failure_and_retry_loop(self):
        fsm = OrderFSM("ord-2", items=[1000], max_attempts=2)
        fsm.submit()
        self.assertEqual(fsm.capture_failed("timeout"), OrderState.FAILED)
        self.assertEqual(fsm.retry_payment(), OrderState.PENDING)
        self.assertEqual(fsm.capture_failed("declined"), OrderState.FAILED)
        with self.assertRaises(InvalidTransitionError):
            fsm.retry_payment()

    def test_illegal_shortcuts_rejected(self):
        fsm = OrderFSM("ord-3", items=[1000])
        with self.assertRaises(InvalidTransitionError):
            fsm.capture_succeeded()


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial order lifecycle fsm"
