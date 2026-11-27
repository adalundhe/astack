#!/usr/bin/env bash
set -euo pipefail

mkdir -p program repo/src repo/tests

git -C repo init -q -b main
git -C repo config user.name "Eval"
git -C repo config user.email "eval@example.invalid"
git -C repo config commit.gpgsign false

cat > repo/src/merkle.py <<'EOF'
"""Domain-separated SHA-256 Merkle tree and inclusion-proof verifier."""
from __future__ import annotations

import hashlib


def hash_leaf(data: bytes) -> str:
    """Hash a leaf with a 0x00 domain prefix to block second-preimage attacks."""
    return hashlib.sha256(b"\x00" + data).hexdigest()


def hash_node(left_hex: str, right_hex: str) -> str:
    """Hash two child digests with a 0x01 domain prefix."""
    payload = b"\x01" + bytes.fromhex(left_hex) + bytes.fromhex(right_hex)
    return hashlib.sha256(payload).hexdigest()


def build_levels(items: list[bytes]) -> list[list[str]]:
    """Return Merkle levels from leaves (level 0) up to the single root (last level)."""
    if not items:
        raise ValueError("items must not be empty")
    levels: list[list[str]] = [[hash_leaf(item) for item in items]]
    while len(levels[-1]) > 1:
        cur = levels[-1]
        nxt: list[str] = []
        for idx in range(0, len(cur), 2):
            left = cur[idx]
            right = cur[idx + 1] if idx + 1 < len(cur) else left
            nxt.append(hash_node(left, right))
        levels.append(nxt)
    return levels


def inclusion_proof(items: list[bytes], index: int) -> list[tuple[str, str]]:
    """Build an audit path of (side, sibling_hex) pairs proving items[index] is in the root."""
    if index < 0 or index >= len(items):
        raise IndexError("leaf index out of range")
    levels = build_levels(items)
    proof: list[tuple[str, str]] = []
    pos = index
    for level in levels[:-1]:
        if pos % 2 == 0:
            sibling = level[pos + 1] if pos + 1 < len(level) else level[pos]
            proof.append(("right", sibling))
        else:
            proof.append(("left", level[pos - 1]))
        pos //= 2
    return proof


def verify_proof(item: bytes, proof: list[tuple[str, str]], expected_root: str) -> bool:
    """Recompute the Merkle root from one item plus its sibling proof path."""
    digest = hash_leaf(item)
    for side, sibling in proof:
        if side == "left":
            digest = hash_node(sibling, digest)
        elif side == "right":
            digest = hash_node(digest, sibling)
        else:
            raise ValueError(f"invalid proof side: {side!r}")
    return digest == expected_root
EOF

cat > repo/tests/test_merkle.py <<'EOF'
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from merkle import build_levels, inclusion_proof, verify_proof


class MerkleTest(unittest.TestCase):
    def test_four_leaf_inclusion_proof(self):
        items = [b"tx-a", b"tx-b", b"tx-c", b"tx-d"]
        root = build_levels(items)[-1][0]
        proof = inclusion_proof(items, 1)
        self.assertTrue(verify_proof(b"tx-b", proof, root))
        self.assertFalse(verify_proof(b"tx-tampered", proof, root))
EOF

git -C repo add .
git -C repo commit -q -m "add SHA-256 Merkle inclusion proof module and test"
