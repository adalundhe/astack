---
name: astack-setup
description: "Configure worker timing and per-role model, provider, and effort in ~/.config/astack/settings.json. Use for /astack-setup."
disable-model-invocation: true
---

# Setup

Configure timing and subagent model settings in `~/.config/astack/settings.json` (or `$XDG_CONFIG_HOME/astack/settings.json`).

1. **Read current settings.** Default to `worker_minutes: 60`, `wind_down_minutes: 5`, `check_in_minutes: 5`, and session defaults for `roles` (`worker`, `reviewer`, plus optional `lead` / `researcher`).
2. **Ask**, showing current values first, with Cursor's question tool:
   - Worker time limit, wind-down buffer, and lead check-in interval (minutes).
   - Model, provider, and effort for `worker` and `reviewer` (and optionally `lead` / `researcher`), leaving blank to inherit the session.

   Cursor options: any subagent model name available in this session (the model name sets provider and, where supported, effort). Never pick values on the person's behalf.
3. **Validate:** positive integers for timing (`wind_down_minutes < worker_minutes`) and valid platform options for any role overrides. Re-ask if invalid.
4. **Write the file** (creating parent directories if needed), omitting any role field left on session default:

   ```json
   {
     "worker_minutes": 60,
     "wind_down_minutes": 5,
     "check_in_minutes": 5,
     "roles": {
       "worker": {"model": "<model>", "provider": "<provider>", "effort": "<effort>"},
       "reviewer": {}
     }
   }
   ```

5. **Install what this tool needs.** Nothing in Cursor: the plugin ships the agents and the hook.
6. **Confirm** in one line: saved values, file path, and that they apply from the next run (program instructions still override them).
