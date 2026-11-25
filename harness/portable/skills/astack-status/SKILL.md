---
name: astack-status
description: "Show an astack program's active workers, reviewers, and researchers, their timers, latest commits, lane states, and open questions. Use for /astack-status or when asked how a program is progressing."
disable-model-invocation: true
---

# Status

Run `astack-status` (from `PATH` once `/astack-setup` links it into `~/.local/bin`, or from `../../bin/astack-status`). It reads the newest lane log under `~/.cache/astack/`; pass a program folder to read another.

Show its output verbatim, then add one plain line flagging anything needing attention (any worker, reviewer, or researcher past its limit, or an open question).

Use `astack-status --line` for a one-line status-bar summary.
