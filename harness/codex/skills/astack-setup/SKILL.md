---
name: astack-setup
description: "Configure per-role provider/model/effort (lead, worker, researcher), approved reviewer_pool across detected harnesses, worker timing, CLI PATH links, and optional uv/Python automation stack (or pure-agentic default). Use for $astack-setup."
---

# Setup

Configure per-role agent providers/models, the approved `reviewer_pool`, timing, CLI `PATH` links, and the automation runtime. Settings live in `~/.config/astack/settings.json` (or `$XDG_CONFIG_HOME/astack/settings.json`).

**Stay fast and in setup mode:**
- Never read plugin/repo source files, run `git diff`/`git status`, run `--dry-run` pre-checks, or edit repository files during setup.
- If a helper script is missing or errors, note it in one line, proceed straight to Step 2 so the person answers the questions, and fall back to direct `uv` commands if needed.

1. **Read current state (one command).**
   - Read `settings.json` if present (defaults: `worker_minutes: 60`, `wind_down_minutes: 5`, `check_in_minutes: 5`, session defaults for `roles`, empty `reviewer_pool`, `automation.mode: "agentic-only"`). If an existing `settings.json` still contains the retired `roles.reviewer` key, note it for one-time conversion into `reviewer_pool` in Step 4.
   - Locate `astack-tools` in order: `PATH` (`astack-tools`), `~/.local/bin/astack-tools`, or `../../bin/astack-tools`, and run it with `doctor --json` (one call reports platform/arch, detected agent harnesses/CLIs, `PATH` status, `uv`, Python `>=3.11`, venv, and installed packages).
   - If `astack-tools` is absent (e.g., a skills-only loader omitted `bin/`) or fails, run one quick probe checking installed harnesses (`claude`, `codex`, `agy`, `gemini`, `cursor`, `agent`, `devin`), `uv` across `PATH` and standard OS locations (`~/.local/bin`, `~/.cargo/bin`, `/opt/homebrew/bin`, `/usr/local/bin`, `%LOCALAPPDATA%\uv`), and the venv path—then move straight to Step 2.
2. **Ask** in your reply (or with `request_user_input` in Plan mode), showing current values first:
   Ask **all** setup choices up front in **two clean rounds** before writing settings or running any installs—never bounce between agent roles and Python setup, never ask a third disconnected follow-up question after installing packages, and never assume a single vendor or pick values on the person's behalf.
   - **Round 1 — Agent roles and approved `reviewer_pool` (ask together: `lead`, `worker`, `researcher`, and `reviewer_pool`):**
     - Build choices dynamically from the harnesses/providers detected in Step 1 (e.g., Anthropic/`claude`, OpenAI/`codex`, Google/`gemini`/`agy`, `cursor`, `devin`) plus **Inherit session** and custom `provider / model / effort`.
     - Users may mix providers across roles (e.g., Claude for `lead`, OpenAI/Codex for `worker`, Gemini/Antigravity for `researcher`, Cursor CLI, Devin, etc.). Never restrict choices to one vendor or claim all roles must share one provider.
     - For **`reviewer_pool`**, ask which reviewer models are approved: a list of `{provider, model, effort}` entries from any provider (used by **review**, **lead**, **go**, and **dagify** for vectored review). **Tell the person explicitly that this list also decides which vendors/providers see their code.** Note that risky review vectors need at least two different models in the pool to compute capture–recapture stopping estimates (a single-model pool works for clean low-risk reviews and flags any vector needing a second model).
   - **Round 2 — Timing, CLI `PATH`, and automation runtime (ask together):**
     1. **Timing:** worker time limit, wind-down buffer, and lead check-in interval (minutes; defaults `60 / 5 / 5`).
     2. **CLI `PATH` links:** whether to put `astack-*` (`astack-tools`, `astack-status`, `astack-decisions`, `astack-verify-merge`, `astack-check-gates`, `astack-review-ledger`, `astack-statechart`, `astack-stamp`) onto `PATH` in `~/.local/bin` via symlink, copy, or skip (skip this question if already on `PATH` or `bin/` is absent).
     3. **Automation stack (person's choice):** **Pure-agentic (`agentic-only`, decline Python stack)** vs. **Python stack via `uv`** (`core`: `taskex`+`orchestral`+`werkflow`, `standard`: core + common `werkflow-modules`, or `all`: core + all 14 modules, plus optional extra modules or `--from-github`; works on Windows, macOS, and Linux, arm64 & amd64).
     4. **Venv & Python (applies only if Python stack is chosen):** default isolated `uv` venv (`~/.local/share/astack/venv` on POSIX, `%LOCALAPPDATA%\astack\venv` on Windows) with detected/provisioned Python `>=3.11`, or a custom venv path / Python spec.
3. **Validate:** positive integers for timing (`wind_down_minutes < worker_minutes`), non-empty strings for any explicitly chosen role `provider`/`model`/`effort`, `reviewer_pool` as a JSON list of `{provider, model, effort}` objects (non-empty `provider` and `model` strings; optional `effort`), and a valid automation choice. Re-ask only what is invalid.
4. **Write `settings.json`** (creating parent directories if needed), omitting role fields left on session default. If an existing `settings.json` still contained the retired `roles.reviewer` key (single object or array), convert it into `reviewer_pool` once (wrapping a single object in a 1-element list) and delete `roles.reviewer`:

   ```json
   {
     "worker_minutes": 60,
     "wind_down_minutes": 5,
     "check_in_minutes": 5,
     "roles": {
       "lead": {"provider": "<provider>", "model": "<model>", "effort": "<effort>"},
       "worker": {"provider": "<provider>", "model": "<model>", "effort": "<effort>"},
       "researcher": {"provider": "<provider>", "model": "<model>", "effort": "<effort>"}
     },
     "reviewer_pool": [
       {"provider": "<provider-1>", "model": "<model-1>", "effort": "<effort-1>"},
       {"provider": "<provider-2>", "model": "<model-2>", "effort": "<effort-2>"}
     ],
     "automation": {
       "mode": "python-stack",
       "profile": "standard",
       "venv": "~/.local/share/astack/venv"
     }
   }
   ```

   If the person declined Python tooling, write `"automation": {"mode": "agentic-only"}` so **workflow-this** and **automate-this** default to pure-agentic workflows.
5. **Install the agents.** Copy `agents/astack-worker.toml` (two folders up from this file) to `$CODEX_HOME/agents/astack-worker.toml` (`~/.codex/agents/` by default), replacing any older copy, and write any configured `roles.worker` `model`, `model_provider`, and `model_reasoning_effort` keys right after `description` (omitting session defaults). Remove stale `$CODEX_HOME/agents/astack-reviewer*.toml` files, then install **one reviewer agent `.toml` per Codex-routable model in `reviewer_pool`**: copy `agents/astack-reviewer.toml` to `$CODEX_HOME/agents/astack-reviewer-<slug>.toml` (where `<slug>` is the lowercase `[a-z0-9-]+` slug of `<provider>-<model>-<effort>`, deduplicated if needed), update `name` to `"astack-reviewer-<slug>"`, and write that entry's `model`, `model_provider`, and `model_reasoning_effort` right after `description` (if `reviewer_pool` is empty, copy `agents/astack-reviewer.toml` as-is for the session default). Cross-provider entries without a configured Codex `model_provider` dispatch via their installed provider CLI (`claude`, `gemini`, `agy`, `cursor`, `devin`); report any approved model with neither an installed `.toml` (with a configured `model_provider`) nor an installed provider CLI as unreachable rather than letting **review** silently substitute another model. If `/hooks` marks astack's hook untrusted, ask the person to trust it. If `astack-tools` was found and the person chose to put `astack-*` on `PATH`, run `<astack-tools> link-bin` (adding `--copy` if they chose a copy; creates symlinks in `~/.local/bin` on macOS/Linux or `.cmd` shims on Windows) **before** running Step 6.
6. **Provision the `uv` Python environment (only if chosen, directly without `--dry-run`):**
   - If `uv` is genuinely absent from both `PATH` and standard OS install paths, ask before installing `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh` or `brew install uv` on macOS/Linux; `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"` or `winget install --id=astral-sh.uv -e` on Windows—all arm64 & amd64) or use an existing Python `>=3.11` via `--python`.
   - If `astack-tools` is available: run `<astack-tools> install --profile <choice>` (adding `--modules ...`, `--venv ...`, `--python ...`, or `--from-github` as requested). `install` already ends with `doctor` output.
   - If `astack-tools` is unavailable (skills-only install without `bin/`): run `uv` directly using the detected `uv` path (`uv python find '>=3.11' || uv python install 3.12`, `uv venv <venv> --python '>=3.11'`, `uv pip install --python <venv-python> --upgrade taskex orchestral werkflow ...`).
   - Show how to run or load the venv (`astack-tools python <script.py>`, `astack-tools werkflow ...`, `eval "$(astack-tools env)"` on POSIX, `astack-tools env --shell powershell | Invoke-Expression` on Windows, or directly `<venv-python>`).
7. **Confirm** in one short summary: saved roles, approved `reviewer_pool` (noting any unreachable model in this harness), timing, settings path, `PATH` link status, automation mode (`agentic-only` or `python-stack` with platform/arch, Python, venv, and package status), and that changes apply from the next run (program instructions still override them).

Referenced skills: `review` (`../astack-review/SKILL.md`), `lead` (`../astack-lead/SKILL.md`), `go` (`../astack-go/SKILL.md`), `dagify` (`../dagify/SKILL.md`), `workflow-this` (`../workflow-this/SKILL.md`), `automate-this` (`../automate-this/SKILL.md`). Read any cited skill file before acting when its trigger applies.
