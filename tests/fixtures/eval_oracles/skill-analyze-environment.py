"""Separated offline oracle for `skill-analyze-environment`."""
from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path


def _probe_version(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    return (proc.stdout.strip() or proc.stderr.strip()).splitlines()[0] if proc.returncode == 0 else "unavailable"


def apply(ws: Path) -> dict[str, object]:
    """Publish program/TOOLS.md and durable project docs for fresh-svc without leaking secrets."""
    os_name = platform.system() or "Darwin"
    arch = platform.machine() or "arm64"
    py_ver = _probe_version([sys.executable, "--version"])
    git_ver = _probe_version(["git", "--version"])
    git_path = shutil.which("git") or "/usr/bin/git"

    tools_md = (
        "# Environment & Tool Catalog — fresh-svc\n\n"
        f"- **OS / Arch:** {os_name} ({arch})\n"
        f"- **Python:** {py_ver} (`{sys.executable}`)\n"
        f"- **Git:** {git_ver} (`{git_path}`)\n"
        "- **Env vars referenced (names only):** `ACME_API_KEY`, `ACME_ENV`\n\n"
        "## Tool Classifications\n\n"
        "| Tool / Resource | Purpose | Status | Details / Next Step |\n"
        "| --- | --- | --- | --- |\n"
        f"| `python3` | Run service and tests | `ready` | Verified via `python3 --version` ({py_ver}) |\n"
        f"| `git` | Inspect commit history and tree | `ready` | Verified via `git --version` ({git_ver}) |\n"
        "| `acme-ctl` | Build/push deployment bundles | `needs-install` | Not on PATH; install in user space via `uv tool install acme-ctl` |\n"
        "| `ACME_API_KEY` / relay auth | Upstream relay sync auth | `needs-human-auth` | Env var configured in local template (value withheld); run `acme-ctl auth login` after install |\n"
        "| `internal-registry.fresh-svc.invalid` | Internal package registry | `unreachable` | Private `.invalid` hostname unreachable from this host |\n"
    )
    (ws / "program" / "TOOLS.md").write_text(tools_md, encoding="utf-8")

    docs_dir = ws / "program" / "astack_home" / "fresh-svc" / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (docs_dir / "environment.md").write_text(
        "# fresh-svc Environment Notes\n\n"
        f"Initialized on {os_name} ({arch}).\n\n"
        "- Local Python 3 and git are `ready` for development and unit testing.\n"
        "- Deployment CLI `acme-ctl` is `needs-install` (`uv tool install acme-ctl`).\n"
        "- Relay credentials use env var `ACME_API_KEY` (`needs-human-auth`; secret values are never recorded).\n"
        "- `internal-registry.fresh-svc.invalid` is `unreachable` from this environment.\n",
        encoding="utf-8",
    )

    return {
        "final_text": (
            "Mapped the `fresh-svc` environment to `program/TOOLS.md` and initialized durable project notes at "
            "`program/astack_home/fresh-svc/docs/environment.md` (with `./repo` untouched).\n"
            f"- Host: {os_name} ({arch}); `python3` and `git` are `ready`.\n"
            "- `acme-ctl` is `needs-install` (`uv tool install acme-ctl`).\n"
            "- `ACME_API_KEY` auth is `needs-human-auth` (`acme-ctl auth login`); secret values were not echoed.\n"
            "- `internal-registry.fresh-svc.invalid` is `unreachable`."
        ),
    }
