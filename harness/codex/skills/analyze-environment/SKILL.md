---
name: analyze-environment
description: "Discover local tools, contexts, and access paths, publish <program>/TOOLS.md, and isolate human auth steps. Use when mapping a task's environment or missing CLIs."
---

# Analyze environment

Map the local runtime, CLIs, APIs, MCP servers, and access paths for the task. Publish `<program>/TOOLS.md` outside the repo, install missing user-space tools when authorized, and isolate **only** human-only auth steps.

1. **Discover what the task touches (`rtfm`):** inspect the brief, repo configs, CI workflows, IaC manifests, scripts, and env-var *names*. Never print secret values (**no-leaked-secrets**). List every relevant runtime, CLI, API, SDK, MCP server, and service.
2. **Probe safely—read-only checks are always allowed:**
   - Check OS, CPU architecture, runtimes, MCP tools, and CLIs across `PATH` and standard user dirs (`~/.local/bin`, `/opt/homebrew/bin`, `/usr/local/bin`, `~/.cargo/bin`).
   - Verify active target contexts for every cloud, edge/DNS/CDN, cluster, or IaC tool from repo configs (account, zone, cluster/namespace, workspace—illustrative, never exhaustive). Record them in `<program>/TOOLS.md`, because an unchecked context can mutate the wrong environment.
   - Run strictly read-only, non-locking auth/version/status probes (forge `auth status`, cloud identity check, cluster `diff`, read-only `GET`). Do not run `terraform init` or `terraform plan` during discovery without explicit scope—`init` writes local files and `plan` takes remote state locks and executes external data sources (`safe-iac`).
   - Classify each tool:
     - **`ready`:** installed or reachable, and read-only probe succeeds.
     - **`needs-install`:** missing locally, with an exact non-root user-space install command.
     - **`needs-human-auth`:** ready or installable, but needs interactive login, SSO, or MFA. Record the exact human command (e.g., `gh auth login`).
     - **`unreachable`:** network, host, or permission wall, with the exact error.
3. **Publish `<program>/TOOLS.md` (outside the repo):** write the catalog—or return it under `TOOLS & ACCESS CATALOG` to Lead. List each tool's purpose, status, path or MCP name, non-root install command, auth probe, verified read-only commands, and human login command if `needs-human-auth`. Include OS/arch and runtime versions so `find-it` and `prove-it` match reality without re-probing. Save durable project environment notes outside transient programs under `$HOME/.astack/<project_name>/docs/` (`astack-tools docs path`), and pair with **jack-in** when building a connection recipe.
4. **Install missing user-space tooling when authorized (`decisions-in-plain-words`):**
   - **Researchers and reviewers** stay read-only and emit the catalog for Lead and workers.
   - **Lead and workers** under `unattended` with `user_space_tool_install` allowed (and not in `autonomy.deny`; never `sudo` or paid signups): install `needs-install` tools into user-owned paths (`~/.local/bin`, `uv` venv, Homebrew). Verify read-only probes, wrap repeated queries in secret-safe scripts (`automate-this`), and mark `<program>/TOOLS.md` `ready`.
5. **Isolate only the human auth step:** never block on a missing CLI or unfamiliar API. Finish discovery, installation, cataloging, and unblocked work first. Escalate only the exact human auth command and what it unlocks.

**Done when:** `<program>/TOOLS.md` classifies every touched tool, authorized user-space installs are verified `ready`, and only genuine `needs-human-auth` commands remain.

Referenced skills: `no-leaked-secrets` (`../no-leaked-secrets/SKILL.md`), `jack-in` (`../jack-in/SKILL.md`). Read any cited skill file before acting when its trigger applies.
