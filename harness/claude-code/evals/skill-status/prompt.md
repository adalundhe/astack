---
description: "Report exact lane counts and states from program/LANES.md and ./repo, flagging the overdue lane past wind-down without mutating the repository."
expected_outcome: "Reads status/SKILL.md, leaves ./repo clean and read-only, and reports exact lane counts and states (1 merged/closed lane lane/core, 2 active lanes: healthy lane/api and overdue lane/index past wind-down/limit) in final response or program/STATUS.md."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Check the status of the program tracked in `program/LANES.md` against `./repo`.

Report the exact lane counts and states (which lanes are merged/closed, which are active and on track, and which are overdue past wind-down/limit) without modifying `./repo`. You may reply directly or also save the report to `program/STATUS.md`.
