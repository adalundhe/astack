---
name: setup
description: "Configure worker timing, per-role model/provider/effort, and optional uv/Python automation stack (taskex, orchestral, werkflow + werkflow-modules, or pure-agentic default). Use for /astack:setup."
disable-model-invocation: true
---

# Setup

Configure timing, subagent model settings, and the automation runtime. Settings live in `~/.config/astack/settings.json` (or `$XDG_CONFIG_HOME/astack/settings.json`).

1. **Read current state.** Read `settings.json` (defaulting to `worker_minutes: 60`, `wind_down_minutes: 5`, `check_in_minutes: 5`, session defaults for `roles`, and `automation.mode: "agentic-only"` unless already configured) and run `astack-tools doctor` to inspect `uv`, compatible Python (`>=3.11`), the managed `uv` venv, and installed `taskex` / `orchestral` / `werkflow` packages.
2. **Ask**, showing current values first, using `AskUserQuestion`:
   - Worker time limit, wind-down buffer, and lead check-in interval (minutes).
   - Model, provider, and effort for `worker` and `reviewer` (and optionally `lead` / `researcher`), leaving blank to inherit the session.
   - **Automation stack (person's choice):**
     - **Pure-agentic workflows (decline Python stack):** skip installing `taskex`/`orchestral`/`werkflow`; default workflows to subagents (**lead**), host-native runners, CI, or repo-native scripts.
     - **Install/update Python automation stack via `uv`:** check for (and install if missing) Python `>=3.11` via `uv`, create/load an isolated `uv` venv (`~/.local/share/astack/venv` or a custom path), and install `core` (`taskex`, `orchestral`, `werkflow`), `standard` (core + common `werkflow-modules`), or `all` (plus optional `--modules` or `--from-github`).

   Claude Code options: `model` (`opus`, `sonnet`, `haiku`, `fable`), `effort` (`low`, `medium`, `high`, `xhigh`, `max`); provider is shared with the session. Never pick values on the person's behalf.
3. **Validate:** positive integers for timing (`wind_down_minutes < worker_minutes`), valid platform options for any role overrides, and a valid automation choice (`agentic-only` or a valid profile/module selection). Re-ask if invalid.
4. **Write `settings.json`** (creating parent directories if needed), omitting role fields left on session default:

   ```json
   {
     "worker_minutes": 60,
     "wind_down_minutes": 5,
     "check_in_minutes": 5,
     "roles": {
       "worker": {"model": "<model>", "provider": "<provider>", "effort": "<effort>"},
       "reviewer": {}
     },
     "automation": {
       "mode": "python-stack",
       "profile": "standard",
       "venv": "~/.local/share/astack/venv"
     }
   }
   ```

   If the person declined Python tooling, write `"automation": {"mode": "agentic-only"}` so **workflow-this** and **automate-this** default to pure-agentic workflows.
5. **Install what this tool needs.** Nothing in Claude Code: the plugin ships the agents and the hook.
6. **Provision the `uv` Python environment (only if chosen):**
   - If `uv` is missing from `PATH`, ask before installing `uv` (e.g., `brew install uv` or the official `uv` installer) or use an existing Python `>=3.11` via `--python`.
   - Run `astack-tools install --profile <choice>` (adding `--modules ...`, `--venv ...`, `--python ...`, or `--from-github` as requested). `astack-tools install` checks `uv python find '>=3.11'`, runs `uv python install` if no compatible Python is installed, creates the isolated `uv` venv, and installs the chosen packages.
   - Verify with `astack-tools doctor` (checking `core_ready` and `taskex`/`orchestral` capabilities) and show how scripts load the venv (`astack-tools python <script.py>`, `astack-tools werkflow ...`, or `eval "$(astack-tools env)"`).
7. **Confirm** in one short summary: saved values, settings path, automation mode (`agentic-only` or `python-stack` with Python/venv/package status), and that changes apply from the next run (program instructions still override them).

Referenced skills: `lead` (`${CLAUDE_SKILL_DIR}/../lead/SKILL.md`), `workflow-this` (`${CLAUDE_SKILL_DIR}/../workflow-this/SKILL.md`), `automate-this` (`${CLAUDE_SKILL_DIR}/../automate-this/SKILL.md`). Read any cited skill file before acting when its trigger applies.
