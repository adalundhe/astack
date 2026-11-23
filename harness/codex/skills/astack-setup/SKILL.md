---
name: astack-setup
description: "Set how long astack workers run, when they wind down, and how often the lead checks in. Use for $astack-setup, or when the person wants to change the worker time limit or the check-in interval."
---

# Setup

Ask the person for three settings and save them. The lead reads them when it starts a program.

1. **Read** `~/.config/astack/settings.json` (under `$XDG_CONFIG_HOME` when that is set). If it is missing, start from the defaults: workers run 60 minutes, wind down 5 minutes before the end, and the lead checks in every 5 minutes.
2. **Ask** in your reply (or with `request_user_input` in Plan mode), showing the current value first:
   - How many minutes may a worker run?
   - How many minutes before that limit does it wind down?
   - Every how many minutes does the lead check in?

   These are the person's choices; never pick them yourself.
3. **Check** that each is a whole number above zero, and that the wind-down is shorter than the limit. If not, ask again.
4. **Write** the whole file, creating its folder if needed:

   ```json
   {"worker_minutes": 60, "wind_down_minutes": 5, "check_in_minutes": 5}
   ```

5. **Install the worker agent.** Codex plugins can't ship agents, so copy `agents/astack-worker.toml` from this package (two folders up from this file) to `$CODEX_HOME/agents/` (`~/.codex/agents/` by default), creating the folder and replacing any older copy. If `/hooks` lists astack's hook as untrusted, ask the person to trust it there.
6. **Confirm** in one line: the values, the file, and that they apply from the next program. A program's own instructions still override them.
