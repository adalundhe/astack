---
name: setup
description: "Configure per-role models (lead, worker, researcher), approved reviewer_pool across detected harnesses, autonomy grant (supervised vs unattended), timers, ~/.astack initialization, CLI PATH links, and optional uv/Python automation stack. Use for /astack:setup."
disable-model-invocation: true
---

# Setup

Configure per-role models, the approved `reviewer_pool`, the **autonomy grant**, role timers, CLI `PATH` links, and the automation runtime. Settings live in `~/.config/astack/settings.json` (or `$XDG_CONFIG_HOME/astack/settings.json`).

**Stay fast and in setup mode:**

- Never read plugin/repo source files, run `git diff`/`git status`, run `--dry-run` pre-checks, or edit repository files during setup.
- If a helper script fails, note it in one line and move straight to Step 2.

1. **Read current state (one command).**
   - Read `settings.json` if present. Defaults are `worker_minutes: 60`, `reviewer_minutes: 30`, `researcher_minutes: 30`, `wind_down_minutes: 5`, `check_in_minutes: 5`, session defaults for `roles`, empty `reviewer_pool`, `autonomy.mode: "supervised"`, and `automation.mode: "agentic-only"`. If an old config has `roles.reviewer`, note it for one-time conversion into `reviewer_pool` in Step 4.
   - Locate `astack-tools` (`PATH`, `~/.local/bin/astack-tools`, `${CLAUDE_SKILL_DIR}/../../bin/astack-tools`, or installed plugin roots) and run `astack-tools doctor --json`. One call reports OS/arch, `~/.astack` status, detected harnesses, Claude `Skill` permission, `PATH`, `uv`, Python `>=3.11`, and venv packages.
   - If a skills-only loader omitted `bin/`, probe installed harnesses (`claude`, `codex`, `agy`, `gemini`, `cursor-agent`, `agent`, `devin`, `pi`) and `uv` in one command. Offer to bootstrap `bin/astack-*` into `~/.local/bin` in Round 2 (or run it directly under `unattended`).
2. **Ask**, showing current values first, using `AskUserQuestion`:
   Ask all choices up front in **two clean rounds** before writing files or installing packages. Never pick values on the person's behalf or assume a single vendor.
   - **Round 1 — Agent roles and approved `reviewer_pool`:**
     - Ask `lead`, `worker`, `researcher`, and `reviewer_pool` together. Build choices dynamically from detected harnesses (`claude`, `codex`, `agy`, `gemini`, `cursor`, `devin`, `pi`, or custom CLI) plus **Inherit session** and custom entries. Users may freely mix providers and harnesses across roles.
     - For `reviewer_pool`, ask which `{provider, model, effort, harness?}` entries are approved for **review**, **lead**, **go**, and **dagify**. **Tell the person explicitly that this list also decides which vendors/providers see their code.** Propose 4–5 diverse models already detected on this machine without burdening the person with estimator math.
   - **Round 2 — Autonomy grant, timing, CLI `PATH`, and automation runtime:**
     1. **Autonomy grant (`autonomy`):** choose **`supervised`** (default) vs. **`unattended`** vs. custom `allow`/`deny`. Read-only and dry-run probes are always allowed. Show what `unattended` permits (`local_worktrees_and_experiments`, `out_of_dir_work`, `user_space_tool_install`, `feature_branch_push`, `feature_branch_rebase_force_with_lease`, `open_and_update_pr`, `watch_pr_and_fix_ci`, `post_audited_pr_replies`) and what it denies (`merge_pr`, `push_protected_branch`, `close_or_delete_others_pr`, `prod_deploy_or_destructive_migration`, `spend_money_or_billing_changes`, `publish_external_release`, `weaken_verification_gates`). Let the person toggle any entry.
     2. **Timing:** hard limits for `worker_minutes`, `reviewer_minutes`, `researcher_minutes`, `wind_down_minutes`, and `check_in_minutes` (defaults `60 / 30 / 30 / 5 / 5`).
     3. **CLI `PATH` links (skip if already on `PATH`):** install `astack-*` launchers into `~/.local/bin` (so updates never break them), copy them, bootstrap `bin/astack-*` if omitted, or skip.
     4. **`claude` `Skill` permission (only if `claude` is detected and `doctor` shows `Skill` blocked/missing):** ask whether to run `astack-tools enable-claude-skills`.
     5. **Automation stack:** choose **Pure-agentic (`agentic-only`)** vs. **Python stack via `uv`** (`core`, `standard`, or `all`, plus optional extra modules or `--from-github`).
     6. **Venv & Python (only if Python stack is chosen):** default isolated `uv` venv (`~/.local/share/astack/venv` or `%LOCALAPPDATA%\astack\venv`) with Python `>=3.11`, or a custom path/Python spec.
3. **Validate:** require positive integers (`wind_down_minutes < min(worker_minutes, reviewer_minutes, researcher_minutes)`), non-empty `provider`/`model` strings on explicit entries, non-overlapping `autonomy.allow`/`deny`, and a valid automation choice. Re-ask only what is invalid.
4. **Write `settings.json` and initialize `~/.astack`:**
   Create parent directories if needed and omit fields left on session default. Convert any retired `roles.reviewer` entry into `reviewer_pool` and remove `roles.reviewer`:

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

   If the person declined Python tooling, write `"automation": {"mode": "agentic-only"}` so **workflow-this** and **automate-this** default to pure-agentic flows.

   Initialize `~/.astack` (`$HOME/.astack` on macOS/Linux; `%USERPROFILE%\.astack` on Windows) by running `<astack-tools> init-home`. If `astack-tools` is absent, create `$HOME/.astack` (`0700` on POSIX) or `%USERPROFILE%\.astack` directly—never store lessons inside a git repo.
5. **Install what this tool needs.** Nothing in Claude Code: the plugin ships the agents and the hook. Check reachability of every approved model in `reviewer_pool` with `astack-dispatch check-pool --host claude`: Claude Code's `Agent` tool selects models by alias (`opus`, `sonnet`, `haiku`), so those dispatch natively via `subagent_type: "astack:reviewer"`; pinned version IDs (e.g. `claude-opus-4-6`) and cross-provider / cross-harness models dispatch via `astack-dispatch run` (`claude`, `codex`, `agy`, `cursor-agent`/`agent`, `devin`, `pi`, `gemini`, or custom CLI); report any approved model reachable through neither as unreachable rather than letting **review** silently substitute another model.
   - If the person chose `PATH` links, run `<astack-tools> link-bin` (or `--copy`) before Step 6.
   - If `bin/` was omitted and they chose bootstrap, download the `adalundhe/astack` tarball into a temp dir, copy `bin/astack-*` and `lib/` into `~/.local/bin` (`_astack_lib/`), then run `astack-dispatch check-pool`.
   - If they enabled `claude` `Skill` permissions, run `<astack-tools> enable-claude-skills`.
6. **Provision the `uv` Python environment (only if chosen):**
   - If `uv` is missing, ask before installing `uv` or use an existing Python `>=3.11` via `--python`.
   - Run `<astack-tools> install --profile <choice>` (adding `--modules`, `--venv`, `--python`, or `--from-github` as requested). If `astack-tools` is absent, run `uv python find '>=3.11'`, `uv venv`, and `uv pip install` directly.
   - Show how to run the venv (`astack-tools python <script.py>`, `astack-tools werkflow ...`, or `astack-tools env`).
7. **Confirm** in one short summary: saved roles, `reviewer_pool` (noting unreachable models), autonomy grant, timing, settings path, `~/.astack` status, `PATH` link status, and automation mode. Note that changes apply on the next run.
