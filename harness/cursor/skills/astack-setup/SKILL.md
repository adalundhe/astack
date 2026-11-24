---
name: astack-setup
description: "Configure worker runtime limit, wind-down buffer, lead check-in interval, and the model, provider, and reasoning effort for workers and reviewers in ~/.config/astack/settings.json. Use for /astack-setup or changing these settings."
---

# Setup

Ask the person for three timing settings and the models workers and reviewers run on, and save them. The lead reads them when starting a program.

1. **Read** `~/.config/astack/settings.json` (or `$XDG_CONFIG_HOME/astack/settings.json` if set). If missing, start from the defaults: 60 minutes per worker, 5-minute wind-down buffer, and 5-minute lead check-in interval; workers and reviewers run on the session's own model.
2. **Ask**, showing the current value first, with Cursor's question tool:
   - How many minutes may a worker run?
   - How many minutes before that limit does it wind down?
   - Every how many minutes does the lead check in?
   - Which model, provider, and reasoning effort should workers use? Reviewers? ("Same as this session" is always an option.)

   Model options in Cursor: any model name you can pass to a subagent in this session. The name sets the provider, and for some models the effort, so workers and reviewers can run on a different provider from the session.

   These are the person's choices; never pick them yourself.
3. **Validate** that the three timings are positive integers, that wind-down is strictly shorter than the worker limit, and that each model, provider, and effort is one on offer. If not, ask again.
4. **Write** the full file, creating parent directories if needed, and omit any role setting that's "same as this session":

   ```json
   {"worker_minutes": 60, "wind_down_minutes": 5, "check_in_minutes": 5,
    "roles": {"worker": {"model": "<model>", "provider": "<provider>", "effort": "<effort>"}, "reviewer": {}}}
   ```

5. **Install what this tool needs.** Nothing in Cursor: the plugin ships the agents and the hook.
6. **Confirm** in one line: the saved values, file path, and that they take effect on the next program (program-specific instructions still override them).

Other subagents that skills start run on the session's model.
