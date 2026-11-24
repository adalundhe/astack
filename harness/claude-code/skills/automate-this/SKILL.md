---
name: automate-this
description: "Replace repeated tool calls, manual commands and watching by hand with a script, a skill, a tool or a watcher, and keep bulk output out of the context, so agent time and attention go to reasoning. Use when you catch yourself running the same commands again, when a search or output would flood the context, re-checking CI or another agent, or tending an environment by hand."
---

# Automate this

Replace repeated manual work, such as rerunning commands or watching CI, with scripts, tools and watchers.

- **Watch with a watcher.** For CI, a test run, a pull request or another agent's progress, start one command in the background that waits for the event (a finished run, an exit code, a new comment, a passing test) and returns. Never re-check by hand (**event-driven**).
- **Script what repeats.** A sequence you've run twice becomes a script, its inputs as arguments, with a clear exit code.
- **Keep the environment up with automation:** setup, cleanup and health checks as scripts, not remembered steps.
- **Make it reusable:** put it where the next agent will find it, in the project's scripts folder, or as a skill when it's a method.
- **Keep the context for reasoning.** Bulk work (a search across many files, a long log, a large output) goes to a subagent or a script that returns only the conclusion, or what failed. Read the part of a file you need, and never paste raw output where its conclusion will do.
- **Keep it honest:** a script exits non-zero when what it checks fails, and says why in one line.

<!-- Adapts pstack's guard-the-context-window principle (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
