"""Separated offline oracle for `skill-address-feedback`."""
from __future__ import annotations

import json
from pathlib import Path


def apply(ws: Path) -> dict[str, object]:
    """Fix the off-by-one pagination bug, add regression tests, and record per-thread resolution proof."""
    repo = ws / "repo"
    (repo / "src" / "pages.py").write_text(
        '"""1-indexed pagination helper."""\n'
        "from __future__ import annotations\n\n\n"
        "def paginate(items: list, page: int, page_size: int) -> dict:\n"
        '    """Return a 1-indexed page slice and pagination metadata."""\n'
        "    if page < 1:\n"
        '        raise ValueError("page must be >= 1")\n'
        "    if page_size < 1:\n"
        '        raise ValueError("page_size must be >= 1")\n'
        "    start = (page - 1) * page_size\n"
        "    end = start + page_size\n"
        "    total = len(items)\n"
        "    total_pages = (total + page_size - 1) // page_size\n"
        "    return {\n"
        '        "items": items[start:end],\n'
        '        "page": page,\n'
        '        "page_size": page_size,\n'
        '        "total": total,\n'
        '        "total_pages": total_pages,\n'
        '        "has_next": end < total,\n'
        "    }\n",
        encoding="utf-8",
    )
    (repo / "tests" / "test_pages.py").write_text(
        "import sys\n"
        "import unittest\n"
        "from pathlib import Path\n\n"
        'sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))\n'
        "from pages import paginate\n\n\n"
        "class PagesTest(unittest.TestCase):\n"
        "    def test_rejects_invalid_arguments(self):\n"
        "        with self.assertRaises(ValueError):\n"
        "            paginate([1, 2, 3], page=0, page_size=2)\n"
        "        with self.assertRaises(ValueError):\n"
        "            paginate([1, 2, 3], page=1, page_size=0)\n\n"
        "    def test_returns_page_size_slice(self):\n"
        "        res = paginate([1, 2, 3, 4, 5], page=1, page_size=2)\n"
        '        self.assertEqual(len(res["items"]), 2)\n'
        '        self.assertEqual(res["total"], 5)\n\n'
        "    def test_one_indexed_page_contents(self):\n"
        "        items = [1, 2, 3, 4, 5]\n"
        "        p1 = paginate(items, page=1, page_size=2)\n"
        "        p2 = paginate(items, page=2, page_size=2)\n"
        "        p3 = paginate(items, page=3, page_size=2)\n"
        '        self.assertEqual(p1["items"], [1, 2])\n'
        '        self.assertTrue(p1["has_next"])\n'
        '        self.assertEqual(p2["items"], [3, 4])\n'
        '        self.assertTrue(p2["has_next"])\n'
        '        self.assertEqual(p3["items"], [5])\n'
        '        self.assertFalse(p3["has_next"])\n\n'
        "    def test_empty_input(self):\n"
        "        res = paginate([], page=1, page_size=5)\n"
        '        self.assertEqual(res["items"], [])\n'
        '        self.assertEqual(res["total"], 0)\n'
        '        self.assertEqual(res["total_pages"], 0)\n'
        '        self.assertFalse(res["has_next"])\n',
        encoding="utf-8",
    )
    resolved = {
        "pr_number": 17,
        "threads": [
            {
                "id": "thread-1",
                "status": "resolved",
                "reply": (
                    "Fixed start offset in src/pages.py from `page * page_size` to `(page - 1) * page_size` "
                    "and added `test_one_indexed_page_contents` asserting exact items and `has_next` across pages 1-3."
                ),
                "evidence": "python3 -B -m unittest discover -s tests passed (4 tests).",
            },
            {
                "id": "thread-2",
                "status": "resolved",
                "reply": (
                    "Added `test_empty_input` in tests/test_pages.py verifying `paginate([], page=1, page_size=5)` "
                    "returns items=[], total=0, total_pages=0, and has_next=False."
                ),
                "evidence": "python3 -B -m unittest discover -s tests passed (4 tests).",
            },
        ],
    }
    (ws / "program" / "resolved_threads.json").write_text(
        json.dumps(resolved, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "final_text": (
            "Resolved both blocking review threads: fixed the 1-indexed start offset in `src/pages.py`, "
            "added exact-page and empty-input regression tests in `tests/test_pages.py`, verified all tests pass, "
            "and saved per-thread resolution proof in `program/resolved_threads.json`."
        ),
    }
