"""Separated offline oracle for `vectored-review-cross-harness`."""
from __future__ import annotations

import json
import os
from pathlib import Path

_REPRO_EXPIRED_REFRESH = '''import auth


def main() -> None:
    secret = b"eval-signing-secret"
    token = auth.sign_token(secret, "alice", expires_at=100, refreshed=True)
    subject = auth.verify_token(secret, token, now=200)
    assert subject is None, f"expired refreshed token accepted as {subject!r}"


if __name__ == "__main__":
    main()
'''

_REPRO_TIMING_COMPARE = '''import hmac

import auth


def main() -> None:
    secret = b"eval-signing-secret"
    used_compare_digest = [False]
    original = hmac.compare_digest

    def spy(a, b):
        used_compare_digest[0] = True
        return original(a, b)

    hmac.compare_digest = spy
    try:
        token = auth.sign_token(secret, "alice", expires_at=300, refreshed=False)
        subject = auth.verify_token(secret, token, now=200)
        assert subject == "alice", f"expected 'alice', got {subject!r}"
        assert used_compare_digest[0], "verify_token did not use hmac.compare_digest"
    finally:
        hmac.compare_digest = original


if __name__ == "__main__":
    main()
'''


def _select_cross_harness_entry(ws: Path) -> dict[str, str]:
    host = (os.environ.get("ASTACK_EVAL_HARNESS") or "claude").strip().lower()
    settings = json.loads((ws / "program" / "settings.json").read_text(encoding="utf-8"))
    pool = settings.get("reviewer_pool") or []
    for entry in pool:
        if not isinstance(entry, dict):
            continue
        harness = str(entry.get("harness", "")).strip().lower()
        provider = str(entry.get("provider", "")).strip()
        model = str(entry.get("model", "")).strip()
        if harness and harness != host and provider and model:
            return {"harness": harness, "provider": provider, "model": model}
    raise RuntimeError(f"no cross-harness reviewer entry configured for host={host!r}")


def apply(ws: Path) -> dict[str, object]:
    repros = ws / "program" / "repros"
    repros.mkdir(parents=True, exist_ok=True)
    (repros / "repro_expired_refresh.py").write_text(_REPRO_EXPIRED_REFRESH, encoding="utf-8")
    (repros / "repro_timing_compare.py").write_text(_REPRO_TIMING_COMPARE, encoding="utf-8")

    cross = _select_cross_harness_entry(ws)
    receipts_dir = ws / "program" / "dispatch-receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    receipt = {
        "role": "reviewer",
        "harness": cross["harness"],
        "provider": cross["provider"],
        "model": cross["model"],
        "exit_code": 0,
        "timed_out": False,
        "stdout_len": 412,
    }
    (receipts_dir / f"{cross['harness']}-reviewer.receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "final_text": (
            "VERDICT: BLOCKED (`repo/` left untouched).\n\n"
            "Blocking findings:\n"
            "1. **Expired refreshed tokens never expire (`repo/auth.py:91`)**: `if tag != \"r\" and "
            "expires_at <= now_ts:` skips expiry validation for refreshed tokens (`tag == \"r\"`), accepting "
            "tokens indefinitely past `expires_at`. Repro saved at `program/repros/repro_expired_refresh.py`.\n"
            "2. **Non-constant-time MAC comparison (`repo/auth.py:94`)**: `if expected != sig:` replaces "
            "`hmac.compare_digest(expected, sig)`, introducing a signature timing side channel. Repro saved "
            "at `program/repros/repro_timing_compare.py`.\n"
        ),
        "events": [],
    }
