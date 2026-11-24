---
name: astack-setup
description: "Configure worker timing, per-role model/provider/effort, and optional Python automation tools (taskex, orchestral, werkflow + werkflow-modules). Use for /astack-setup."
disable-model-invocation: true
---

# Setup

Configure timing, subagent model settings, and optional automation tools. Settings live in `~/.config/astack/settings.json` (or `$XDG_CONFIG_HOME/astack/settings.json`).

1. **Read current state.** Read `settings.json` (defaulting to `worker_minutes: 60`, `wind_down_minutes: 5`, `check_in_minutes: 5`, and session defaults for `roles`) and run `astack-tools doctor` to check whether `taskex`, `orchestral`, and `werkflow` are installed in the managed venv.
2. **Ask**, showing current values first, with Cursor's question tool:
   - Worker time limit, wind-down buffer, and lead check-in interval (minutes).
   - Model, provider, and effort for `worker` and `reviewer` (and optionally `lead` / `researcher`), leaving blank to inherit the session.
   - Whether to install or update the Python automation stack via `astack-tools install` (`skip`, `core`, `standard`, or `all`, plus any extra `werkflow` modules).

   Cursor options: any subagent model name available in this session (the model name sets provider and, where supported, effort). Never pick values on the person's behalf.
3. **Validate:** positive integers for timing (`wind_down_minutes < worker_minutes`) and valid platform options for any role overrides. Re-ask if invalid.
4. **Write `settings.json`** (creating parent directories if needed), omitting any role field left on session default:

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
6. **Install automation tools if chosen:** run `astack-tools install --profile <choice>` (adding `--modules ...` if requested) and verify with `astack-tools doctor`.
7. **Confirm** in one short summary: saved values, file path, automation venv status, and that changes apply from the next run (program instructions still override them).
