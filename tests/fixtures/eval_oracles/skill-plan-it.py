"""Separated offline oracle for `skill-plan-it`."""
from __future__ import annotations

from pathlib import Path

GRILLING_DOC = """# Grilling Snapshot: Automatic Invoice Retries (`billing`)

## Repo Receipts and Contradictions
- `repo/docs/spec.md` specifies a **72-hour** retry window (`MAX_RETRY_WINDOW_HOURS = 72`) and names records `dunning_attempt`.
- `repo/src/billing.py` defines `MAX_RETRY_WINDOW_HOURS = 24`, `RETRY_LIMIT = 3`, `GATEWAY_TIMEOUT_SECONDS = 10`, and names records `RetryCharge` (`repo/tests/test_billing.py` pins `24`).
- Request conflict 1: returning HTTP 200 in under 500 ms p99 is physically incompatible with running up to 3 synchronous 10 s gateway retries (up to 30 s worst-case latency) in the checkout handler.
- Request conflict 2: unlimited retries conflict with the 24-hour refund-window cutoff and require idempotency keys to avoid duplicate charges on gateway timeouts.

## Decision Tree
- [OPEN - ACTIVE] Branch 1: Synchronous checkout retries vs asynchronous retry queue with HTTP 202 acceptance.
- [OPEN] Branch 2: Canonical retry window (24h in `repo/src/billing.py` vs 72h in `repo/docs/spec.md`) and cap policy.
- [OPEN] Branch 3: Idempotency key storage to prevent duplicate charges across retries.
- [OPEN] Branch 4: Canonical domain term (`RetryCharge` vs `dunning_attempt`).

## Cost Ledger
| Branch | Latency Impact | Consistency / Failure Risk | Operational Burden |
| --- | --- | --- | --- |
| Pending Branch 1 (Async queue) | Checkout stays under 500 ms p99 | Eventual payment confirmation; needs idempotency key per invoice | One retry worker + persisted queue table |
| Pending Branch 1 (Sync handler) | Up to 30 s p99 during gateway stall | Client timeouts trigger blind re-submits and duplicate charges | Zero extra worker process |
"""


def apply(ws: Path) -> dict[str, object]:
    """Write GRILLING.md outside repo under ASTACK_HOME and return a focused single-decision exchange."""
    arch_dir = ws / "program" / "astack_home" / "billing" / "architecture"
    arch_dir.mkdir(parents=True, exist_ok=True)
    (arch_dir / "GRILLING.md").write_text(GRILLING_DOC, encoding="utf-8")
    return {
        "final_text": (
            "Before coding, inspecting `repo/docs/spec.md` and `repo/src/billing.py` turned up one "
            "doc-vs-code contradiction and two conflicting requirements in `program/request.md`:\n\n"
            "1. **Spec vs code contradiction:** `repo/docs/spec.md` sets a **72-hour** retry window "
            "and calls records `dunning_attempt`, while `repo/src/billing.py` (and `repo/tests/test_billing.py`) "
            "enforces `MAX_RETRY_WINDOW_HOURS = 24` with `RetryCharge`.\n"
            "2. **Request conflicts:** (a) Returning HTTP 200 under 500 ms p99 cannot coexist with up to "
            "3 synchronous gateway retries at `GATEWAY_TIMEOUT_SECONDS = 10` (up to 30 s per request); "
            "(b) unlimited retries conflict with a hard 24-hour cutoff and require idempotency keys to prevent duplicate charges.\n\n"
            "### Decision 1 (highest impact): Checkout execution model\n"
            "- **Option A (Asynchronous retry queue — recommended):** Accept the checkout request, persist "
            "a pending charge with an idempotency key, return HTTP 202 under 500 ms, and let a background worker "
            "run retries within a bounded window. When the payment gateway stalls for 10 s, checkout threads stay "
            "unblocked and callers poll or receive a webhook.\n"
            "- **Option B (Synchronous retries inside checkout):** Drop the 500 ms SLA and allow up to 30 s "
            "request times. During a gateway brownout, worker threads saturate and client timeouts trigger duplicate submissions.\n\n"
            "**Recommendation:** Pick Option A so checkout latency stays bounded under 500 ms and retries survive timeouts.\n"
            "Saved the open decision tree and cost ledger to `program/astack_home/billing/architecture/GRILLING.md`. "
            "Reply with Option A or Option B before we resolve the 24h vs 72h window and idempotency branch."
        ),
    }
