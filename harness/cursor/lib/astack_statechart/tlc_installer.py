"""Pinned, atomic, SHA-256-verified TLC (tla2tools.jar) installer for astack-statechart.

Installs the immutable official TLA+ Tools v1.7.4 (TLC2 Version 2.19) jar into
user-space storage (`~/.local/share/tla+/tla2tools.jar` on macOS/Linux or
`%LOCALAPPDATA%\\tla+\\tla2tools.jar` on Windows) with streaming SHA-256 checks,
ZIP/JAR class verification, and atomic rename (`safe-to-rerun`).
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

DEFAULT_TLC_VERSION = "1.7.4"
DEFAULT_TLC_URL = "https://github.com/tlaplus/tlaplus/releases/download/v1.7.4/tla2tools.jar"
DEFAULT_TLC_SHA256 = "936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88"


class TLCInstallError(RuntimeError):
    """Raised when downloading or verifying tla2tools.jar fails."""


def default_tlc_jar_path() -> Path:
    """Return cross-OS user-space install path for tla2tools.jar."""
    if env_jar := os.environ.get("ASTACK_TLC_JAR"):
        return Path(env_jar).expanduser()
    if xdg := os.environ.get("XDG_DATA_HOME"):
        return Path(xdg).expanduser() / "tla+" / "tla2tools.jar"
    if os.name == "nt":
        local_app = os.environ.get("LOCALAPPDATA")
        base = Path(local_app) if local_app else Path.home() / "AppData" / "Local"
        return base / "tla+" / "tla2tools.jar"
    return Path.home() / ".local" / "share" / "tla+" / "tla2tools.jar"


def java_install_hint() -> str:
    if sys.platform == "darwin":
        return "brew install openjdk  (or install Temurin JDK from https://adoptium.net)"
    if os.name == "nt":
        return "winget install EclipseAdoptium.Temurin.21.JRE"
    return "sudo apt-get install -y default-jre-headless  (or install OpenJDK 17+)"


def _probe_java() -> tuple[str | None, bool, str]:
    java = shutil.which("java")
    if not java:
        return None, False, ""
    try:
        proc = subprocess.run([java, "-version"], capture_output=True, text=True, timeout=5)
        out = (proc.stderr or proc.stdout or "").strip().splitlines()
        return java, proc.returncode == 0, (out[0] if out else "")
    except (OSError, subprocess.SubprocessError):
        return java, False, ""


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(1 << 16)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def verify_jar(path: Path, expected_sha256: str | None = None) -> tuple[bool, str, str]:
    """Verify path is a valid ZIP/JAR containing tlc2/TLC.class and optional SHA-256."""
    if not path.is_file():
        return False, "", f"file does not exist: {path}"
    digest = _sha256_file(path)
    if expected_sha256:
        want = expected_sha256.strip().lower()
        if digest.lower() != want:
            return False, digest, f"SHA-256 mismatch: expected {want}, got {digest}"
    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = set(zf.namelist())
            if "tlc2/TLC.class" not in names:
                return False, digest, "archive does not contain tlc2/TLC.class"
    except (zipfile.BadZipFile, OSError) as exc:
        return False, digest, f"invalid JAR archive: {exc}"
    return True, digest, "ok"


def _probe_tlc_version(java: str, jar: Path) -> str:
    try:
        proc = subprocess.run(
            [java, "-cp", str(jar), "tlc2.TLC", "-h"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
        for line in combined.splitlines():
            if "TLC2 Version" in line or "TLC Version" in line:
                return line.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def install_tlc(
    *,
    dest: Path | None = None,
    url: str | None = None,
    expected_sha256: str | None = None,
    force: bool = False,
    timeout: float = 120.0,
) -> dict[str, Any]:
    """Download, verify, and atomically install tla2tools.jar. Idempotent and crash-safe."""
    target = (dest or default_tlc_jar_path()).expanduser().resolve()
    use_default = not url or url == DEFAULT_TLC_URL
    source_url = url or DEFAULT_TLC_URL
    sha_to_check = expected_sha256 if expected_sha256 is not None else (DEFAULT_TLC_SHA256 if use_default else None)

    java_path, java_ok, java_ver = _probe_java()

    # Idempotent fast path: already installed and verified
    if not force and target.is_file():
        ok, digest, reason = verify_jar(target, expected_sha256=sha_to_check)
        if ok:
            tlc_ver = _probe_tlc_version(java_path, target) if (java_path and java_ok) else ""
            return {
                "installed": True,
                "already_installed": True,
                "jar": str(target),
                "version": DEFAULT_TLC_VERSION if use_default else "custom",
                "url": source_url,
                "sha256": digest,
                "sha256_verified": bool(sha_to_check),
                "java_found": java_ok,
                "java_path": java_path if java_ok else None,
                "java_version": java_ver,
                "tlc_version": tlc_ver,
                "java_install_hint": None if java_ok else java_install_hint(),
            }

    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_name(f".{target.name}.tmp.{os.getpid()}")

    try:
        req = urllib.request.Request(
            source_url,
            headers={"User-Agent": "astack-statechart/1.0 (https://github.com/adalundhe/astack)"},
        )
        hasher = hashlib.sha256()
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp_path, "wb") as out:
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                hasher.update(chunk)
                out.write(chunk)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        tmp_path.unlink(missing_ok=True)
        raise TLCInstallError(f"failed to download TLC from {source_url}: {exc}") from exc

    ok, digest, reason = verify_jar(tmp_path, expected_sha256=sha_to_check)
    if not ok:
        tmp_path.unlink(missing_ok=True)
        raise TLCInstallError(f"downloaded TLC archive failed verification ({reason})")

    try:
        os.replace(tmp_path, target)
    except OSError as exc:
        tmp_path.unlink(missing_ok=True)
        raise TLCInstallError(f"failed to move verified jar into place at {target}: {exc}") from exc

    tlc_ver = _probe_tlc_version(java_path, target) if (java_path and java_ok) else ""
    return {
        "installed": True,
        "already_installed": False,
        "jar": str(target),
        "version": DEFAULT_TLC_VERSION if use_default else "custom",
        "url": source_url,
        "sha256": digest,
        "sha256_verified": bool(sha_to_check),
        "java_found": java_ok,
        "java_path": java_path if java_ok else None,
        "java_version": java_ver,
        "tlc_version": tlc_ver,
        "java_install_hint": None if java_ok else java_install_hint(),
    }
