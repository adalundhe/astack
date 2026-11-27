---
description: "Atomic outcome eval for cross-repo: fixes a broken multi-repo release plan in program/release-plan.json by pinning exact git commit SHAs from ./repo-lib and ./repo-app (removing floating main/latest refs) and correcting topological deploy order (repo-lib before repo-app)."
expected_outcome: "Reads cross-repo/SKILL.md, inspects ./repo-lib and ./repo-app without modifying either repo, updates program/release-plan.json so repo-lib deploys before repo-app with explicit depends_on and exact pinned 40-char git SHAs instead of floating main/latest refs."
timeout_seconds: 360
---

`/astack:go` Audit and fix `program/release-plan.json` for our two local repositories `./repo-lib` and `./repo-app`. Check which repository depends on the other, replace any floating branch or tag references with exact immutable commit SHAs from git, fix the deploy order and dependency links so upstream releases complete before downstream consumers deploy, and ensure rollback notes run in reverse order. Do not edit `./repo-lib` or `./repo-app`.
