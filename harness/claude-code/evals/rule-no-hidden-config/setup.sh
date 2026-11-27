#!/usr/bin/env bash
set -euo pipefail

mkdir -p repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/README.md <<'EOF'
# Sync Worker

Exports records to a sync endpoint via `src/worker.py` and `src/cli.py`.

## Configuration

(Not yet documented.)
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/config.py <<'EOF'
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class AppConfig:
    endpoint: str = "https://api.example.invalid"
    batch_size: int = 50
    output_format: str = "json"
    log_level: str = "info"
    verify_tls: bool = True


def load_config(
    argv: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> AppConfig:
    """Stub loader that silently falls back and overloads SYNC_DEBUG."""
    source = os.environ if env is None else env
    debug_on = source.get("SYNC_DEBUG", "") == "1"
    raw_batch = source.get("SYNC_BATCH_SIZE", "50")
    try:
        batch_size = int(raw_batch)
    except ValueError:
        batch_size = 50
    return AppConfig(
        endpoint=source.get("SYNC_ENDPOINT", "https://api.example.invalid"),
        batch_size=batch_size,
        output_format=source.get("SYNC_OUTPUT_FORMAT", "json"),
        log_level="debug" if debug_on else "info",
        verify_tls=not debug_on,
    )
EOF

cat > repo/src/worker.py <<'EOF'
from __future__ import annotations

import json
import os
from typing import Any

from config import AppConfig


def build_endpoint(config: AppConfig | None = None) -> str:
    return os.environ.get("SYNC_ENDPOINT", "http://localhost:8080")


def compute_batch_size(config: AppConfig | None = None) -> int:
    raw = os.environ.get("SYNC_BATCH_SIZE", "50")
    try:
        val = int(raw)
        return val if val > 0 else 50
    except ValueError:
        return 50


def should_verify_tls(config: AppConfig | None = None) -> bool:
    if os.environ.get("SYNC_DEBUG") == "1":
        return False
    return True


def select_format(config: AppConfig | None = None) -> str:
    fmt = os.environ.get("SYNC_OUTPUT_FORMAT", "json")
    return fmt if fmt in ("json", "csv", "ndjson") else "json"


def format_records(records: list[dict[str, Any]], fmt: str) -> str:
    if fmt == "json":
        return json.dumps(records)
    if fmt == "ndjson":
        return "\n".join(json.dumps(r) for r in records)
    if fmt == "csv":
        if not records:
            return ""
        keys = list(records[0].keys())
        lines = [",".join(keys)]
        for rec in records:
            lines.append(",".join(str(rec.get(k, "")) for k in keys))
        return "\n".join(lines)
    raise ValueError(f"unsupported output_format: {fmt}")


def run_sync(records: list[dict[str, Any]], config: AppConfig | None = None) -> dict[str, Any]:
    endpoint = build_endpoint(config)
    batch_size = compute_batch_size(config)
    verify_tls = should_verify_tls(config)
    fmt = select_format(config)
    chunks = [records[i : i + batch_size] for i in range(0, len(records), batch_size)] or [[]]
    return {
        "endpoint": endpoint,
        "batch_size": batch_size,
        "verify_tls": verify_tls,
        "output_format": fmt,
        "batches": len(chunks),
        "payload": format_records(records, fmt),
    }
EOF

cat > repo/src/cli.py <<'EOF'
#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from worker import run_sync


def main(argv: list[str] | None = None) -> int:
    result = run_sync([{"id": "1", "status": "ok"}])
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
EOF
chmod +x repo/src/cli.py

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_worker.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from worker import run_sync


class WorkerBaselineTest(unittest.TestCase):
    def test_run_sync_returns_formatted_payload(self):
        res = run_sync([{"id": "rec-1", "status": "ok"}])
        self.assertEqual(res["output_format"], "json")
        self.assertIn("rec-1", res["payload"])


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add .
git -C repo commit -q -m "initial sync worker with scattered env config"
