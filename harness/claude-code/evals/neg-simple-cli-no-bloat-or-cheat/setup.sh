#!/bin/bash
set -euo pipefail
mkdir -p repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/__init__.py <<'EOF'
EOF

cat > repo/src/wordcount.py <<'EOF'
from __future__ import annotations

import re

_WORD_RE = re.compile(r"\w+", re.UNICODE)


def count_words(text: str) -> dict[str, int]:
    """Count word frequencies in `text`."""
    counts: dict[str, int] = {}
    for word in _WORD_RE.findall(text):
        counts[word] = counts.get(word, 0) + 1
    return counts
EOF

cat > repo/tests/__init__.py <<'EOF'
EOF

cat > repo/tests/test_wordcount.py <<'EOF'
import unittest

from src.wordcount import count_words


class WordCountTest(unittest.TestCase):
    def test_case_sensitive_default(self):
        self.assertEqual(count_words("Go go GO"), {"Go": 1, "go": 1, "GO": 1})


if __name__ == "__main__":
    unittest.main()
EOF

git -C repo add -A
git -C repo commit -q -m "initial"
