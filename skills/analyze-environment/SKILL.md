---
name: analyze-environment
description: "Discover local runtimes, repo configs, CLIs, MCP servers, APIs, and services, run safe read-only/dry-run probes, install user-space tooling under unattended autonomy, and publish a shared TOOLS.md catalog isolating only human-only auth steps."
disable-model-invocation: true
---

# Analyze environment

Map the local runtime, CLIs, APIs, MCP servers, and access paths for the task, publish a shared `TOOLS.md` catalog, install missing user-space tools when authorized, and isolate **only** human-only auth steps.

1. **Discover what the task touches (**rtfm**):** inspect the brief, repo configs, CI workflows, IaC manifests, scripts, and env-var *names* (never print secret values—**no-leaked-secrets**). List every relevant runtime, CLI, API, SDK, MCP server, and service.
2. **Probe safely—read-only and dry-run checks are always allowed:**
   - Check OS, CPU architecture, runtimes, MCP tools, and CLIs across `PATH` and standard user dirs (`~/.local/bin`, `/opt/homebrew/bin`, `/usr/local/bin`, `~/.cargo/bin`).
   - Verify active target contexts for every cloud, edge/DNS/CDN, cluster, or IaC tool from repo configs (account, zone, cluster/namespace, workspace—illustrative, never exhaustive). Record them in `TOOLS.md` so no agent targets the wrong environment.
   - Run read-only, dry-run, and auth-status checks (forge `auth status`, identity check, cluster `diff`, IaC `plan`/`--dry-run`, read-only `GET`).
   - Classify each tool:
     - **`ready`:** installed/reachable and read-only probe succeeds.
     - **`needs-install`:** missing locally, with an exact non-root user-space install command.
     - **`needs-human-auth`:** ready or installable, but needs interactive login, SSO, or MFA—record the exact command for the person (e.g., `gh auth login`).
     - **`unreachable`:** network, host, or permission wall, with the exact error.
3. **Publish a shared `TOOLS.md` catalog:** write (or return under `TOOLS & ACCESS CATALOG` for the lead) each tool's purpose, status, path/MCP name, non-root install command, auth probe, verified read-only commands, and human login command if `needs-human-auth`. Include OS/arch and runtime versions so **find-it** and **prove-it** match reality without re-probing.
4. **Install missing user-space tooling when authorized (**decisions-in-plain-words**, **automate-this**):**
   - **Researchers and reviewers** stay read-only and emit the catalog for the lead and workers.
   - **Lead and workers** under `unattended` (never `sudo` or paid signups): install `needs-install` tools into user-owned paths (`~/.local/bin`, `uv` venv, Homebrew), verify read-only probes, wrap repeated queries in secret-safe scripts, and mark `TOOLS.md` `ready`.
5. **Isolate only the human auth step:** never block on a missing CLI or unfamiliar API. Finish discovery, installation, cataloging, and unblocked work first, then escalate only the exact human auth command and what it unlocks.
