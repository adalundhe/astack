"""Separated offline oracle for `skill-talk-to-me`."""
from __future__ import annotations

import importlib.util
from pathlib import Path


def apply(ws: Path) -> dict[str, object]:
    """Compute real hashes from repo/src/merkle.py and write a plain guide with Mermaid diagram."""
    merkle_path = ws / "repo" / "src" / "merkle.py"
    spec = importlib.util.spec_from_file_location("eval_merkle_mod", merkle_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    items = [b"tx-a", b"tx-b", b"tx-c", b"tx-d"]
    levels = mod.build_levels(items)
    root = levels[-1][0]
    proof = mod.inclusion_proof(items, 1)
    verified = mod.verify_proof(b"tx-b", proof, root)

    h_a, h_b, h_c, h_d = [h[:8] for h in levels[0]]
    h_ab, h_cd = [h[:8] for h in levels[1]]
    h_root = root[:8]

    guide = (
        "# How Merkle-Tree Inclusion Proofs Work in `src/merkle.py`\n\n"
        "## Bottom Line\n"
        "A Merkle-tree inclusion proof lets you prove a single item belongs to a dataset using only `O(log N)` sibling hashes "
        "instead of downloading the entire list. In `src/merkle.py`, `inclusion_proof` builds that minimal sibling path and `verify_proof` checks it against one trusted root hash.\n\n"
        "## Key Domain Terms (Mapped to `src/merkle.py`)\n"
        "- **Leaf hash (`hash_leaf`):** SHA-256 digest of `0x00 || data` for one raw item.\n"
        "- **Internal node hash (`hash_node`):** SHA-256 digest of `0x01 || left || right`, pairing two child digests.\n"
        "- **Merkle levels & root (`build_levels`):** Repeated pairwise hashing until one top digest (`levels[-1][0]`) summarizes the whole batch.\n"
        "- **Audit path / inclusion proof (`inclusion_proof`):** Ordered list of `(side, sibling_hex)` pairs needed to climb from one leaf to the root.\n"
        "- **Proof verification (`verify_proof`):** Re-hashes the target item with each `(side, sibling)` pair and checks equality with `expected_root`.\n\n"
        "## Tree & Proof Flow\n"
        "```mermaid\n"
        "flowchart BT\n"
        f"  A[\"tx-a ({h_a})\"] --> AB[\"H(A,B) ({h_ab})\"]\n"
        f"  B[\"tx-b ({h_b})\"] --> AB\n"
        f"  C[\"tx-c ({h_c})\"] --> CD[\"H(C,D) ({h_cd})\"]\n"
        f"  D[\"tx-d ({h_d})\"] --> CD\n"
        f"  AB --> R[\"Root ({h_root})\"]\n"
        f"  CD --> R\n"
        "```\n\n"
        "## Worked Example (`items = [b'tx-a', b'tx-b', b'tx-c', b'tx-d']`, proving `b'tx-b'`)\n"
        f"1. **Input & leaf hash:** `hash_leaf(b'tx-b')` -> `{h_b}...`.\n"
        f"2. **Proof returned by `inclusion_proof(items, 1)`:** `[('left', '{h_a}...'), ('right', '{h_cd}...')]` (2 hashes instead of all 4 items).\n"
        f"3. **Step 1 in `verify_proof`:** Combine `left` sibling `{h_a}...` with `{h_b}...` via `hash_node(left, current)` -> `{h_ab}...`.\n"
        f"4. **Step 2 in `verify_proof`:** Combine `{h_ab}...` with `right` sibling `{h_cd}...` via `hash_node(current, right)` -> `{h_root}...`.\n"
        f"5. **Output:** Recomputed root equals `expected_root` (`{h_root}...`) -> `{verified}`.\n\n"
        "## Analogy (and Where It Breaks Down)\n"
        "- **Analogy:** Like a tournament bracket where each match's score sheet seals both players' names — to prove a player reached the final, you only need the opponents they faced in each round, not every other match.\n"
        "- **Where it breaks down:** Hash order (`left` vs `right`) is strict and irreversible; swapping two siblings produces a completely different root, unlike an unordered match pairing.\n\n"
        "## Hidden Pitfalls\n"
        "- **Second-preimage attacks:** Without the `0x00` (leaf) vs `0x01` (node) byte prefixes in `hash_leaf`/`hash_node`, an attacker could pass an internal node's 64-byte concatenation as a fake leaf.\n"
        "- **Odd-leaf duplication:** When a level has an odd number of nodes, `build_levels` duplicates the last hash (`right = cur[idx + 1] if idx + 1 < len(cur) else left`). Systems that fail to record tree size can accept forged duplicate trailing leaves (CVE-2012-2459 pattern).\n"
    )

    (ws / "program" / "GUIDE.md").write_text(guide, encoding="utf-8")
    return {"final_text": guide}
