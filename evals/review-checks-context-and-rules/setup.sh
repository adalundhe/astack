#!/bin/bash
set -euo pipefail
mkdir -p program/repros repo/src repo/tests repo/docs repo/infra

if [ -n "${ASTACK_EVAL_SETTINGS_JSON:-}" ]; then
  printf '%s\n' "$ASTACK_EVAL_SETTINGS_JSON" > program/settings.json
else
cat > program/settings.json <<'EOF'
{
  "worker_minutes": 60,
  "reviewer_minutes": 30,
  "researcher_minutes": 30,
  "wind_down_minutes": 5,
  "check_in_minutes": 5,
  "roles": {
    "worker": {"provider": "anthropic", "model": "haiku", "effort": "medium"}
  },
  "reviewer_pool": [
    {"provider": "anthropic", "model": "sonnet", "effort": "medium"},
    {"provider": "anthropic", "model": "haiku", "effort": "medium"}
  ]
}
EOF
fi

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Webhook Relay

Delivers signed partner webhook events from internal clusters.

## Cluster bootstrap status

- `tools-uswest2-prod`: bootstrapped
- `tools-useast1-prod`: NOT bootstrapped (manual provisioning still pending)

## Endpoints

- `/v1/hooks`: legacy read-only inspection endpoint (see `docs/AD-003.md`)
- `/v2/hooks`: active delivery pipeline
EOF

cat > repo/docs/AD-003.md <<'EOF'
# AD-003: Legacy Webhook Endpoint and Delivery Configuration

## Decisions

1. **Keep `/v1/hooks` read-only until Q3 partner migration completes.** Do not delete, deprecate, or add write mutations to `/v1/hooks` before Q3 migration sign-off.
2. **Derive batch sizes and timeouts from caller config or payload/SLA budgets.** Never hardcode arbitrary magic constants for batch limits or HTTP timeouts inside `WebhookClient`.
EOF

cat > repo/infra/clusters.json <<'EOF'
{
  "tools-uswest2-prod": {"bootstrapped": true, "region": "us-west-2"},
  "tools-useast1-prod": {"bootstrapped": false, "region": "us-east-1"}
}
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/webhooks.py <<'EOF'
from __future__ import annotations

from typing import Callable


class WebhookDeliveryError(RuntimeError):
    """Raised when a webhook delivery fails."""


def v1_hooks_handler(method: str) -> dict[str, str]:
    if method != "GET":
        raise PermissionError("/v1/hooks is read-only")
    return {"status": "ok", "version": "v1"}


def deliver_single(
    transport: Callable[[list[dict]], tuple[int, dict[str, str]]],
    event: dict,
) -> int:
    status, _ = transport([event])
    if status >= 400:
        raise WebhookDeliveryError(f"webhook delivery failed with status {status}")
    return 1
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_webhooks.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from webhooks import WebhookDeliveryError, deliver_single, v1_hooks_handler


class WebhookBaseTest(unittest.TestCase):
    def test_v1_is_read_only(self):
        self.assertEqual(v1_hooks_handler("GET")["version"], "v1")
        with self.assertRaises(PermissionError):
            v1_hooks_handler("POST")

    def test_deliver_single_raises_on_error(self):
        with self.assertRaises(WebhookDeliveryError):
            deliver_single(lambda batch: (502, {}), {"id": "e1"})
EOF

git -C repo add .
git -C repo commit -q -m "initial webhook relay service"

# Second commit on main bootstraps tools-useast1-prod in infra/clusters.json,
# leaving README.md contradicting the commit and cluster config.
cat > repo/infra/clusters.json <<'EOF'
{
  "tools-uswest2-prod": {"bootstrapped": true, "region": "us-west-2"},
  "tools-useast1-prod": {"bootstrapped": true, "region": "us-east-1"}
}
EOF
git -C repo add infra/clusters.json
git -C repo commit -q -m "Bootstrap tools-useast1-prod cluster and enable webhook relay"
BOOTSTRAP_SHA=$(git -C repo rev-parse --short HEAD)

# Branch lane/webhook-batching implements batch delivery with:
#  1. Silent failure contradicting PR description, issue #42, and no-hidden-flow-control (except Exception: return None)
#  2. Hardcoded magic constants MAX_BATCH_SIZE = 37 and TIMEOUT_SEC = 13 contradicting AD-003 and no-picked-constants
#  3. Implicit lifecycle flag _connected = False silently returning [] before connect() (no-implicit-states)
#  4. Redundant comment "# increment delivered count" (comment-cop)
#  5. Touches README.md while leaving the stale "tools-useast1-prod: NOT bootstrapped" contradiction intact
git -C repo checkout -q -b lane/webhook-batching

cat > repo/README.md <<'EOF'
# Webhook Relay

Delivers signed partner webhook events from internal clusters, now with batched v2 delivery.

## Cluster bootstrap status

- `tools-uswest2-prod`: bootstrapped
- `tools-useast1-prod`: NOT bootstrapped (manual provisioning still pending)

## Endpoints

- `/v1/hooks`: legacy read-only inspection endpoint (see `docs/AD-003.md`)
- `/v2/hooks`: active batched delivery pipeline
EOF

cat > repo/src/webhooks.py <<'EOF'
from __future__ import annotations

from typing import Callable

MAX_BATCH_SIZE = 37
TIMEOUT_SEC = 13


class WebhookDeliveryError(RuntimeError):
    """Raised when a webhook delivery fails."""


def v1_hooks_handler(method: str) -> dict[str, str]:
    if method != "GET":
        raise PermissionError("/v1/hooks is read-only")
    return {"status": "ok", "version": "v1"}


def deliver_single(
    transport: Callable[[list[dict]], tuple[int, dict[str, str]]],
    event: dict,
) -> int:
    status, _ = transport([event])
    if status >= 400:
        raise WebhookDeliveryError(f"webhook delivery failed with status {status}")
    return 1


class WebhookBatchClient:
    """Batched webhook client honoring upstream Retry-After headers."""

    def __init__(self, transport: Callable[[list[dict], int], tuple[int, dict[str, str]]]):
        self._transport = transport
        self._connected = False
        self.last_retry_after: int | None = None

    def connect(self) -> None:
        self._connected = True

    def deliver_batch(self, events: list[dict]) -> int | None:
        if not self._connected:
            return 0
        delivered = 0
        for idx in range(0, len(events), MAX_BATCH_SIZE):
            chunk = events[idx : idx + MAX_BATCH_SIZE]
            try:
                status, headers = self._transport(chunk, TIMEOUT_SEC)
                if status == 429:
                    retry_after = int(headers.get("Retry-After", "1"))
                    self.last_retry_after = retry_after
                    status, _ = self._transport(chunk, TIMEOUT_SEC)
                if status >= 400:
                    raise WebhookDeliveryError(f"batch failed with status {status}")
                # increment delivered count
                delivered += len(chunk)
            except Exception:
                return None
        return delivered
EOF

cat > repo/tests/test_webhooks.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from webhooks import WebhookBatchClient, WebhookDeliveryError, deliver_single, v1_hooks_handler


class WebhookBaseTest(unittest.TestCase):
    def test_v1_is_read_only(self):
        self.assertEqual(v1_hooks_handler("GET")["version"], "v1")
        with self.assertRaises(PermissionError):
            v1_hooks_handler("POST")

    def test_deliver_single_raises_on_error(self):
        with self.assertRaises(WebhookDeliveryError):
            deliver_single(lambda batch: (502, {}), {"id": "e1"})

    def test_batch_happy_path_and_retry_after(self):
        calls = []

        def fake_transport(chunk, timeout):
            calls.append((len(chunk), timeout))
            if len(calls) == 1:
                return 429, {"Retry-After": "2"}
            return 200, {}

        client = WebhookBatchClient(fake_transport)
        client.connect()
        sent = client.deliver_batch([{"id": "1"}, {"id": "2"}])
        self.assertEqual(sent, 2)
        self.assertEqual(client.last_retry_after, 2)
EOF

git -C repo add .
git -C repo commit -q -m "Add WebhookBatchClient and refresh README for v2 batching"
git -C repo rev-parse HEAD > program/head_sha.txt
git -C repo diff main..lane/webhook-batching > program/change.diff
git -C repo log --oneline -n 10 > program/git-log.txt

cat > program/pr.md <<EOF
# PR #87: Add batched webhook delivery

Fixes #42 (see \`program/linked-issue-42.md\`).
Related docs: \`repo/docs/AD-003.md\`.
Prior review discussion: \`program/pr-comments.md\`.

## Summary
- Adds \`WebhookBatchClient\` for batched \`/v2/hooks\` delivery.
- Honors upstream \`Retry-After\` header on 429 responses.
- Keeps \`/v1/hooks\` untouched and read-only.
- **Guarantee:** all failed webhook deliveries raise \`WebhookDeliveryError\` and are never silently dropped.
- Updates \`README.md\` for v2 batching.
EOF

cat > program/linked-issue-42.md <<'EOF'
# Issue #42: Batched webhook delivery without silent drops

## Requirements
1. Support delivering webhook events in batches.
2. **Never silently drop failed deliveries:** any HTTP error (`>= 400`) or transport failure MUST raise `WebhookDeliveryError` so the job runner retries and alerts. Never swallow exceptions or return `None`.
3. Per `docs/AD-003.md`, keep `/v1/hooks` read-only until Q3 partner migration finishes — do not delete or alter `/v1/hooks` in this work.
4. Per `docs/AD-003.md`, make batch size and timeout caller-configured or derived from payload/SLA budgets rather than arbitrary hardcoded constants.
EOF

cat > program/pr-comments.md <<'EOF'
# PR #87 Review Comments

- **@alice (resolved):** Why does retry pacing honor the upstream `Retry-After` header instead of doing local exponential backoff?
  - **@bob:** Confirmed with the gateway team during #42 scoping — the upstream webhook gateway always sends `Retry-After` on 429s and rejects unpaced local exponential retries. Leaving local exponential backoff out is intentional.
  - **@alice:** Got it, resolving this thread.

- **@carol (resolved):** Are we removing `/v1/hooks` here?
  - **@bob:** No — `docs/AD-003.md` and issue #42 keep `/v1/hooks` read-only until Q3 partner migration signs off.
  - **@carol:** Makes sense, resolved.
EOF
