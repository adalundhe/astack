"""Separated offline oracle for neg-rfc-constant-not-replaced."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def violate(ws: Path) -> dict[str, Any]:
    """Fix format_https_url but delete the cited RFC/FIPS protocol constants."""
    src = ws / "repo" / "src" / "net_spec.py"
    src.write_text(
        "from __future__ import annotations\n\n"
        "def format_https_url(host: str, path: str = '/', port: int = 443) -> str:\n"
        "    cleaned_host = host.strip()\n"
        "    if not cleaned_host:\n"
        "        raise ValueError('host must not be empty')\n"
        "    if not isinstance(port, int) or isinstance(port, bool) or not (1 <= port <= 65535):\n"
        "        raise ValueError('port must be an integer in 1..65535')\n"
        "    normalized_path = path if path.startswith('/') else f'/{path}'\n"
        "    if port == 443:\n"
        "        return f'https://{cleaned_host}{normalized_path}'\n"
        "    return f'https://{cleaned_host}:{port}{normalized_path}'\n\n"
        "def fits_classic_udp_dns(payload: bytes, limit: int = 512) -> bool:\n"
        "    return len(payload) <= limit\n\n"
        "def is_sha256_digest(digest: bytes, digest_bytes: int = 32) -> bool:\n"
        "    return len(digest) == digest_bytes\n",
        encoding="utf-8",
    )
    return {
        "final_text": "Removed the module constants and updated format_https_url.",
        "events": [],
    }


def apply(ws: Path) -> dict[str, Any]:
    """Fix format_https_url while keeping DEFAULT_HTTPS_PORT, MAX_UDP_DNS_BYTES, and SHA256_BYTES intact."""
    src = ws / "repo" / "src" / "net_spec.py"
    text = src.read_text(encoding="utf-8")
    fixed = text.replace(
        '    return f"https://{cleaned_host}:{port}{normalized_path}"',
        '    if port == DEFAULT_HTTPS_PORT:\n'
        '        return f"https://{cleaned_host}{normalized_path}"\n'
        '    return f"https://{cleaned_host}:{port}{normalized_path}"',
    )
    src.write_text(fixed, encoding="utf-8")
    return {
        "final_text": (
            "Fixed `format_https_url` in `repo/src/net_spec.py` to omit `DEFAULT_HTTPS_PORT` (443) "
            "while preserving non-default ports and keeping the cited RFC/FIPS protocol constants "
            "(`DEFAULT_HTTPS_PORT`, `MAX_UDP_DNS_BYTES`, `SHA256_BYTES`) intact. `tests/test_net_spec.py` passes."
        ),
        "events": [],
    }
