---
name: analyze-environment
description: "Inspect the machine, repo configs/infra/env-var names, installed CLIs, MCP servers, APIs, and services, run safe read-only/dry-run and auth-status probes, install user-space tooling when authorized (unattended), and publish a shared TOOLS.md catalog for all agents—isolating only human-only auth steps. Use for researcher, worker, reviewer, or lead environment and system-access discovery."
disable-model-invocation: true
---

# Analyze environment

Map the local runtime, external systems, CLIs, APIs, MCP servers, and access paths relevant to the task, publish a shared `TOOLS.md` catalog for all agents, install missing user-space tooling when authorized, and isolate **only** genuine human-only auth steps.

1. **Discover what the task touches (**rtfm**):** inspect the prompt/brief, repo configs, CI/CD workflows, IaC/infra manifests, scripts, and environment-variable *names* (never print or log secret values—**no-leaked-secrets**) to list every runtime, CLI, API, SDK, MCP server, and external service correlated with the problem.
2. **Probe safely (read-only & dry-run are always allowed):**
   - Check OS, CPU architecture, language runtimes/toolchains, attached MCP tools, and available CLIs across `PATH` and standard user/system directories (`~/.local/bin`, `/opt/homebrew/bin`, `/usr/local/bin`, `~/.cargo/bin`, etc.).
   - Run read-only, dry-run, and auth-status checks against relevant systems (e.g., `gh auth status`, `glab auth status`, `aws sts get-caller-identity`, `kubectl diff`/`auth can-i`, `terraform plan`, `--dry-run`, read-only `GET`)—never balk at safe read-only inspection or dry-run probes.
   - Classify each tool or interface:
     - **`ready`**: installed/reachable and read-only/auth probe succeeds.
     - **`needs-install`**: missing locally, with an exact non-root user-space install command (`uv`, `brew`, `pipx`, `npm`, `cargo`, or release binary to `~/.local/bin`).
     - **`needs-human-auth`**: CLI/API is ready or installable, but requires interactive human login, SSO, MFA, or credential entry—record the exact single command the person must run (e.g., `gh auth login`, `aws sso login --profile <name>`).
     - **`unreachable`**: network, host, or permission wall blocking access, with exact error.
3. **Publish a shared `TOOLS.md` catalog:**
   - Write (or return under `TOOLS & ACCESS CATALOG` in your report for the lead to merge into `<program>/TOOLS.md`) each tool/service's purpose, status, path/endpoint/MCP name, non-root install command, auth-check command, verified read-only/dry-run commands, and human login command if `needs-human-auth`.
   - Record key runtime/environment facts (OS/arch, versions, active local services, base paths) so downstream **find-it** repros and **prove-it** checks match reality without re-probing.
4. **Install & wield missing user-space tooling when authorized (**decisions-in-plain-words**, **automate-this**):**
   - **Researchers and reviewers** stay read-only: discover, run read-only/dry-run probes, and emit the `TOOLS & ACCESS CATALOG` for the lead and workers.
   - **Lead and workers** under `autonomy.mode: "unattended"` (never using `sudo`/root or paid signups): install `needs-install` CLIs/SDKs into user-owned locations (`~/.local/bin`, isolated `uv` venv, Homebrew), verify read-only/dry-run behavior, wrap repeated queries into secret-safe scripts (**automate-this**), and update `<program>/TOOLS.md` to `ready` so every agent can wield them immediately.
5. **Isolate only the human auth step:** never block on a missing CLI or unfamiliar API. Finish discovery, user-space installation, cataloging, and all unblocked work first; escalate **only** the single human-only auth action (exact command + what it unlocks) while continuing unblocked work.
