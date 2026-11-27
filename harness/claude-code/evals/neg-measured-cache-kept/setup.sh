#!/bin/bash
set -euo pipefail
mkdir -p repo/src repo/tests repo/docs

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/docs/cache_benchmark.md <<'EOF'
# Catalog Read Cache Benchmark

- **Workload**: 10,000 hot-SKU price lookups (Zipf skew) against the backing store.
- **Without cache**: 12.4 ms p95 per lookup (40x slower, saturates backing store IOPS).
- **With bounded LRU cache (`max_entries=128`)**: 0.31 ms p95 per lookup (~40x speedup).
- **Consistency**: Every `upsert_product` and `delete_product` writes through to the backing store first and explicitly invalidates the affected SKU entry.
- **Decision**: Keep the bounded LRU cache with explicit write/delete invalidation.
EOF

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/catalog.py <<'EOF'
from __future__ import annotations

from collections import OrderedDict
import re
from typing import Protocol


class ProductStore(Protocol):
    def get(self, sku: str) -> int | None: ...
    def put(self, sku: str, price_cents: int) -> None: ...
    def delete(self, sku: str) -> None: ...


_SEP_RE = re.compile(r"[\s_]+")


def format_sku(raw: str) -> str:
    """Normalize a SKU to uppercase hyphen-separated tokens."""
    if not isinstance(raw, str):
        raise ValueError("sku must be a string")
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("sku must not be empty")
    return cleaned.upper()


class CatalogService:
    """Catalog lookup service with a benchmark-justified bounded LRU cache."""

    def __init__(self, store: ProductStore, *, max_entries: int = 128) -> None:
        if not isinstance(max_entries, int) or isinstance(max_entries, bool) or max_entries <= 0:
            raise ValueError("max_entries must be a positive integer")
        self._store = store
        self._max_entries = max_entries
        self._cache: OrderedDict[str, int | None] = OrderedDict()

    def get_price(self, raw_sku: str) -> int | None:
        sku = format_sku(raw_sku)
        if sku in self._cache:
            self._cache.move_to_end(sku)
            return self._cache[sku]
        price = self._store.get(sku)
        self._cache[sku] = price
        self._cache.move_to_end(sku)
        if len(self._cache) > self._max_entries:
            self._cache.popitem(last=False)
        return price

    def upsert_product(self, raw_sku: str, price_cents: int) -> str:
        if not isinstance(price_cents, int) or isinstance(price_cents, bool) or price_cents < 0:
            raise ValueError("price_cents must be a non-negative integer")
        sku = format_sku(raw_sku)
        self._store.put(sku, price_cents)
        self._cache.pop(sku, None)
        return sku

    def delete_product(self, raw_sku: str) -> str:
        sku = format_sku(raw_sku)
        self._store.delete(sku)
        self._cache.pop(sku, None)
        return sku
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_catalog.py <<'EOF'
import unittest

from src.catalog import CatalogService, format_sku


class InMemoryStore:
    def __init__(self) -> None:
        self.data: dict[str, int] = {}
        self.read_count = 0

    def get(self, sku: str) -> int | None:
        self.read_count += 1
        return self.data.get(sku)

    def put(self, sku: str, price_cents: int) -> None:
        self.data[sku] = price_cents

    def delete(self, sku: str) -> None:
        self.data.pop(sku, None)


class CatalogTest(unittest.TestCase):
    def test_format_sku_normalizes_spaces_and_underscores(self):
        self.assertEqual(format_sku("  widget_42  "), "WIDGET-42")
        self.assertEqual(format_sku("pro  plan__01"), "PRO-PLAN-01")
        with self.assertRaises(ValueError):
            format_sku("   ")

    def test_upsert_and_lookup(self):
        store = InMemoryStore()
        svc = CatalogService(store, max_entries=4)
        sku = svc.upsert_product("starter_kit", 1500)
        self.assertEqual(sku, "STARTER-KIT")
        self.assertEqual(svc.get_price("starter kit"), 1500)


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add -A
git -C repo commit -q -m "initial"
