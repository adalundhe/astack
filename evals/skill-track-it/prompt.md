---
description: "Atomic outcome eval for track-it: syncs program/issues.json against program/LANES.md and ./repo evidence, closing #101 with its verified commit SHA, keeping #102 open and marked blocked with a blocker note, keeping #103 open in progress, and leaving ./repo clean."
expected_outcome: "Reads track-it/SKILL.md, verifies git commit SHA and test results in ./repo without modifying ./repo, marks #101 closed with the exact commit SHA and proof, keeps #102 open as blocked with the failing test / #98 blocker note, and leaves #103 open."
timeout_seconds: 360
---

`/astack:go` Sync our issue tracker mirror in `program/issues.json` against the lane statuses in `program/LANES.md` and actual evidence in `./repo` (git history and tests). Close completed issues with exact commit proof, mark blocked issues open with an accurate blocker note without closing them, leave in-progress issues open, and do not modify `./repo`.
