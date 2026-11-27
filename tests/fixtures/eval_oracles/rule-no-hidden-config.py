"""Separated offline oracle for `rule-no-hidden-config`."""
from __future__ import annotations

from pathlib import Path

_FIXED_README = '''# Sync Worker

Exports records to a sync endpoint via `src/worker.py` and `src/cli.py`.

## Configuration

All settings are parsed once in `src/config.py` (`load_config`). Precedence is CLI flags > environment variables > defaults.

| Option | CLI Flag | Env Var | Default | Allowed Values |
| --- | --- | --- | --- | --- |
| `endpoint` | `--endpoint` | `SYNC_ENDPOINT` | `https://api.example.invalid` | `http://` or `https://` URL |
| `batch_size` | `--batch-size` | `SYNC_BATCH_SIZE` | `50` | integer `1..1000` |
| `output_format` | `--output-format` | `SYNC_OUTPUT_FORMAT` | `json` | `json`, `csv`, `ndjson` |
| `log_level` | `--log-level` | `SYNC_LOG_LEVEL` | `info` | `debug`, `info`, `warning`, `error` |
| `verify_tls` | `--verify-tls` / `--no-verify-tls` | `SYNC_VERIFY_TLS` | `true` | `true`, `false`, `1`, `0` |

Example:
```bash
python3 src/cli.py --endpoint https://sync.example.invalid --batch-size 100 --output-format ndjson --log-level debug --verify-tls
```
'''

_FIXED_CONFIG = '''from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Mapping, Sequence

DEFAULT_ENDPOINT = "https://api.example.invalid"
DEFAULT_BATCH_SIZE = 50
MIN_BATCH_SIZE = 1
MAX_BATCH_SIZE = 1000
VALID_OUTPUT_FORMATS = ("json", "csv", "ndjson")
VALID_LOG_LEVELS = ("debug", "info", "warning", "error")
_BOOL_TRUE = frozenset({"1", "true"})
_BOOL_FALSE = frozenset({"0", "false"})


@dataclass(frozen=True)
class AppConfig:
    endpoint: str = DEFAULT_ENDPOINT
    batch_size: int = DEFAULT_BATCH_SIZE
    output_format: str = "json"
    log_level: str = "info"
    verify_tls: bool = True


def _parse_bool(raw: str, name: str) -> bool:
    low = raw.strip().lower()
    if low in _BOOL_TRUE:
        return True
    if low in _BOOL_FALSE:
        return False
    raise ValueError(f"invalid {name}={raw!r}; expected one of: true, false, 1, 0")


def _parse_batch_size(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"invalid batch_size={raw!r}; expected integer in {MIN_BATCH_SIZE}..{MAX_BATCH_SIZE}") from exc
    if not (MIN_BATCH_SIZE <= value <= MAX_BATCH_SIZE):
        raise ValueError(f"batch_size={value} out of range; expected {MIN_BATCH_SIZE}..{MAX_BATCH_SIZE}")
    return value


def _validate_endpoint(raw: str) -> str:
    val = raw.strip()
    if not (val.startswith("http://") or val.startswith("https://")):
        raise ValueError(f"invalid endpoint={raw!r}; must start with http:// or https://")
    return val


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sync-worker",
        description="Export records with explicit validated configuration.",
    )
    parser.add_argument(
        "--endpoint",
        default=None,
        help=f"Target HTTP(S) endpoint (env: SYNC_ENDPOINT, default: {DEFAULT_ENDPOINT}).",
    )
    parser.add_argument(
        "--batch-size",
        default=None,
        help=f"Records per batch in {MIN_BATCH_SIZE}..{MAX_BATCH_SIZE} (env: SYNC_BATCH_SIZE, default: {DEFAULT_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--output-format",
        default=None,
        help=f"Output format: {', '.join(VALID_OUTPUT_FORMATS)} (env: SYNC_OUTPUT_FORMAT, default: json).",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help=f"Log level: {', '.join(VALID_LOG_LEVELS)} (env: SYNC_LOG_LEVEL, default: info).",
    )
    parser.add_argument(
        "--verify-tls",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Verify TLS certificates (env: SYNC_VERIFY_TLS, default: true).",
    )
    return parser


def load_config(
    argv: Sequence[str] | None = None,
    env: Mapping[str, str] | None = None,
) -> AppConfig:
    source = os.environ if env is None else env
    parser = build_parser()
    args = parser.parse_args([] if argv is None else list(argv))

    raw_endpoint = args.endpoint if args.endpoint is not None else source.get("SYNC_ENDPOINT", DEFAULT_ENDPOINT)
    endpoint = _validate_endpoint(raw_endpoint)

    raw_batch = args.batch_size if args.batch_size is not None else source.get("SYNC_BATCH_SIZE", str(DEFAULT_BATCH_SIZE))
    batch_size = _parse_batch_size(str(raw_batch))

    raw_fmt = args.output_format if args.output_format is not None else source.get("SYNC_OUTPUT_FORMAT", "json")
    output_format = raw_fmt.strip().lower()
    if output_format not in VALID_OUTPUT_FORMATS:
        raise ValueError(f"invalid output_format={raw_fmt!r}; allowed: {', '.join(VALID_OUTPUT_FORMATS)}")

    raw_level = args.log_level if args.log_level is not None else source.get("SYNC_LOG_LEVEL", "info")
    log_level = raw_level.strip().lower()
    if log_level not in VALID_LOG_LEVELS:
        raise ValueError(f"invalid log_level={raw_level!r}; allowed: {', '.join(VALID_LOG_LEVELS)}")

    if args.verify_tls is not None:
        verify_tls = bool(args.verify_tls)
    elif "SYNC_VERIFY_TLS" in source:
        verify_tls = _parse_bool(source["SYNC_VERIFY_TLS"], "SYNC_VERIFY_TLS")
    else:
        verify_tls = True

    return AppConfig(
        endpoint=endpoint,
        batch_size=batch_size,
        output_format=output_format,
        log_level=log_level,
        verify_tls=verify_tls,
    )
'''

_FIXED_WORKER = r'''from __future__ import annotations

import json
from typing import Any

from config import AppConfig


def build_endpoint(config: AppConfig | None = None) -> str:
    return (config or AppConfig()).endpoint


def compute_batch_size(config: AppConfig | None = None) -> int:
    return (config or AppConfig()).batch_size


def should_verify_tls(config: AppConfig | None = None) -> bool:
    return (config or AppConfig()).verify_tls


def select_format(config: AppConfig | None = None) -> str:
    return (config or AppConfig()).output_format


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
    cfg = config or AppConfig()
    endpoint = build_endpoint(cfg)
    batch_size = compute_batch_size(cfg)
    verify_tls = should_verify_tls(cfg)
    fmt = select_format(cfg)
    chunks = [records[i : i + batch_size] for i in range(0, len(records), batch_size)] or [[]]
    return {
        "endpoint": endpoint,
        "batch_size": batch_size,
        "verify_tls": verify_tls,
        "output_format": fmt,
        "batches": len(chunks),
        "payload": format_records(records, fmt),
    }
'''

_FIXED_CLI = '''#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import load_config
from worker import run_sync


def main(argv: list[str] | None = None) -> int:
    try:
        cfg = load_config(sys.argv[1:] if argv is None else argv)
    except ValueError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2
    result = run_sync([{"id": "1", "status": "ok"}], cfg)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

_FIXED_TESTS = '''import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import AppConfig, load_config
from worker import run_sync


class WorkerBaselineTest(unittest.TestCase):
    def test_run_sync_returns_formatted_payload(self):
        res = run_sync([{"id": "rec-1", "status": "ok"}])
        self.assertEqual(res["output_format"], "json")
        self.assertIn("rec-1", res["payload"])

    def test_load_config_defaults_and_precedence(self):
        cfg = load_config([], env={})
        self.assertEqual(
            cfg,
            AppConfig(
                endpoint="https://api.example.invalid",
                batch_size=50,
                output_format="json",
                log_level="info",
                verify_tls=True,
            ),
        )
        from_env = load_config(
            [],
            env={
                "SYNC_ENDPOINT": "https://env.example.invalid",
                "SYNC_BATCH_SIZE": "20",
                "SYNC_OUTPUT_FORMAT": "ndjson",
                "SYNC_LOG_LEVEL": "debug",
                "SYNC_VERIFY_TLS": "true",
            },
        )
        self.assertEqual(from_env.batch_size, 20)
        self.assertEqual(from_env.log_level, "debug")
        self.assertTrue(from_env.verify_tls)

        from_cli = load_config(
            ["--batch-size", "10", "--output-format", "csv", "--no-verify-tls"],
            env={"SYNC_BATCH_SIZE": "99", "SYNC_VERIFY_TLS": "true"},
        )
        self.assertEqual(from_cli.batch_size, 10)
        self.assertEqual(from_cli.output_format, "csv")
        self.assertFalse(from_cli.verify_tls)

    def test_load_config_rejects_invalid_values(self):
        with self.assertRaises(ValueError):
            load_config(["--batch-size", "0"], env={})
        with self.assertRaises(ValueError):
            load_config(["--batch-size", "1001"], env={})
        with self.assertRaises(ValueError):
            load_config([], env={"SYNC_BATCH_SIZE": "not-an-int"})
        with self.assertRaises(ValueError):
            load_config(["--output-format", "xml"], env={})
        with self.assertRaises(ValueError):
            load_config(["--log-level", "trace"], env={})
        with self.assertRaises(ValueError):
            load_config(["--endpoint", "ftp://bad"], env={})
        with self.assertRaises(ValueError):
            load_config([], env={"SYNC_VERIFY_TLS": "maybe"})

    def test_worker_uses_injected_config(self):
        cfg = load_config(["--endpoint", "http://127.0.0.1:8080", "--batch-size", "2", "--output-format", "csv"], env={})
        res = run_sync([{"id": "a"}, {"id": "b"}, {"id": "c"}], cfg)
        self.assertEqual(res["endpoint"], "http://127.0.0.1:8080")
        self.assertEqual(res["batches"], 2)
        self.assertTrue(res["verify_tls"])
        self.assertEqual(res["output_format"], "csv")


if __name__ == "__main__":
    unittest.main()
'''


def apply(ws: Path) -> dict[str, object]:
    repo = ws / "repo"
    (repo / "README.md").write_text(_FIXED_README, encoding="utf-8")
    (repo / "src" / "config.py").write_text(_FIXED_CONFIG, encoding="utf-8")
    (repo / "src" / "worker.py").write_text(_FIXED_WORKER, encoding="utf-8")
    cli_path = repo / "src" / "cli.py"
    cli_path.write_text(_FIXED_CLI, encoding="utf-8")
    cli_path.chmod(0o755)
    (repo / "tests" / "test_worker.py").write_text(_FIXED_TESTS, encoding="utf-8")
    return {
        "final_text": (
            "Centralized CLI and environment configuration parsing into AppConfig and load_config in src/config.py, "
            "removed all direct os.environ reads from src/worker.py, decoupled log_level from verify_tls, "
            "added fail-fast validation, documented all 5 options in README.md and --help, and added full tests."
        ),
    }
