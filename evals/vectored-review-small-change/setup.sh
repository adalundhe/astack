#!/bin/bash
set -euo pipefail
mkdir -p program repo
if [ -n "${ASTACK_EVAL_SETTINGS_JSON:-}" ]; then
  printf '%s\n' "$ASTACK_EVAL_SETTINGS_JSON" > program/settings.json
else
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
fi

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false
cat > repo/fmt.py <<'EOF'
def normalize_spaces(text: str) -> str:
    """Trim leading and trailing ASCII spaces."""
    return text.strip(" ")
EOF
cat > repo/test_fmt.py <<'EOF'
import unittest
from fmt import normalize_spaces


class NormalizeSpacesTest(unittest.TestCase):
    def test_trims_outer_spaces(self):
        self.assertEqual(normalize_spaces("  hello world  "), "hello world")

    def test_empty(self):
        self.assertEqual(normalize_spaces(""), "")


if __name__ == "__main__":
    unittest.main()
EOF
git -C repo add fmt.py test_fmt.py
git -C repo commit -q -m "initial ASCII space trimmer with unit tests"

git -C repo checkout -q -b lane/collapse-spaces
cat > repo/fmt.py <<'EOF'
import re


def normalize_spaces(text: str) -> str:
    """Trim outer ASCII spaces and collapse runs of 2+ ASCII spaces to one."""
    return re.sub(r" {2,}", " ", text.strip(" "))
EOF
cat > repo/test_fmt.py <<'EOF'
import unittest
from fmt import normalize_spaces


class NormalizeSpacesTest(unittest.TestCase):
    def test_trims_outer_spaces(self):
        self.assertEqual(normalize_spaces("  hello world  "), "hello world")
        self.assertEqual(normalize_spaces("\thello\n"), "\thello\n")

    def test_empty(self):
        self.assertEqual(normalize_spaces(""), "")
        self.assertEqual(normalize_spaces("    "), "")

    def test_collapses_repeated_ascii_spaces_only(self):
        self.assertEqual(normalize_spaces("a  b"), "a b")
        self.assertEqual(normalize_spaces("a  b   c"), "a b c")
        self.assertEqual(normalize_spaces("  hello   world  "), "hello world")
        self.assertEqual(normalize_spaces("a\n\nb"), "a\n\nb")
        self.assertEqual(normalize_spaces("a\t\tb"), "a\t\tb")
        self.assertEqual(normalize_spaces("a\u00a0\u00a0b"), "a\u00a0\u00a0b")
        self.assertEqual(normalize_spaces("don't   stop"), "don't stop")


if __name__ == "__main__":
    unittest.main()
EOF
git -C repo add fmt.py test_fmt.py
git -C repo commit -q -m "collapse repeated ASCII spaces in normalize_spaces with unit tests"
git -C repo diff main..lane/collapse-spaces > program/change.diff
mkdir -p program/base
git -C repo show main:fmt.py > program/base/fmt.py
git -C repo show main:test_fmt.py > program/base/test_fmt.py
