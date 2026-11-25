---
name: setup
description: "Configure per-role provider/model/effort (lead, worker, researcher), approved reviewer_pool across detected harnesses, autonomy grant (supervised vs unattended allow/deny), worker/reviewer/researcher timers, Claude skill permissions, CLI PATH links, and optional uv/Python automation stack (or pure-agentic default). Use for /astack:setup."
disable-model-invocation: true
---

# Setup

Configure per-role agent providers/models, the approved `reviewer_pool`, the **autonomy grant** (what unattended execution permits and forbids), timing, CLI `PATH` links, and the automation runtime. Settings live in `~/.config/astack/settings.json` (or `$XDG_CONFIG_HOME/astack/settings.json`).

**Stay fast and in setup mode:**
- Never read plugin/repo source files, run `git diff`/`git status`, run `--dry-run` pre-checks, or edit repository files during setup.
- If a helper script is missing or errors, note it in one line, proceed straight to Step 2 so the person answers the questions, and fall back to direct `uv` commands if needed.

1. **Read current state (one command).**
   - Read `settings.json` if present (defaults: `worker_minutes: 60`, `reviewer_minutes: 30`, `researcher_minutes: 30`, `wind_down_minutes: 5`, `check_in_minutes: 5`, session defaults for `roles`, empty `reviewer_pool`, `autonomy: {"mode": "supervised", "allow": [], "deny": ["merge_pr", "push_protected_branch", "close_or_delete_others_pr", "prod_deploy_or_destructive_migration", "spend_money_or_billing_changes", "publish_external_release", "weaken_verification_gates"]}`, `automation.mode: "agentic-only"`; older configs without `reviewer_minutes`/`researcher_minutes` fall back to `worker_minutes`). If an existing `settings.json` still contains the retired `roles.reviewer` key, note it for one-time conversion into `reviewer_pool` in Step 4.
   - Locate `astack-tools` in order: `PATH` (`astack-tools`), `~/.local/bin/astack-tools`, `${CLAUDE_SKILL_DIR}/../../bin/astack-tools`, or installed plugin/cache roots (`~/.claude/plugins`, `~/.codex`, `$CODEX_HOME`, `~/.cursor/plugins`, `~/.gemini`, `~/.agents`) picking the highest-version copy that includes `bin/`, and run it with `doctor --json` (one call reports platform/arch, detected agent harnesses/CLIs, `claude` `Skill` permission status in `~/.claude/settings.json`, `PATH` status, `uv`, Python `>=3.11`, venv, and installed packages).
   - If a skills-only loader omitted `bin/` everywhere and `astack-tools` is absent, run one quick probe checking installed harnesses (`claude`, `codex`, `agy`, `gemini`, `cursor-agent`, `agent`, `cursor`, `devin`, `pi`), `uv` across `PATH` and standard OS locations (`~/.local/bin`, `~/.cargo/bin`, `/opt/homebrew/bin`, `/usr/local/bin`, `%LOCALAPPDATA%\uv`), and the venv path—then in Round 2 offer to bootstrap `bin/astack-*` into `~/.local/bin` from the matching `adalundhe/astack` release/repo (or run it directly when `autonomy.mode` is `"unattended"`), and move straight to Step 2.
2. **Ask**, showing current values first, using `AskUserQuestion`:
   Ask **all** setup choices up front in **two clean rounds** before writing settings or running any installs—never bounce between agent roles and Python setup, never ask a third disconnected follow-up question after installing packages, and never assume a single vendor or pick values on the person's behalf.
   - **Round 1 — Agent roles and approved `reviewer_pool` (ask together: `lead`, `worker`, `researcher`, and `reviewer_pool`):**
     - Build choices dynamically from the harnesses/providers detected in Step 1 (e.g., Anthropic/`claude`, OpenAI/`codex`, Google/`agy`/`gemini`, Cursor CLI/`agent`, `devin`, multi-provider `pi`, or custom CLI) plus **Inherit session** and custom `provider / model / effort / harness`.
     - Users may mix providers and harnesses across roles (e.g., Claude for `lead`, Codex for `worker`, Antigravity or Pi for `researcher`, Cursor CLI, Devin, etc.). Never restrict choices to one vendor or claim all roles must share one provider or harness.
     - For **`reviewer_pool`**, ask which reviewer models are approved: a list of `{provider, model, effort}` entries (with optional `harness`—`claude`, `codex`, `agy`, `cursor`, `devin`, `pi`, `gemini`, or `custom` with `command`) from any provider and harness (used by **review**, **lead**, **go**, and **dagify** for vectored review). **Tell the person explicitly that this list also decides which vendors/providers see their code.** By default, propose a diverse multi-model pool (4–5 distinct models/tiers drawn from the harnesses and providers already detected on this machine—never burden the user with stopping-estimator math).
   - **Round 2 — Autonomy grant, timing, CLI `PATH`, and automation runtime (ask together):**
     1. **Autonomy grant (`autonomy`):** choose **`supervised`** (default: settle technical choices locally, pause before mutating external actions unless asked; read-only/dry-run probes are always allowed) vs. **`unattended`** ("go ahead unattended") vs. **custom `allow`/`deny`**. Show explicitly what **`unattended`** permits without asking confirmation (`allow`: `local_worktrees_and_experiments`, `out_of_dir_work`, `user_space_tool_install`, `feature_branch_push`, `feature_branch_rebase_force_with_lease` after `git range-diff` + `patch-id-check`, `open_and_update_pr`, `watch_pr_and_fix_ci`, `post_audited_pr_replies` after `/leave-feedback` `CLEAR`) and what it **never** permits without explicit per-action approval (`deny`: `merge_pr`, `push_protected_branch`, `close_or_delete_others_pr`, `prod_deploy_or_destructive_migration`, `spend_money_or_billing_changes`, `publish_external_release`, `weaken_verification_gates`). Let the person toggle any entry in `allow` or `deny`.
     2. **Timing:** hard time limits for workers, reviewers, and researchers, plus wind-down buffer and lead check-in interval (minutes; defaults `60 / 30 / 30 / 5 / 5`; lead enforces check-ins and timers across all three roles).
     3. **CLI `PATH` links (or bootstrap if `bin/` was omitted):** whether to put `astack-*` (`astack-tools`, `astack-dispatch`, `astack-watch-pr`, `astack-watch-github`, `astack-watch-gitlab`, `astack-watch-bitbucket`, `astack-status`, `astack-decisions`, `astack-verify-merge`, `astack-check-gates`, `astack-review-ledger`, `astack-statechart`, `astack-stamp`) onto `PATH` in `~/.local/bin` via launchers (each runs the newest installed astack, so an update doesn't break it), copy, bootstrap from `adalundhe/astack` (when a skills-only loader omitted `bin/`), or skip (skip this question if already on `PATH`).
     4. **`claude` `Skill` permission (only if `claude` is detected and `doctor` shows `Skill` is blocked in `permissions.deny` or not yet explicitly allowed in `~/.claude/settings.json`):** ask whether to enable `Skill` in `~/.claude/settings.json` via `astack-tools enable-claude-skills` so `claude` sessions can auto-discover and load astack skills without being blocked.
     5. **Automation stack (person's choice):** **Pure-agentic (`agentic-only`, decline Python stack)** vs. **Python stack via `uv`** (`core`: `taskex`+`orchestral`+`werkflow`, `standard`: core + common `werkflow-modules`, or `all`: core + all 14 modules, plus optional extra modules or `--from-github`; works on Windows, macOS, and Linux, arm64 & amd64).
     6. **Venv & Python (applies only if Python stack is chosen):** default isolated `uv` venv (`~/.local/share/astack/venv` on POSIX, `%LOCALAPPDATA%\astack\venv` on Windows) with detected/provisioned Python `>=3.11`, or a custom venv path / Python spec.
3. **Validate:** positive integers for timing (`wind_down_minutes < min(worker_minutes, reviewer_minutes, researcher_minutes)`), non-empty strings for any explicitly chosen role `provider`/`model`/`effort`, `reviewer_pool` as a JSON list of `{provider, model, effort}` objects (non-empty `provider` and `model` strings; optional `effort`), `autonomy` as `{"mode": "supervised" | "unattended", "allow": [...], "deny": [...]}` with non-overlapping string lists, and a valid automation choice. Re-ask only what is invalid.
4. **Write `settings.json`** (creating parent directories if needed), omitting role fields left on session default. If an existing `settings.json` still contained the retired `roles.reviewer` key (single object or array), convert it into `reviewer_pool` once (wrapping a single object in a 1-element list) and delete `roles.reviewer`:

   ```json
   {
     "worker_minutes": 60,
     "reviewer_minutes": 30,
     "researcher_minutes": 30,
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
     "autonomy": {
       "mode": "unattended",
       "allow": [
         "local_worktrees_and_experiments",
         "out_of_dir_work",
         "user_space_tool_install",
         "feature_branch_push",
         "feature_branch_rebase_force_with_lease",
         "open_and_update_pr",
         "watch_pr_and_fix_ci",
         "post_audited_pr_replies"
       ],
       "deny": [
         "merge_pr",
         "push_protected_branch",
         "close_or_delete_others_pr",
         "prod_deploy_or_destructive_migration",
         "spend_money_or_billing_changes",
         "publish_external_release",
         "weaken_verification_gates"
       ]
     },
     "automation": {
       "mode": "python-stack",
       "profile": "standard",
       "venv": "~/.local/share/astack/venv"
     }
   }
   ```

   If the person declined Python tooling, write `"automation": {"mode": "agentic-only"}` so **workflow-this** and **automate-this** default to pure-agentic workflows.
5. **Install what this tool needs.** Nothing in Claude Code: the plugin ships the agents and the hook. Check reachability of every approved model in `reviewer_pool` with `astack-dispatch check-pool --host claude`: Claude Code's `Agent` tool selects models by alias (`opus`, `sonnet`, `haiku`), so those dispatch natively via `subagent_type: "astack:reviewer"`; pinned version IDs (e.g. `claude-opus-4-6`) and cross-provider / cross-harness models dispatch via `astack-dispatch run` (`claude`, `codex`, `agy`, `cursor-agent`/`agent`, `devin`, `pi`, `gemini`, or custom CLI); report any approved model reachable through neither as unreachable rather than letting **review** silently substitute another model. If `astack-tools` was found and the person chose to put `astack-*` on `PATH`, run `<astack-tools> link-bin` (adding `--copy` if they chose a copy; creates symlinks in `~/.local/bin` on macOS/Linux or `.cmd` shims on Windows) **before** running Step 6. If `bin/` was omitted by a skills-only loader and the person chose bootstrap, download the matching `adalundhe/astack` tarball (`curl -fsSL https://github.com/adalundhe/astack/archive/refs/heads/main.tar.gz`) into a temp dir, copy `bin/astack-*` into `~/.local/bin` with `chmod +x`, and then run `astack-dispatch check-pool` and Step 6 cleanly. If the person opted to enable `claude` `Skill` permissions in Round 2, run `<astack-tools> enable-claude-skills` as well.
6. **Provision the `uv` Python environment (only if chosen, directly without `--dry-run`):**
   - If `uv` is genuinely absent from both `PATH` and standard OS install paths, ask before installing `uv` (`curl -LsSf https://astral.sh/uv/install.sh | sh` or `brew install uv` on macOS/Linux; `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"` or `winget install --id=astral-sh.uv -e` on Windows—all arm64 & amd64) or use an existing Python `>=3.11` via `--python`.
   - If `astack-tools` is available: run `<astack-tools> install --profile <choice>` (adding `--modules ...`, `--venv ...`, `--python ...`, or `--from-github` as requested). `install` already ends with `doctor` output.
   - If `astack-tools` is unavailable (skills-only install without `bin/`): run `uv` directly using the detected `uv` path (`uv python find '>=3.11' || uv python install 3.12`, `uv venv <venv> --python '>=3.11'`, `uv pip install --python <venv-python> --upgrade taskex orchestral werkflow ...`).
   - Show how to run or load the venv (`astack-tools python <script.py>`, `astack-tools werkflow ...`, `eval "$(astack-tools env)"` on POSIX, `astack-tools env --shell powershell | Invoke-Expression` on Windows, or directly `<venv-python>`).
7. **Confirm** in one short summary: saved roles, approved `reviewer_pool` (noting any unreachable model in this harness), autonomy grant (`mode`, `allow`, `deny`), timing, settings path, `PATH` link status, automation mode (`agentic-only` or `python-stack` with platform/arch, Python, venv, and package status), and that changes apply from the next run (program instructions still override them).

Referenced skills: `review` (`${CLAUDE_SKILL_DIR}/../review/SKILL.md`), `lead` (`${CLAUDE_SKILL_DIR}/../lead/SKILL.md`), `go` (`${CLAUDE_SKILL_DIR}/../go/SKILL.md`), `dagify` (`${CLAUDE_SKILL_DIR}/../dagify/SKILL.md`), `workflow-this` (`${CLAUDE_SKILL_DIR}/../workflow-this/SKILL.md`), `automate-this` (`${CLAUDE_SKILL_DIR}/../automate-this/SKILL.md`). Read any cited skill file before acting when its trigger applies.
