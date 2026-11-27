"""Separated offline oracle for `leave-feedback-audits-before-posting`."""
from __future__ import annotations

from pathlib import Path

_FINAL_COMMENT = """A few items to address before merging PR #87:

1. **Silent failure in `src/webhooks.py` (`WebhookBatchClient.deliver_batch`)**: the `except Exception: return None` handler swallows both `WebhookDeliveryError` (HTTP `>= 400`) and transport exceptions. Issue #42 and the PR description require failed deliveries to raise `WebhookDeliveryError` so callers retry and alert. Remove the broad `return None` catch and let `WebhookDeliveryError` propagate (wrapping unexpected transport exceptions in `WebhookDeliveryError`).
2. **Stale cluster status in `README.md`**: `README.md` still lists `tools-useast1-prod` as not bootstrapped, which contradicts `infra/clusters.json` (updated in commit "Bootstrap tools-useast1-prod cluster and enable webhook relay" to `"bootstrapped": true`). Update the `README.md` bootstrap section so both match.
3. **Hardcoded delivery limits in `src/webhooks.py`**: `MAX_BATCH_SIZE = 37` and `TIMEOUT_SEC = 13` conflict with `docs/AD-003.md` and issue #42, which require batch sizes and timeouts to be caller-configured or derived from payload/SLA budgets. Pass these in via configuration or constructor parameters instead of module constants.
"""


def apply(ws: Path) -> dict[str, object]:
    (ws / "program" / "final-comment.md").write_text(_FINAL_COMMENT, encoding="utf-8")
    return {
        "final_text": _FINAL_COMMENT,
        "events": [],
    }
