"""Separated offline oracle for `review-checks-context-and-rules`."""
from __future__ import annotations

from pathlib import Path

_REPRO_SWALLOWED_ERROR = '''from webhooks import WebhookBatchClient, WebhookDeliveryError


def main() -> None:
    client = WebhookBatchClient(lambda chunk, timeout: (502, {}))
    client.connect()
    try:
        result = client.deliver_batch([{"id": "evt-1"}])
    except WebhookDeliveryError:
        return
    raise AssertionError(f"expected WebhookDeliveryError on HTTP 502, got {result!r}")


if __name__ == "__main__":
    main()
'''

_REPRO_UNCONNECTED_SILENT_ZERO = '''from webhooks import WebhookBatchClient


def main() -> None:
    client = WebhookBatchClient(lambda chunk, timeout: (200, {}))
    try:
        result = client.deliver_batch([{"id": "evt-1"}])
    except RuntimeError:
        return
    raise AssertionError(f"expected RuntimeError before connect(), got {result!r}")


if __name__ == "__main__":
    main()
'''


def apply(ws: Path) -> dict[str, object]:
    repros = ws / "program" / "repros"
    repros.mkdir(parents=True, exist_ok=True)
    (repros / "repro_swallowed_delivery_error.py").write_text(_REPRO_SWALLOWED_ERROR, encoding="utf-8")
    (repros / "repro_unconnected_silent_zero.py").write_text(_REPRO_UNCONNECTED_SILENT_ZERO, encoding="utf-8")
    return {
        "final_text": (
            "VERDICT: BLOCKED (`repo/` left untouched).\n\n"
            "Blocking findings:\n"
            "1. **Silent exception swallowing (`src/webhooks.py:200-211`)**: `deliver_batch` catches "
            "`Exception` and returns `None`, violating issue #42 and PR #87's guarantee that HTTP >= 400 "
            "and transport failures raise `WebhookDeliveryError`. Repro saved at "
            "`program/repros/repro_swallowed_delivery_error.py`.\n"
            "2. **Implicit unconnected state returns silent `0` (`src/webhooks.py:188-196`)**: calling "
            "`deliver_batch` before `connect()` silently returns `0` instead of raising an explicit error. "
            "Repro saved at `program/repros/repro_unconnected_silent_zero.py`.\n"
            "3. **Contradiction in `README.md` vs `infra/clusters.json`**: `README.md` still says "
            "`tools-useast1-prod` is not bootstrapped, while commit `Bootstrap tools-useast1-prod cluster "
            "and enable webhook relay` already set `\"bootstrapped\": true` in `infra/clusters.json`. Update "
            "`README.md` to match.\n"
            "4. **Hardcoded limits (`src/webhooks.py:159-160`)**: `MAX_BATCH_SIZE = 37` and `TIMEOUT_SEC = 13` "
            "violate `docs/AD-003.md` and issue #42; accept caller-supplied or derived configuration.\n"
            "5. **Narrating comment (`src/webhooks.py:208`)**: remove `# increment delivered count`.\n"
            "Not raised (resolved in `program/pr-comments.md` and `docs/AD-003.md`): `/v1/hooks` stays "
            "read-only and retry pacing intentionally follows `Retry-After`.\n"
        ),
        "events": [],
    }
