---
type: llm
---

Evaluate the research report against `research-this/SKILL.md`.

PASS if all of these hold:
- Covers both internal code (`repo/src/client.py`) and external/local sources (`program/sources/official-spec-v2.1.md`, `program/sources/old-blog-2021.md`).
- Verifies exact quotes in place and resolves the contradiction in favor of v2.1 and SHA-256 HMAC, explicitly flagging `old-blog-2021.md` as an outdated counterclaim.
- Assigns A–F grades and numeric scores strictly matching canonical bands (`A` 85+, `B` 70–84, `C` 50–69, `D` 30–49, `F` <30; never `55–69` or `30–54`).
- Persists the research output under `program/astack_home/proto-check/research/` and leaves `./repo` clean.

FAIL otherwise.
