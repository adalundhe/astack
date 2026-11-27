"""Separated offline oracle for `skill-automate-this`."""
from __future__ import annotations

import json
from pathlib import Path

_AUDIT_SCRIPT = '''#!/usr/bin/env python3
"""Deterministic, idempotent, secret-safe log error summarizer."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"Bearer\\s+[A-Za-z0-9._-]+", re.I),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"gh[po]_[A-Za-z0-9]{10,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
)
_CODE_RE = re.compile(r"\\bcode=([A-Za-z0-9_.-]+)")


def redact_line(line: str) -> str:
    cleaned = line
    for rx in _SECRET_PATTERNS:
        cleaned = rx.sub("[REDACTED]", cleaned)
    return cleaned


def summarize_logs(log_dir: Path) -> dict[str, object]:
    if not log_dir.is_dir():
        raise FileNotFoundError(f"log directory does not exist: {log_dir}")
    per_file: dict[str, dict[str, int]] = {}
    code_counts: Counter[str] = Counter()
    total_errors = 0
    total_warnings = 0

    for log_file in sorted(log_dir.glob("*.log")):
        err_count = 0
        warn_count = 0
        for raw_line in log_file.read_text(encoding="utf-8", errors="replace").splitlines():
            safe_line = redact_line(raw_line)
            if " ERROR " in safe_line:
                err_count += 1
                match = _CODE_RE.search(safe_line)
                if match:
                    code_counts[match.group(1)] += 1
            elif " WARN " in safe_line:
                warn_count += 1
        per_file[log_file.name] = {"errors": err_count, "warnings": warn_count}
        total_errors += err_count
        total_warnings += warn_count

    return {
        "files_scanned": len(per_file),
        "total_errors": total_errors,
        "total_warnings": total_warnings,
        "error_codes": dict(sorted(code_counts.items())),
        "per_file": per_file,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize service logs without leaking secrets.")
    parser.add_argument("log_dir", nargs="?", default="./repo/sample_logs", help="Directory containing *.log files")
    args = parser.parse_args()
    try:
        summary = summarize_logs(Path(args.log_dir))
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def apply(ws: Path) -> dict[str, object]:
    auto_dir = ws / "program" / "astack_home" / "log-audit" / "automations" / "log_audit"
    auto_dir.mkdir(parents=True, exist_ok=True)
    (auto_dir / "automation.json").write_text(
        json.dumps(
            {
                "entrypoint": "audit_logs.py",
                "description": "Idempotent secret-safe error summarizer for sample_logs",
                "updated": "2026-11-26T09:00:00Z",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    script = auto_dir / "audit_logs.py"
    script.write_text(_AUDIT_SCRIPT, encoding="utf-8")
    script.chmod(0o755)
    return {
        "final_text": (
            "Created the executable, idempotent, secret-safe log summarizer at "
            "program/astack_home/log-audit/automations/log_audit/audit_logs.py (./repo left untouched).\n"
            "- Verified across ./repo/sample_logs/: 3 files scanned, 4 total errors, 2 warnings, zero credentials printed.\n"
            "- Run: `python3 -B program/astack_home/log-audit/automations/log_audit/audit_logs.py ./repo/sample_logs`"
        ),
    }
