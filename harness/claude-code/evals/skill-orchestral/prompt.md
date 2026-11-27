---
description: "Create a saved multi-wave Orchestral DAG workflow for project data-sync under ASTACK_HOME where step code owns state-passing and branching while keeping ./repo clean."
expected_outcome: "Reads orchestral/SKILL.md, saves a syntactically valid Orchestral multi-wave DAG script and automation.json manifest under program/astack_home/data-sync/automations/<name>/ classified as runner orchestral, keeps ./repo clean, leaks zero secrets, and provides exact run and resume commands."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Project `data-sync` (`./repo`) needs a concise multi-wave DAG workflow script built with `orchestral` where step code owns state-passing and conditional branching. Read `./program/request.md` and `./repo/README.md` for the DAG stages and failure/checkpoint requirements.

With `ASTACK_HOME` set to `./program/astack_home`, store the self-contained automation and its manifest outside the repository under `ASTACK_HOME` for project `data-sync`. Leave `./repo` unmodified, keep all configuration secret-free, and provide exact run and resume commands.
