#!/bin/bash
set -euo pipefail
mkdir -p program repo
cat > program/settings.json <<'EOF'
{
  "roles": {
    "worker": {"provider": "anthropic", "model": "haiku", "effort": "medium"}
  },
  "reviewer_pool": [
    {"provider": "anthropic", "model": "sonnet", "effort": "medium"},
    {"provider": "anthropic", "model": "haiku", "effort": "medium"}
  ]
}
EOF

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false
cat > repo/fmt.py <<'EOF'
def format_title(text: str) -> str:
    """Trim outer ASCII spaces and title-case the string."""
    return text.strip(" ").title()
EOF
cat > repo/test_fmt.py <<'EOF'
import unittest
from fmt import format_title


class FormatTitleTest(unittest.TestCase):
    def test_trims_outer_spaces(self):
        self.assertEqual(format_title("  hello world  "), "Hello World")

    def test_empty(self):
        self.assertEqual(format_title(""), "")


if __name__ == "__main__":
    unittest.main()
EOF
git -C repo add fmt.py test_fmt.py
git -C repo commit -q -m "initial title formatter with unit tests"

git -C repo checkout -q -b lane/collapse-spaces
cat > repo/fmt.py <<'EOF'
import re


def format_title(text: str) -> str:
    """Trim outer ASCII spaces, collapse repeated ASCII spaces, and title-case."""
    return re.sub(r" {2,}", " ", text.strip(" ")).title()
EOF
cat > repo/test_fmt.py <<'EOF'
import unittest
from fmt import format_title


class FormatTitleTest(unittest.TestCase):
    def test_trims_outer_spaces(self):
        self.assertEqual(format_title("  hello world  "), "Hello World")
        self.assertEqual(format_title("\thello\n"), "\tHello\n")

    def test_empty(self):
        self.assertEqual(format_title(""), "")
        self.assertEqual(format_title("    "), "")

    def test_collapses_repeated_ascii_spaces_only(self):
        self.assertEqual(format_title("a  b"), "A B")
        self.assertEqual(format_title("a  b   c"), "A B C")
        self.assertEqual(format_title("  hello   world  "), "Hello World")
        self.assertEqual(format_title("a\n\nb"), "A\n\nB")
        self.assertEqual(format_title("a\t\tb"), "A\t\tB")
        self.assertEqual(format_title("a\u00a0\u00a0b"), "A\u00a0\u00a0B")


if __name__ == "__main__":
    unittest.main()
EOF
git -C repo add fmt.py test_fmt.py
git -C repo commit -q -m "collapse repeated ASCII spaces in format_title with unit tests"
git -C repo diff main..lane/collapse-spaces > program/change.diff
mkdir -p program/base
git -C repo show main:fmt.py > program/base/fmt.py
git -C repo show main:test_fmt.py > program/base/test_fmt.py
