---
name: astack-setup
description: "Configure worker runtime limit, wind-down buffer, and lead check-in interval in ~/.config/astack/settings.json. Use for $astack-setup or changing program timing settings."
---

# Setup

Ask the person for three timing settings and save them. The lead reads them when starting a program.

1. **Read** `~/.config/astack/settings.json` (or `$XDG_CONFIG_HOME/astack/settings.json` if set). If missing, start from the defaults: 60 minutes per worker, 5-minute wind-down buffer, and 5-minute lead check-in interval.
2. **Ask** in your reply (or with `request_user_input` in Plan mode), showing the current value first:
   - How many minutes may a worker run?
   - How many minutes before that limit does it wind down?
   - Every how many minutes does the lead check in?

   These are the person's choices; never pick them yourself.
3. **Validate** that all three are positive integers and that wind-down is strictly shorter than the worker limit. If not, ask again.
4. **Write** the full file, creating parent directories if needed:

   ```json
   {"worker_minutes": 60, "wind_down_minutes": 5, "check_in_minutes": 5}
   ```

5. **Install the agents.** Codex plugins can't ship agents, so copy `agents/astack-worker.toml` and `agents/astack-reviewer.toml` from this package (two folders up from this file) to `$CODEX_HOME/agents/` (`~/.codex/agents/` by default), creating the folder and replacing any older copies. If `/hooks` lists astack's hook as untrusted, ask the person to trust it there.
6. **Confirm** in one line: the saved values, file path, and that they take effect on the next program (program-specific instructions still override them).
