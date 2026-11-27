---
description: "A/B test at least two distinct prefix-matching implementations on program/queries.json and graft only the verified faster winner into repo/src/matcher.py."
expected_outcome: "Reads ab-test/SKILL.md, benchmarks baseline plus >= 2 distinct variants (such as bisect vs prefix trie) with parity checks in program/ab_results.json, lands only the verified faster winner in repo/src/matcher.py, passes unittest and mutation checks, keeps gates intact, and leaves no losing variant files in ./repo."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Read `program/ab_brief.md` and run a controlled A/B comparison of at least two distinct prefix-matching implementations against the baseline in `./repo/src/matcher.py` using `program/queries.json`.

Record the measured timings, parity checks, and winning pick in `program/ab_results.json`, graft only the verified faster winner into `./repo/src/matcher.py`, ensure no losing variant files remain inside `./repo`, and verify the test suite passes.
