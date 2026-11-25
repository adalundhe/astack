#!/usr/bin/env python3
"""Objective post-run verifier for review-checks-context-and-rules.

Verifies repo/ was untouched AND saved reproduction scripts objectively prove the silent
exception swallowing bug in `WebhookBatchClient.deliver_batch` (fails on buggy, passes on fixed),
while also tracking proof of the implicit unconnected silent-zero bug.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _repro_verify import PlantedBug, verify_reproductions  # noqa: E402


def fix_bug1_swallowed_delivery_error(repo: Path) -> None:
    p = repo / "src" / "webhooks.py"
    text = p.read_text(encoding="utf-8")
    old = (
        "            try:\n"
        "                status, headers = self._transport(chunk, TIMEOUT_SEC)\n"
        "                if status == 429:\n"
        '                    retry_after = int(headers.get("Retry-After", "1"))\n'
        "                    self.last_retry_after = retry_after\n"
        "                    status, _ = self._transport(chunk, TIMEOUT_SEC)\n"
        "                if status >= 400:\n"
        '                    raise WebhookDeliveryError(f"batch failed with status {status}")\n'
        "                # increment delivered count\n"
        "                delivered += len(chunk)\n"
        "            except Exception:\n"
        "                return None"
    )
    new = (
        "            try:\n"
        "                status, headers = self._transport(chunk, TIMEOUT_SEC)\n"
        "                if status == 429:\n"
        '                    retry_after = int(headers.get("Retry-After", "1"))\n'
        "                    self.last_retry_after = retry_after\n"
        "                    status, _ = self._transport(chunk, TIMEOUT_SEC)\n"
        "            except WebhookDeliveryError:\n"
        "                raise\n"
        "            except Exception as exc:\n"
        '                raise WebhookDeliveryError(f"transport failed: {exc}") from exc\n'
        "            if status >= 400:\n"
        '                raise WebhookDeliveryError(f"batch failed with status {status}")\n'
        "            delivered += len(chunk)"
    )
    assert old in text, "bug1 anchor missing in webhooks.py"
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


def fix_bug2_unconnected_silent_zero(repo: Path) -> None:
    p = repo / "src" / "webhooks.py"
    text = p.read_text(encoding="utf-8")
    old = "        if not self._connected:\n            return 0"
    new = '        if not self._connected:\n            raise RuntimeError("WebhookBatchClient must be connected before deliver_batch")'
    assert old in text, "bug2 anchor missing in webhooks.py"
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


PLANTED_BUGS = [
    PlantedBug(
        "bug1_swallowed_delivery_error",
        "deliver_batch swallows WebhookDeliveryError and transport errors returning None",
        fix_bug1_swallowed_delivery_error,
        attempts=1,
    ),
    PlantedBug(
        "bug2_unconnected_silent_zero",
        "deliver_batch silently returns 0 before connect() instead of failing explicitly",
        fix_bug2_unconnected_silent_zero,
        attempts=1,
    ),
]


def main() -> int:
    ws = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    code, _ = verify_reproductions(
        ws,
        PLANTED_BUGS,
        min_proven=1,
        require_all=("bug1_swallowed_delivery_error",),
    )
    return code


if __name__ == "__main__":
    sys.exit(main())
