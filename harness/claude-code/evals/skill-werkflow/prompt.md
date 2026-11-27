---
description: "Create a composable Werkflow @step and WorkflowGroup migration automation using werkflow-modules under ASTACK_HOME while keeping ./repo clean."
expected_outcome: "Reads werkflow/SKILL.md, saves a syntactically valid Werkflow script using @step, @requires, WorkflowGroup, werkflow-modules, and close() cleanup plus automation.json and secret-free .werkflow.json.example under program/astack_home/jira-migrate/automations/<name>/, keeps ./repo clean, and provides the exact non-interactive run command."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Project `jira-migrate` (`./repo`) needs a composable `@step` + `WorkflowGroup` automation built with `werkflow` and `werkflow-modules`. Read `./program/request.md` and `./repo/README.md` for the migration stages and module requirements.

With `ASTACK_HOME` set to `./program/astack_home`, store the self-contained automation, manifest, and non-secret config template outside the repository under `ASTACK_HOME` for project `jira-migrate`. Leave `./repo` unmodified, keep all configuration secret-free, and provide the exact non-interactive run command.
