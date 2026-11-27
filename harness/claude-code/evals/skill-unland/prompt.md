---
description: "Atomic outcome eval for unland: inspects git history on ./repo where commit B introduced a test-breaking regression beneath commit C (good unrelated docs), safely creates a git revert of ONLY commit B while preserving commit C and history, and leaves tests green."
expected_outcome: "Reads unland/SKILL.md, inspects git log on ./repo, creates a clean git revert commit targeting ONLY commit B (preserving commit C in ancestry and docs/API.md intact), passes unittest without modifying tests, and leaves ./repo working tree clean."
timeout_seconds: 360
---

`/astack:go` Tests in `./repo` started failing on `main` after a recent feature commit landed, and an unrelated documentation commit has already landed on top of it. Verify how the regression landed in git history, safely revert only the offending change without rewriting shared history or dropping the later documentation commit, and confirm the test suite passes again.
