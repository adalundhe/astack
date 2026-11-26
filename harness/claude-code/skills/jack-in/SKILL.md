---
name: jack-in
description: "Discover target environment access paths, build reusable connection tooling and scripts, and verify safety. Use when connecting to or automating access to an environment."
disable-model-invocation: true
---

# Jack in

Turn an environment connection requirement into verified, reusable scripts, wrappers, and tooling—not just ad-hoc notes. **Owned by the Lead** (run the three stages sequentially on single-agent hosts).

## 1. Lock the target environment and dispatch researchers

Confirm the exact environment the user named or the repo selects (**rtfm**, **lookup**). Check saved `$HOME/.astack/<project_name>/docs/` and `automations/` before rediscovering from scratch.

Dispatch read-only `astack:researcher` subagent(s) (`roles.researcher`, per **lead**) using **analyze-environment** to discover what is installed, configured, and reachable locally. Never assume a fixed list of vendors or CLIs—derive the tooling from the repo's real infrastructure and local host:

- **Target scope:** exact account, region, cluster, namespace, host, workspace, or local stack.
- **Network & perimeter gates:** VPN, bastion or jump host, private endpoint, tunnel, port-forward, or allowlist prerequisites.
- **Identity & auth:** SSO, role assumption, session token, cert, or key state (`ready`, `needs-install`, `needs-human-auth`, `unreachable`).
- **Connection & inspection tooling:** whichever discovered CLI, TUI, shell, database, IaC, or API clients fit the target, plus verified read-only probes.

## 2. Dispatch workers to wrap discovered tooling into user scripts

Dispatch isolated `astack:worker` subagent(s) (**lead**) to consume every discovered CLI, TUI, SDK, tunnel, or auth check into clean, ready-to-run scripts the user can invoke directly (**automate-this**, **stepped-complexity**, **safe-to-rerun**). Do not hand the user a pile of raw one-liners when a reusable script can wrap them cleanly.

- **Consume discovered tooling directly:** wrap the discovered tools so one clear entrypoint handles prerequisite checks, context switching, tunnels or port-forwards, interactive or read-only inspection, and clean teardown.
- **Where scripts live:** store scripts under `$HOME/.astack/<project_name>/automations/<automation_name>/` (`astack-tools automations path`, or Windows `%USERPROFILE%\.astack\...`) using **taskex**, **orchestral**, **werkflow**, or portable shell/Python. Put files inside the repo only when asked.
- **Where docs live:** save a brief usage and prerequisite guide under `$HOME/.astack/<project_name>/docs/` (`astack-tools docs path`).
- **Built-in guardrails:**
  - Verify the active target context before running any command so scripts never hit the wrong environment.
  - Default to read-only inspection (**least-privilege**). Block production or mutating actions unless explicitly requested and approved (**decisions-in-plain-words**).
  - Never hardcode or print tokens, private keys, or credentials (**no-leaked-secrets**).
  - Surface missing tools (`needs-install`) and human VPN or SSO logins (`needs-human-auth`) with exact next-step commands. Clean up temporary tunnels and port-forwards on exit (**cleanup**).
  - Save any captured diagnostic logs, traces, or metrics to `$HOME/.astack/<project_name>/logging/<logs|traces|metrics>/` (`astack-tools logging path`).

## 3. Run limited vectored review (safety and correctness)

Run a focused, limited vectored review (**review**, **adversarial-review**) with `astack:reviewer` covering two vectors only:

1. **Safety:** verify target-context locking (no accidental prod or cross-env hits), **least-privilege** read-only defaults, and **no-leaked-secrets** across code, args, env, and logs. Check safe argument handling (`shell=False` or strict quoting) and clean tunnel teardown.
2. **Correctness:** run a real read-only dry-run or non-destructive probe against the target (**prove-it**). Verify prerequisite checks (`needs-install`, `needs-human-auth`) and non-zero exit codes on failure.

Save review proof under `$HOME/.astack/<project_name>/reviews/<date_time>/` (`astack-tools reviews path`). Have workers fix any blocking finding and re-verify before delivery.

## 4. Deliver ready-to-run scripts

Reply concisely with:
- exact paths to the generated scripts (`automations/`) and docs (`docs/`);
- any remaining human-only prerequisite (VPN or interactive login command);
- exact one-command invocations to connect, inspect, and cleanly disconnect (**triage**, **net-trace**, **find-it**).

**Done when:** researchers mapped the environment via **analyze-environment**, workers consumed the discovered tooling into verified user scripts, and limited safety-and-correctness vectored review cleared with saved proof.

Referenced skills: `rtfm` (`${CLAUDE_SKILL_DIR}/../rtfm/SKILL.md`), `lookup` (`${CLAUDE_SKILL_DIR}/../lookup/SKILL.md`), `lead` (`${CLAUDE_SKILL_DIR}/../lead/SKILL.md`), `analyze-environment` (`${CLAUDE_SKILL_DIR}/../analyze-environment/SKILL.md`), `automate-this` (`${CLAUDE_SKILL_DIR}/../automate-this/SKILL.md`), `stepped-complexity` (`${CLAUDE_SKILL_DIR}/../stepped-complexity/SKILL.md`), `safe-to-rerun` (`${CLAUDE_SKILL_DIR}/../safe-to-rerun/SKILL.md`), `taskex` (`${CLAUDE_SKILL_DIR}/../taskex/SKILL.md`), `orchestral` (`${CLAUDE_SKILL_DIR}/../orchestral/SKILL.md`), `werkflow` (`${CLAUDE_SKILL_DIR}/../werkflow/SKILL.md`), `least-privilege` (`${CLAUDE_SKILL_DIR}/../least-privilege/SKILL.md`), `decisions-in-plain-words` (`${CLAUDE_SKILL_DIR}/../decisions-in-plain-words/SKILL.md`), `no-leaked-secrets` (`${CLAUDE_SKILL_DIR}/../no-leaked-secrets/SKILL.md`), `cleanup` (`${CLAUDE_SKILL_DIR}/../cleanup/SKILL.md`), `review` (`${CLAUDE_SKILL_DIR}/../review/SKILL.md`), `adversarial-review` (`${CLAUDE_SKILL_DIR}/../adversarial-review/SKILL.md`), `prove-it` (`${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`), `triage` (`${CLAUDE_SKILL_DIR}/../triage/SKILL.md`), `net-trace` (`${CLAUDE_SKILL_DIR}/../net-trace/SKILL.md`), `find-it` (`${CLAUDE_SKILL_DIR}/../find-it/SKILL.md`). Read any cited skill file before acting when its trigger applies.
