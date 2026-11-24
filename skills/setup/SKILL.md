---
name: setup
description: "Configure worker runtime limit, wind-down buffer, and lead check-in interval in ~/.config/astack/settings.json. Use for /astack:setup or changing program timing settings."
---

# Setup

Ask the person for three timing settings and save them. The lead reads them when starting a program.

1. **Read** `~/.config/astack/settings.json` (or `$XDG_CONFIG_HOME/astack/settings.json` if set). If missing, start from the defaults: 60 minutes per worker, 5-minute wind-down buffer, and 5-minute lead check-in interval.
2. **Ask**, showing the current value first, using `AskUserQuestion`:
   - How many minutes may a worker run?
   - How many minutes before that limit does it wind down?
   - Every how many minutes does the lead check in?

   These are the person's choices; never pick them yourself.
3. **Validate** that all three are positive integers and that wind-down is strictly shorter than the worker limit. If not, ask again.
4. **Write** the full file, creating parent directories if needed:

   ```json
   {"worker_minutes": 60, "wind_down_minutes": 5, "check_in_minutes": 5}
   ```

5. **Install what this tool needs.** Nothing in Claude Code: the plugin ships the agents and the hook.
6. **Confirm** in one line: the saved values, file path, and that they take effect on the next program (program-specific instructions still override them).
