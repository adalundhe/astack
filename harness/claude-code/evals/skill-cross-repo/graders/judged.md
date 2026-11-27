---
type: llm
---

Evaluate the updated `program/release-plan.json` against `cross-repo`.

PASS if all of these hold:
- Leaves `./repo-lib` and `./repo-app` untouched.
- Fixes deploy order so upstream `repo-lib` releases before downstream `repo-app`, with `deploy-app` declaring `depends_on: ["release-lib"]` (and `release-lib` having no cycle or downstream dependency).
- Replaces floating `"main"` and `"latest"` refs with exact immutable 40-character git commit SHAs resolved from `./repo-lib` and `./repo-app`.
- Keeps verification commands and documents reverse-order rollback (roll back `repo-app` before rolling back `repo-lib`).

FAIL otherwise.
