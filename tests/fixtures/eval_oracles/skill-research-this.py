"""Separated offline oracle for `skill-research-this`."""
from __future__ import annotations

from pathlib import Path


def apply(ws: Path) -> dict[str, object]:
    """Write canonical A-F graded research resolving v2.1 vs 2021 blog contradiction."""
    research_dir = ws / "program" / "astack_home" / "proto-check" / "research" / "handshake-protocol"
    research_dir.mkdir(parents=True, exist_ok=True)
    report = (
        "# Handshake Protocol Research — proto-check\n\n"
        "## Question\n"
        "Should `proto-check` send `X-Proto-Version: 2.1` with SHA-256 HMAC or `X-Proto-Version: 1.0` with MD5?\n\n"
        "## Canonical Grade Scale\n"
        "- A: 85+, B: 70–84, C: 50–69, D: 30–49, F: <30.\n\n"
        "## Findings\n\n"
        "### Finding 1: Protocol v2.1 and live client code require `X-Proto-Version: 2.1` and SHA-256 HMAC\n"
        "- **Grade A (99)** — 2 independent primary origins (official spec, live code); 2/2 quotes verified.\n"
        "- **Support calculation:** `1 - (1 - 0.90) * (1 - 0.90) = 0.99`; score = `99`.\n"
        "- **Source [1] (Official Specification, weight 0.90, verified):** `program/sources/official-spec-v2.1.md:6` — "
        "\"All v2.1 handshake requests MUST send header X-Proto-Version: 2.1 and use SHA-256 HMAC signatures; legacy MD5 signatures and X-Proto-Version: 1.0 were removed in v2.0.\"\n"
        "- **Source [2] (Internal Code, weight 0.90, verified):** `repo/src/client.py:7-16` — "
        "`PROTO_VERSION = \"2.1\"` and `hmac.new(signing_key, payload, hashlib.sha256).hexdigest()`.\n"
        "- **Counterclaim handled:** `program/sources/old-blog-2021.md:5` (2021 personal blog, outdated) only describes v1.0 behavior that was explicitly removed in v2.0.\n\n"
        "### Finding 2: Legacy claim that clients should send `X-Proto-Version: 1.0` with MD5\n"
        "- **Grade F (8)** — 1 stale blog source (0.50 x 0.75 = 0.375) contradicted by 2 verified primary sources (against = 0.99); `round(0.375 * (1 - 0.8 * 0.99) * 100) = 8`.\n"
        "- **Source [3] (Personal Blog, weight 0.50 x 0.75 out-of-date = 0.375, verified):** `program/sources/old-blog-2021.md:5` — "
        "\"Clients should send X-Proto-Version: 1.0 and sign payloads with MD5 for maximum compatibility with older servers.\"\n\n"
        "## Numbered Sources\n"
        "1. `program/sources/official-spec-v2.1.md` (Section 4.2, Protocol Standards Committee, 2026-06-01) — official specification.\n"
        "2. `repo/src/client.py` (lines 7–16) — live repository implementation.\n"
        "3. `program/sources/old-blog-2021.md` (Alex Example, 2021-03-14) — outdated personal blog (superseded by v2.0+).\n"
    )
    out_file = research_dir / "findings.md"
    out_file.write_text(report, encoding="utf-8")

    return {
        "final_text": (
            "Resolved the handshake contradiction and saved graded findings to "
            "`program/astack_home/proto-check/research/handshake-protocol/findings.md` (`./repo` untouched):\n"
            "- **Grade A (99):** Rely on `X-Proto-Version: 2.1` and SHA-256 HMAC, verified in both "
            "`program/sources/official-spec-v2.1.md` (Section 4.2) and `repo/src/client.py:7-16`.\n"
            "- **Grade F (8):** `program/sources/old-blog-2021.md` (`1.0` + MD5) is an outdated 2021 blog post superseded when v1.0/MD5 were removed in v2.0."
        ),
    }
