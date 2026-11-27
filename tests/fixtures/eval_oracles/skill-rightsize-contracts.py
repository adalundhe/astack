"""Separated offline oracle for `skill-rightsize-contracts`."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_ASTACK_TOOLS = Path(__file__).resolve().parents[3] / "bin" / "astack-tools"

CATALOG_MD = """# Payments SDK Contract Catalog & Rightsizing Plan

## 1. Observed Contract Surface
- `src/sdk.py:8-23` — `create_charge(...)` currently exposes 14 top-level keyword parameters.
- `src/sdk.py:34` — `PAYMENTS_API_KEY` environment fallback.
- `src/sdk.py:49` — Undocumented hidden environment toggle `PAYMENTS_SDK_FORCE_SYNC_FALLBACK` that silently alters execution mode.
- Real callers inspected: `examples/quickstart.py:4-8` (Tier 0 basic charge) and `tests/test_sdk.py:6-24` (Tier 0 defaults + Tier 1 currency/timeout/retry tuning). Neither caller uses any alias, `environment`, `base_url`, `retry_enabled`, `legacy_xml_envelope`, or `PAYMENTS_SDK_FORCE_SYNC_FALLBACK`.

## 2. Stepped-Complexity Ladder (Target Right-Sized Contract)
- **Tier 0 — Basic Charge (minimum surface, sensible defaults):**
  `create_charge(amount_cents: int, customer_id: str, *, api_key: str | None = None)`
  - Defaults: `currency="USD"`, environment auto-derived from `api_key` prefix (`live_` vs `test_`), `timeout_ms=5000`, `max_retries=2`.
- **Tier 1 — Multi-Currency & Explicit Control:**
  Add optional `currency: str = "USD"` directly on `create_charge`.
- **Tier 2 — Advanced Transport & Retry Tuning:**
  Group `timeout_ms: int = 5000`, `max_retries: int = 2` (`0` disables retries), and `base_url: str | None = None` into an optional `transport: TransportConfig | None = None` object so basic callers never wade through transport knobs.

## 3. Specific Surface Reductions

| Touchpoint (`file:line`) | Complexity Defect | Proposed Right-Sized Contract | Migration Safety |
| --- | --- | --- | --- |
| `src/sdk.py:9-10` (`amount` vs `amount_cents`) | Duplicate alias for minor-unit integer amount | Keep `amount_cents` only; drop `amount` | Emit `DeprecationWarning` for one minor release before removing in v2 |
| `src/sdk.py:11-12` (`currency_code` vs `currency`) | Duplicate alias for ISO currency | Keep `currency="USD"` only; drop `currency_code` | Deprecate with warning, remove in v2 |
| `src/sdk.py:13-14` (`cust_id` vs `customer_id`) | Duplicate abbreviated alias | Keep `customer_id` only; drop `cust_id` | Deprecate with warning, remove in v2 |
| `src/sdk.py:18-19` (`timeout_seconds` vs `timeout_ms`) | Duplicate unit-mismatched timeout parameter | Keep `timeout_ms=5000` inside Tier-2 `TransportConfig`; drop `timeout_seconds` | Deprecate with warning, remove in v2 |
| `src/sdk.py:20-21` (`retry_enabled` vs `max_retries`) | Redundant boolean toggle duplicating `max_retries=0` | Keep `max_retries=2` (`0` disables retries); drop `retry_enabled` | Map `retry_enabled=False` -> `max_retries=0` with deprecation warning during rollout |
| `src/sdk.py:16` (`environment`) | Redundant option already derivable from `api_key` prefix (`live_`/`test_`) | Derive automatically from `api_key` prefix; allow explicit `base_url` override in Tier 2 only | Warn on mismatch against key prefix, remove in v2 |
| `src/sdk.py:22` (`legacy_xml_envelope`) | Dead bolt-on parameter ignored at `src/sdk.py:52` | Delete dead parameter | Log deprecation notice if caller passes `True`, drop in v2 |
| `src/sdk.py:49` (`PAYMENTS_SDK_FORCE_SYNC_FALLBACK`) | Hidden undocumented env toggle silently changing behavior | Remove hidden env toggle (or expose explicit documented Tier-2 option if genuinely needed) | Audit production env configs before removal so no live service depends on it |
"""


def apply(ws: Path) -> dict[str, object]:
    """Publish reduction catalog under ASTACK_HOME/payments-sdk/docs/contracts/ without touching ./repo."""
    astack_home = (ws / "program" / "astack_home").resolve()
    env = {**os.environ, "ASTACK_HOME": str(astack_home)}
    out_path = subprocess.run(
        [
            sys.executable, "-B", str(_ASTACK_TOOLS),
            "docs", "path", "payments-sdk", "contracts",
            "--file", "sdk-contracts.md", "--ensure",
        ],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    ).stdout.strip()
    Path(out_path).write_text(CATALOG_MD, encoding="utf-8")
    return {
        "final_text": (
            f"Published the payments-sdk contract reduction catalog to `{out_path}` without modifying `./repo`. "
            "Collapsed 14 overlapping parameters in `src/sdk.py:8-23` into a 3-tier stepped-complexity contract "
            "(removing duplicate aliases `amount`, `currency_code`, `cust_id`, `timeout_seconds`, redundant `retry_enabled`/`environment`, "
            "dead `legacy_xml_envelope`, and hidden env toggle `PAYMENTS_SDK_FORCE_SYNC_FALLBACK`)."
        ),
    }
