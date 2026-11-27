---
description: "Distill a sprawling stakeholder request into concise checkable alignment lines (goal, problem, in-scope deliverable, explicit out-of-scope boundaries naming PDF export and DB migration, assumptions, and an executable Done-when check) while leaving ./repo untouched."
expected_outcome: "Reads run-it-back/SKILL.md, leaves ./repo clean, and writes a clear restatement in final_text or program/ALIGNMENT.md covering the CSV export of active invoices, explicit exclusions of PDF export and DB migration, problem, assumptions, and an executable Done-when check."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Read `./program/ask.md` and `./repo/src/invoices.py`, then restate what is being asked in short, checkable lines before any implementation begins.

Leave `./repo` untouched and record your alignment restatement (goal, problem, in-scope deliverable, explicit out-of-scope boundaries, assumptions, and an executable Done-when check) in your final response (or `./program/ALIGNMENT.md`).
