---
name: astack-setup
description: "Configure worker timing and per-role model, provider, and effort in ~/.config/astack/settings.json. Use for $astack-setup."
disable-model-invocation: true
---

# Setup

Configure timing and subagent model settings in `~/.config/astack/settings.json` (or `$XDG_CONFIG_HOME/astack/settings.json`).

1. **Read current settings.** Default to `worker_minutes: 60`, `wind_down_minutes: 5`, `check_in_minutes: 5`, and session defaults for `roles` (`worker`, `reviewer`, plus optional `lead` / `researcher`).
2. **Ask** in your reply (or with `request_user_input` in Plan mode), showing current values first:
   - Worker time limit, wind-down buffer, and lead check-in interval (minutes).
   - Model, provider, and effort for `worker` and `reviewer` (and optionally `lead` / `researcher`), leaving blank to inherit the session.

   Codex options: any model/provider configured in Codex plus reasoning effort (`low`, `medium`, `high`), written per agent TOML as `model`, `model_provider`, and `model_reasoning_effort`. Never pick values on the person's behalf.
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

5. **Install the agents.** Copy `agents/astack-worker.toml` and `agents/astack-reviewer.toml` (two folders up from this file) to `$CODEX_HOME/agents/` (`~/.codex/agents/` by default), replacing older copies. Right after `description` in each copy, write any configured `model`, `model_provider`, and `model_reasoning_effort` keys (omitting session defaults). If `/hooks` marks astack's hook untrusted, ask the person to trust it.
6. **Confirm** in one line: saved values, file path, and that they apply from the next run (program instructions still override them).
