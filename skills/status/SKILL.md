---
name: status
description: "Show an astack program's running workers, their clocks and last commits, its lanes, and the questions waiting on the person. Use for /astack:status, or when the person asks how the program or its workers are doing."
---

# Status

Run `astack-status`. It reads the newest lane log under `~/.cache/astack/`; pass a program folder to read another.

Show its output as it is. Then add one plain line for anything that needs the person: a worker past its limit, or a question waiting.

`astack-status --line` prints a one-line summary, for a status bar.
