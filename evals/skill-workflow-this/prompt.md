---
description: "Turn a reviewed recurring audit task graph into a crash-resumable automated workflow and usage documentation saved outside ./repo under ASTACK_HOME."
expected_outcome: "Reads workflow-this/SKILL.md, saves a runnable stdlib Python crash-resumable workflow with explicit task states under program/astack_home/nightly-audit/automations/<name>/ and usage documentation under program/astack_home/nightly-audit/docs/, leaves ./repo clean, and reports verification results and rerun/resume commands."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Project `nightly-audit` (`./repo`) has a reviewed recurring audit task graph in `./program/workflow_request.md` that needs to run unattended on a schedule.

With `ASTACK_HOME` set to `./program/astack_home`, turn the reviewed graph into a crash-resumable automated workflow stored under `ASTACK_HOME` for `nightly-audit`, write its usage documentation (including the task state machine and exact rerun/resume commands) under `ASTACK_HOME` docs for `nightly-audit`, verify it against `./repo`, and leave `./repo` unmodified.
