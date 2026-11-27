---
description: "Create a saved recurring TaskEx health-check watcher automation for project ops-portal under ASTACK_HOME while keeping the target git repository clean."
expected_outcome: "Reads taskex/SKILL.md, saves a syntactically valid TaskEx automation script and automation.json manifest under program/astack_home/ops-portal/automations/<name>/ classified as runner taskex, keeps ./repo clean, leaks zero secrets, and provides exact run and resume commands."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Project `ops-portal` (`./repo`) needs a saved recurring health-check watcher automation written with `taskex`. Read `./program/request.md` and `./repo/README.md` for the watcher requirements and target check script.

With `ASTACK_HOME` set to `./program/astack_home`, store the self-contained automation and its manifest outside the repository under `ASTACK_HOME` for project `ops-portal`. Leave `./repo` unmodified, keep all configuration secret-free, and end with the exact run and resume commands.
