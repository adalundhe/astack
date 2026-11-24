---
name: astack-setup
description: "Configure worker timing, per-role model/provider/effort, and optional Python automation tools (taskex, orchestral, werkflow + werkflow-modules). Use for $astack-setup."
---

# Setup

Configure timing, subagent model settings, and optional automation tools. Settings live in `~/.config/astack/settings.json` (or `$XDG_CONFIG_HOME/astack/settings.json`).

1. **Read current state.** Read `settings.json` (defaulting to `worker_minutes: 60`, `wind_down_minutes: 5`, `check_in_minutes: 5`, and session defaults for `roles`) and run `astack-tools doctor` to check whether `taskex`, `orchestral`, and `werkflow` are installed in the managed venv.
2. **Ask** in your reply (or with `request_user_input` in Plan mode), showing current values first:
   - Worker time limit, wind-down buffer, and lead check-in interval (minutes).
   - Model, provider, and effort for `worker` and `reviewer` (and optionally `lead` / `researcher`), leaving blank to inherit the session.
   - Whether to install or update the Python automation stack via `astack-tools install` (`skip`, `core`, `standard`, or `all`, plus any extra `werkflow` modules).

   Codex options: any model/provider configured in Codex plus reasoning effort (`low`, `medium`, `high`), written per agent TOML as `model`, `model_provider`, and `model_reasoning_effort`. Never pick values on the person's behalf.
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

5. **Install the agents.** Copy `agents/astack-worker.toml` and `agents/astack-reviewer.toml` (two folders up from this file) to `$CODEX_HOME/agents/` (`~/.codex/agents/` by default), replacing older copies. Right after `description` in each copy, write any configured `model`, `model_provider`, and `model_reasoning_effort` keys (omitting session defaults). If `/hooks` marks astack's hook untrusted, ask the person to trust it.
6. **Install automation tools if chosen:** run `astack-tools install --profile <choice>` (adding `--modules ...` if requested) and verify with `astack-tools doctor`.
7. **Confirm** in one short summary: saved values, file path, automation venv status, and that changes apply from the next run (program instructions still override them).
