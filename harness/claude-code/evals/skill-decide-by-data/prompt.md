---
description: "Settle an engineering debate between algo_a and algo_b by measuring both on program/dataset.json instead of debating intuition."
expected_outcome: "Reads decide-by-data/SKILL.md, leaves ./repo clean, measures repo/src/algo_a.py and repo/src/algo_b.py on program/dataset.json with output parity verification, and records empirical winner 'algo_b' with timings and parity proof in program/decision.json."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Read `program/debate.md` and settle the disagreement between `./repo/src/algo_a.py` and `./repo/src/algo_b.py` using real measurements on `program/dataset.json`.

Do not modify `./repo`. Verify output parity, record the empirical winner, measured timings, and parity proof in `program/decision.json`, and summarize the `decided:` call with the numbers.
