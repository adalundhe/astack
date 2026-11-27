---
description: "Build a throwaway runnable CLI prototype outside ./repo comparing immediate-undo vs two-step-confirm UX state transitions via --scenario flags while leaving ./repo untouched."
expected_outcome: "Reads play-with-me/SKILL.md, builds a runnable throwaway CLI prototype at program/prototype/demo.py (outside ./repo) supporting --scenario undo and --scenario confirm non-interactively with distinct concrete outputs and explicit mocking notes, runs it to confirm both flows work, and leaves ./repo clean."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Read `./program/design_question.md` to see the UX trade-off we are deciding for report deletion in `./repo`.

Before touching production code in `./repo`, build a small throwaway runnable CLI prototype at `./program/prototype/demo.py` (strictly outside `./repo`) so we can try both state-transition flows (`--scenario undo` and `--scenario confirm`) non-interactively in one command. Run both scenarios yourself to verify they work with no side effects on `./repo`, state explicitly what is stubbed/mocked, and share the exact commands and what to try.
