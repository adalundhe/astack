#!/bin/bash
set -euo pipefail
mkdir -p program repo/src

git -C repo init -q -b main
git -C repo config user.name eval
git -C repo config user.email eval@example.invalid
git -C repo config commit.gpgsign false

cat > repo/src/core.py <<'EOF'
def compute(x: int) -> int:
    return x + 1
EOF
cat > repo/README.md <<'EOF'
# Sample
EOF
git -C repo add .
git -C repo commit -q -m "initial"

cat > repo/src/core.py <<'EOF'
def compute(x: int) -> int:
    return x + 999
EOF
git -C repo add .
git -C repo commit -q -m "break compute"
BUG_SHA=$(git -C repo rev-parse HEAD)
git -C repo revert --no-edit "$BUG_SHA" >/dev/null

for i in 1 2 3 4; do
  printf "\nNote %s\n" "$i" >> repo/README.md
  git -C repo add .
  git -C repo commit -q -m "docs update $i"
done

cat > repo/src/core.py <<'EOF'
def compute(x: int) -> int:
    return x * 2
EOF
printf "\nUpdated docs\n" >> repo/README.md
git -C repo add .
git -C repo commit -q -m "candidate change"
