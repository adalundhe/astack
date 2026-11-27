#!/bin/bash
set -euo pipefail
mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval User"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/core.py <<'EOF'
def health() -> str:
    return "ok"
EOF

git -C repo add .
git -C repo commit -q -m "feat(core): land core health module (lane/core)"
MAIN_SHA=$(git -C repo rev-parse HEAD)
echo "${MAIN_SHA}" > program/base_sha.txt

# Create real branch lane/api with a recent commit
git -C repo checkout -q -b lane/api
cat > repo/src/api.py <<'EOF'
def handle_request(path: str) -> int:
    return 200 if path == "/health" else 404
EOF
git -C repo add src/api.py
git -C repo commit -q -m "wip(api): add health endpoint handler"

# Create real branch lane/index with a commit
git -C repo checkout -q main
git -C repo checkout -q -b lane/index
cat > repo/src/index.py <<'EOF'
def build_index(items: list[str]) -> dict[str, int]:
    return {item: idx for idx, item in enumerate(items)}
EOF
git -C repo add src/index.py
git -C repo commit -q -m "wip(index): scaffold inverted index builder"

# Return to main clean
git -C repo checkout -q main

python3 -B - <<'PY'
from datetime import datetime, timedelta, timezone
from pathlib import Path

now = datetime.now(timezone.utc)
fmt = lambda delta_min: (now + timedelta(minutes=delta_min)).strftime("%Y-%m-%dT%H:%MZ")
main_sha = Path("program/base_sha.txt").read_text(encoding="utf-8").strip()

lanes = f"""<!-- astack lane log -->
# Platform Program

Repository: ./repo

## Log
{fmt(-150)} started w1 on lane/core (agent worker-1) | branch main | wind-down {fmt(-100)} | ends {fmt(-90)}
{fmt(-110)} ended w1: merged core health module at {main_sha[:7]}
{fmt(-105)} closed lane/core: merged at {main_sha}
{fmt(-90)} started w3 on lane/index (agent worker-3) | branch lane/index | wind-down {fmt(-40)} | ends {fmt(-30)}
{fmt(-15)} started w2 on lane/api (agent worker-2) | branch lane/api | wind-down {fmt(35)} | ends {fmt(45)}
"""
Path("program/LANES.md").write_text(lanes, encoding="utf-8")
PY
