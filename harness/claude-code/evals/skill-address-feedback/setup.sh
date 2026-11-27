#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval User"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/pages.py <<'EOF'
"""1-indexed pagination helper."""
from __future__ import annotations


def paginate(items: list, page: int, page_size: int) -> dict:
    """Return a 1-indexed page slice and pagination metadata."""
    if page < 1:
        raise ValueError("page must be >= 1")
    if page_size < 1:
        raise ValueError("page_size must be >= 1")
    start = page * page_size
    end = start + page_size
    total = len(items)
    total_pages = (total + page_size - 1) // page_size
    return {
        "items": items[start:end],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": end < total,
    }
EOF

cat > repo/tests/test_pages.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pages import paginate


class PagesTest(unittest.TestCase):
    def test_rejects_invalid_arguments(self):
        with self.assertRaises(ValueError):
            paginate([1, 2, 3], page=0, page_size=2)
        with self.assertRaises(ValueError):
            paginate([1, 2, 3], page=1, page_size=0)

    def test_returns_page_size_slice(self):
        res = paginate([1, 2, 3, 4, 5], page=1, page_size=2)
        self.assertEqual(len(res["items"]), 2)
        self.assertEqual(res["total"], 5)
EOF

git -C repo add .
git -C repo commit -q -m "initial pagination helper"

cat > program/review_threads.json <<'EOF'
{
  "pr_number": 17,
  "threads": [
    {
      "id": "thread-1",
      "severity": "blocking",
      "path": "src/pages.py",
      "line": 11,
      "author": "reviewer-1",
      "comment": "Off-by-one pagination bug: `start = page * page_size` treats 1-indexed `page` as 0-indexed, so `page=1` skips the first page of items. Use `(page - 1) * page_size` and add a test asserting exact items for page 1, middle pages, and the final page."
    },
    {
      "id": "thread-2",
      "severity": "blocking",
      "path": "tests/test_pages.py",
      "line": 1,
      "author": "reviewer-2",
      "comment": "Missing empty-input test: add a regression test verifying `paginate([], page=1, page_size=5)` returns `items=[]`, `total=0`, `total_pages=0`, and `has_next=False`."
    }
  ]
}
EOF
