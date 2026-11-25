#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests repo/docs repo/infra

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
- `/v2/hooks`: active batched delivery pipeline
EOF

cat > repo/docs/AD-003.md <<'EOF'
# AD-003: Legacy Webhook Endpoint and Delivery Configuration

1. Keep `/v1/hooks` read-only until Q3 partner migration completes.
2. Derive batch sizes and timeouts from caller config or payload/SLA budgets — never hardcode magic constants.
EOF

cat > repo/infra/clusters.json <<'EOF'
{
  "tools-uswest2-prod": {"bootstrapped": true, "region": "us-west-2"},
  "tools-useast1-prod": {"bootstrapped": false, "region": "us-east-1"}
}
EOF

git -C repo add .
git -C repo commit -q -m "initial webhook relay"

cat > repo/infra/clusters.json <<'EOF'
{
  "tools-uswest2-prod": {"bootstrapped": true, "region": "us-west-2"},
  "tools-useast1-prod": {"bootstrapped": true, "region": "us-east-1"}
}
EOF
git -C repo add infra/clusters.json
git -C repo commit -q -m "Bootstrap tools-useast1-prod cluster and enable webhook relay"
BOOTSTRAP_SHA=$(git -C repo rev-parse --short HEAD)

git -C repo checkout -q -b lane/webhook-batching

cat > repo/src/webhooks.py <<'EOF'
from __future__ import annotations
from typing import Callable

MAX_BATCH_SIZE = 37
TIMEOUT_SEC = 13


class WebhookDeliveryError(RuntimeError):
    pass


def v1_hooks_handler(method: str) -> dict[str, str]:
    if method != "GET":
        raise PermissionError("/v1/hooks is read-only")
    return {"status": "ok", "version": "v1"}


class WebhookBatchClient:
    def __init__(self, transport: Callable[[list[dict], int], tuple[int, dict[str, str]]]):
        self._transport = transport

    def deliver_batch(self, events: list[dict]) -> int | None:
        delivered = 0
        for idx in range(0, len(events), MAX_BATCH_SIZE):
            chunk = events[idx : idx + MAX_BATCH_SIZE]
            try:
                status, headers = self._transport(chunk, TIMEOUT_SEC)
                if status == 429:
                    status, _ = self._transport(chunk, TIMEOUT_SEC)
                if status >= 400:
                    raise WebhookDeliveryError(f"batch failed with status {status}")
                delivered += len(chunk)
            except Exception:
                return None
        return delivered
EOF

git -C repo add .
git -C repo commit -q -m "Add WebhookBatchClient for batched v2 delivery"
git -C repo rev-parse HEAD > program/head_sha.txt
git -C repo diff main..lane/webhook-batching > program/change.diff
git -C repo log --oneline -n 10 > program/git-log.txt

cat > program/pr.md <<'EOF'
# PR #87: Add batched webhook delivery

Fixes #42 (`program/linked-issue-42.md`). See `repo/docs/AD-003.md` and `program/pr-comments.md`.
Guarantee: all failed webhook deliveries raise `WebhookDeliveryError` and are never silently dropped.
EOF

cat > program/linked-issue-42.md <<'EOF'
# Issue #42: Batched webhook delivery without silent drops

1. Any HTTP error (`>= 400`) or transport failure MUST raise `WebhookDeliveryError`; never swallow exceptions or return `None`.
2. Per `docs/AD-003.md`, keep `/v1/hooks` read-only until Q3 partner migration finishes.
3. Per `docs/AD-003.md`, batch size and timeout must be configurable or derived, not hardcoded magic numbers.
EOF

cat > program/pr-comments.md <<'EOF'
# PR #87 Review Comments

- **@alice (resolved):** Why does retry pacing honor `Retry-After` instead of doing local exponential backoff?
  - **@bob:** Confirmed with gateway team in #42 — upstream gateway always sends `Retry-After` on 429s and rejects unpaced local exponential retries. Resolved.
- **@carol (resolved):** Should `/v1/hooks` stay read-only?
  - **@bob:** Yes, per `docs/AD-003.md` and issue #42 until Q3 migration completes. Resolved.
EOF

# Deliberately terrible draft committing every anti-pattern /leave-feedback must catch and fix!
cat > program/draft-comment.md <<EOF
Hi! Per our 3-reviewer jackknife run logged in coverage-map.md (POOL EXHAUSTED on sonnet/haiku, P2 severity), I wanted to share some thoughts after looking at the diff:

1. ${BOOTSTRAP_SHA} says tools-useast1-prod was bootstrapped.
2. In \`src/webhooks.py\`, the error handling inside \`deliver_batch\` feels somewhat concerning and suboptimal in terms of overall reliability posture, and it might be worth giving some additional consideration to how exceptions are handled there, because swallowing errors is generally not ideal and could potentially cause issues downstream in some scenarios where reliability matters.
3. Also, could you please clarify why \`/v1/hooks\` is still read-only instead of supporting writes, and why retry handling honors \`Retry-After\` rather than using local exponential backoff?
4. Furthermore, on the constants front, \`MAX_BATCH_SIZE = 37\` and \`TIMEOUT_SEC = 13\` are hardcoded. As mentioned above, reliability posture and configuration cleanliness are important considerations here.
EOF
