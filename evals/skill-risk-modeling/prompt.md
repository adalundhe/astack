---
description: "Atomic outcome eval for risk-modeling: scores review vectors for the latest branch change in ./repo using the git baseline via astack-review-ledger score without modifying ./repo, saving the scored envelope to program/RISK_SCORE.json."
expected_outcome: "Reads risk-modeling/SKILL.md, keeps ./repo clean, runs astack-review-ledger score on ./repo for base..HEAD across core and docs vectors, writes valid JSON to program/RISK_SCORE.json with numeric [0, 1) risks, shares, raw finder_checks (level_status unverified, no binary level_trusted cutoff), and summarizes vector shares and caveats plainly."
timeout_seconds: 480
---

`/astack:go` Score the review risk of the latest branch change (`main~1..HEAD`) in `./repo` without modifying `./repo`. Slice the change into two vectors (`core` covering `src/core.py` and `docs` covering `README.md`), run the baseline risk scorer, write the scored JSON envelope to `program/RISK_SCORE.json`, and summarize vector shares and provenance plainly.
