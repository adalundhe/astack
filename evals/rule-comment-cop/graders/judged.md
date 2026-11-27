---
type: llm
---

Evaluate the cleanup of `./repo/src/rate_limiter.py` against `comment-cop`.

PASS if all of these hold:
- Strips narrating comments, ASCII section dividers, git-history notes (`OPS-991`), and commented-out code.
- Preserves the SPDX/Copyright license header and the RFC 6585 / Envoy 1.29 `Retry-After` constraint comment.
- Keeps the public API and unit tests passing without adding new narrating comments.

FAIL otherwise.
