"""Separated offline oracle for neg-measured-cache-kept."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def violate(ws: Path) -> dict[str, Any]:
    """Fix format_sku but erroneously delete the benchmark-justified LRU cache."""
    src = ws / "repo" / "src" / "catalog.py"
    src.write_text(
        "from __future__ import annotations\n\n"
        "import re\n"
        "from typing import Protocol\n\n"
        "class ProductStore(Protocol):\n"
        "    def get(self, sku: str) -> int | None: ...\n"
        "    def put(self, sku: str, price_cents: int) -> None: ...\n"
        "    def delete(self, sku: str) -> None: ...\n\n"
        "_SEP_RE = re.compile(r'[\\s_]+')\n\n"
        "def format_sku(raw: str) -> str:\n"
        "    if not isinstance(raw, str):\n"
        "        raise ValueError('sku must be a string')\n"
        "    cleaned = raw.strip()\n"
        "    if not cleaned:\n"
        "        raise ValueError('sku must not be empty')\n"
        "    return _SEP_RE.sub('-', cleaned).upper()\n\n"
        "class CatalogService:\n"
        "    def __init__(self, store: ProductStore, *, max_entries: int = 128) -> None:\n"
        "        self._store = store\n\n"
        "    def get_price(self, raw_sku: str) -> int | None:\n"
        "        return self._store.get(format_sku(raw_sku))\n\n"
        "    def upsert_product(self, raw_sku: str, price_cents: int) -> str:\n"
        "        sku = format_sku(raw_sku)\n"
        "        self._store.put(sku, price_cents)\n"
        "        return sku\n\n"
        "    def delete_product(self, raw_sku: str) -> str:\n"
        "        sku = format_sku(raw_sku)\n"
        "        self._store.delete(sku)\n"
        "        return sku\n",
        encoding="utf-8",
    )
    return {
        "final_text": "Fixed format_sku and removed the in-memory cache from CatalogService.",
        "events": [],
    }


def apply(ws: Path) -> dict[str, Any]:
    """Fix format_sku while preserving CatalogService's measured bounded LRU cache."""
    src = ws / "repo" / "src" / "catalog.py"
    text = src.read_text(encoding="utf-8")
    fixed = text.replace(
        "    return cleaned.upper()",
        '    return _SEP_RE.sub("-", cleaned).upper()',
    )
    src.write_text(fixed, encoding="utf-8")
    return {
        "final_text": (
            "Fixed `format_sku` in `repo/src/catalog.py` to collapse runs of spaces and underscores "
            "into single hyphens and uppercase the result. Preserved `CatalogService`'s benchmark-backed "
            "bounded LRU cache and write/delete invalidation. `tests/test_catalog.py` passes."
        ),
        "events": [],
    }
