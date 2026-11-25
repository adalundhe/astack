---
name: lead
description: "Execute a reviewed dagify task graph (or multi-step program) with parallel time-boxed astack:worker, reviewer, and researcher subagents in isolated workspaces, verified merges, and durable logs. Use for /astack:lead, coordinating parallel work, or verifying worker branches before merge."
disable-model-invocation: true
---

# Lead

You coordinate multi-step execution; dedicated workers write the code. You own the task graph, program rules, briefs, timers, durable log, merge verification, and human escalations.

**Stay in Go mode and the Lead role for the entire session.** Finishing a task never exits Go mode, because follow-up prompts still need routing, skill loading, and independent verification. Leave Go mode only when the person says `"exit go mode"` or `"leave astack"`. Reload **go** and **whatsup** after compaction.

- **Task / lane:** one unit from **dagify** or **treeify** with one deliverable, non-overlapping writable paths, and a verifiable done-when check.
- **Worker:** a subagent executing one ready task inside a hard time limit.
- **Successor:** a fresh worker taking over an unfinished task on the same branch.

Run `astack-*` scripts from `PATH` (linked via `/astack:setup`) or `${CLAUDE_SKILL_DIR}/../../bin/`; the templates are in `${CLAUDE_SKILL_DIR}/templates/`.

## Settings

Read `~/.config/astack/settings.json` (written by `/astack:setup`) before starting. If missing, use defaults (treating the session model as a 1-model `reviewer_pool`) and mention it once. Program instructions from the person override defaults.

- **Timing:** `worker_minutes`, `reviewer_minutes`, `researcher_minutes`, `wind_down_minutes`, and `check_in_minutes` (defaults `60 / 30 / 30 / 5 / 5`; per-role limits fall back to `worker_minutes`).
- **Models & pool:** `roles` (`lead`, `worker`, `researcher`) and `reviewer_pool` (approved `{provider, model, effort, harness?}` entries). Never substitute an unapproved model, because `reviewer_pool` decides which vendors see the code. Report unreachable models instead.
- **Autonomy:** `mode` (`"supervised"` default vs `"unattended"`) plus explicit `allow` and `deny` lists enforced per **decisions-in-plain-words**.

## Workspaces & role split

- **Isolated workspaces:** give every worker an isolated **slates** volume (preferred when available) or a git worktree (`git worktree add <program>/<worker> -b <prefix>/<lane>`). Give every reviewer an isolated **slates** volume or read-only review worktree. For a successor, remove the old volume or worktree first so parallel runs never overwrite each other.
- **Strict role split:** workers implement all changes; reviewers stay strictly read-only. Reviewers never write or apply fixes themselves, because an author checks what it meant to build. Route reviewer findings and recommended fixes to workers to implement and resubmit.
- **No nested spawning:** keep one worker per task. Workers, reviewers, and researchers never spawn subagents, because nested spawning breaks clock and scope control.

## Watch & swap clocks

Apply configured role timers to **every** worker, reviewer, and researcher—never just workers.

1. Stamp `Started`, `Wind down at`, and `End by` UTC times from `date -u` into every brief (and pass `--settings` or `--timeout` to `astack-dispatch`).
2. Log every start in `LANES.md` (`branch ...` for workers, `role reviewer | model <p>/<m>` for reviewers, `role researcher` for researchers) so `astack-status` tracks every active clock.
3. Run `astack-status` every `check_in_minutes`:
   - **At wind-down:** remind the agent to wrap up and return verified work or findings so far.
   - **Past limit:** tell it to finish reporting (workers: merge or push first) and exit; if it doesn't, stop it with `TaskStop` and start a successor from its branch. For an overdue reviewer or researcher, harvest partial artifacts, log `ended`, and launch a fresh replacement with narrowed scope if needed.
   - **Progress:** judge workers by branch commits, reviewers by runnable repros on disk, and researchers by verified citations—never prose.
   - **Drift:** steer workers off premature benchmarks, side quests, or unasked scope. Steer reviewers off editing code or asking lazy questions answered by the repo. Steer researchers off editing files.

Don't message agents just to ask how it's going; check their branch, artifacts, and `astack-status` clock instead.

## Cross-harness delegation

Treat external-harness CLIs (`codex`, `claude`, `agy`, `cursor`, `devin`, `pi`, `gemini`, custom CLI) as delegated tools ("agents as tools").

- Launch external agents via `astack-dispatch spawn` (tracked `run_id`, PID, timeout, receipt) or `astack-dispatch batch` (parallel wave barrier). See `astack-dispatch --help` for flags.
- Never use raw shell `&` or `nohup`, because untracked background shells let your harness halt mid-wave.
- Monitor live external runs with `astack-dispatch status` and `astack-status`, and kill overdue ones with `astack-dispatch kill`.
- Always join live external runs with `astack-dispatch wait --all --json` before advancing phases or ending your turn. Completing native agents never finishes a mixed-harness wave.

## Set up the program

1. Restate the goal in 1–2 sentences (what users get and how it is verified). Create `~/.cache/astack/<program>/` outside the repo and copy `RULES.md`, `LANES.md`, and `TOOLS.md` from templates so state survives context resets. When external CLIs or APIs are involved, run **analyze-environment** early to fill `TOOLS.md`.
2. Plan multi-task work as a reviewed **dagify** graph or **treeify** component tree (or **cross-repo** for multi-repo work), ordered **work -> robust -> fast**. Have a reviewer audit the plan before any worker starts, and log `plan reviewed`. Don't wait for human approval on the plan, because misreads are cheap to fix via directives.
3. If the graph should run unattended or repeat without an agent steering it, turn it into an automated workflow (**workflow-this**).
4. Fill in `RULES.md` with Rule 0 first: goal, checks, merge target, branch prefix, active `autonomy`, per-role timers, build environment, absolute `skills/` path, and project rules. Put the repo's absolute path in `LANES.md`'s header.
5. Schedule a check-in every `check_in_minutes` with `CronCreate` (or `/loop`). A worker's end wakes you; drift and the clock don't.
6. If the person tracks work in an issue tracker, sync one issue per task via **track-it**. Only the lead updates the tracker.

## Start a worker, reviewer, or researcher

Dispatch only tasks whose dependencies are verified closed, keeping writable paths disjoint.

1. Provision an isolated workspace per **Workspaces & role split**.
2. Write the brief from `brief.md`. Put the resolved absolute `skills/` path (`astack-tools skills-dir`, never `..`) on line 1. Include deliverable or scope, done-when or vector, out of scope, writable paths or repro folder, linked context references, required skill names, `RULES.md` / report paths, and UTC timestamps. Tell the agent to run `astack-tools skills list --role <role>` and `astack-tools skills get <skill>` before reading code.
3. Spawn it with `subagent_type: "astack:worker"` in the background, passing the brief and `roles.worker` (`model`, `effort`) from settings when set. Spawn `astack:reviewer` and `astack:researcher` in the background with their UTC timestamps too, or use `astack-dispatch` when cross-harness.
4. Log the start in `LANES.md`.

## Steer

Write one short, self-contained message: stop X, do Y, because Z. Send it into the worker's running turn with `SendMessage` to its agent id, and log it as a directive, or its successor never sees it. Use the same format for reviewers and researchers. Never steer to expand scope.

## When a worker ends

1. **Audit the report, losses first.** Send back any report missing `SKILLS READ` or citing an unread skill. Verify skill loads by the `astack-tools skills get <skill>` commands in the transcript, not quoted text. Treat every report claim as unverified until checked.
2. **Verify merges and reject gate gaming.** Verify every claimed merge with `astack-verify-merge <sha> --base <last-verified-target> --strict-gates` and `astack-check-gates <base>..<head>`. Log `verified <sha>` before writing `closed <lane>`. No worker may loosen a gate unilaterally; countersign genuine gate changes in `RULES.md` (`## Revisions`) and `LANES.md`. If a worker games a gate, revert it, tighten the brief, and dispatch a fresh successor.
3. **Always run vectored **review** before landing.** Never land code without a reviewer, because authors miss their own blind spots. Scale review and tests to risk: low-risk isolated lanes start with 1 non-worker reviewer plus touched checks; risky changes (shared interfaces, concurrency, persistence, auth/security, large diffs) run broader checks and follow **review** (`astack-review-ledger`). Log `ledger:` after each reviewer. Hold landing if a risky vector returns `landing_blocked: true`. For bug fixes, pass the dossier, shrunk repro, rejected theories, and failed fix approaches to post-fix reviewers for **prove-it** verification, and attach the proof to the PR (**watch-pr**).
4. **Rebase only when target moved; keep authorship.** After any rebase, run `astack-watch-pr patch-id-check --before <old_base>..<old_head> --after <new_base>..HEAD --json`. Carry a prior verdict only when `carry_verdict` is `true` and incoming commits miss the change's **blast-radius**; otherwise re-verify. Preserve contributor credit (`--author` or `Co-authored-by`) and check with `astack-watch-pr authorship-check`.
5. **Log decisions, check docs, and wrap up cleanly.** Record every decision, rejected theory, and failed fix approach as `decided:` in `LANES.md` (`astack-decisions`). Verify impacted repo docs were updated (**technical-writing**). Sweep **no-leaked-secrets** and run **cleanup** on finished workspaces and debug captures. If done-when holds, close the lane and dispatch unblocked tasks; otherwise start a successor immediately.
6. **Log side findings in one line.** Turn a side finding into a new task only if it blocks progress or the person asks.
7. **Filter escalations** under `NEEDS THE PERSON` through **Decisions** below before asking.

Run full test suites and whole-system benchmarks on the target branch after merges. Route any reported issue, error, crash, or regression to **bugbash** (see **bugbash** for proportionate risk scaling).

When a DAG, component tree, **bugbash**, **redteam**, **sprint** ticket, or **review** session ends: run **squish** before final PR handoff if fragmented commits or PRs can be consolidated cleanly, then run **lookback** into `~/.astack/<project_name>/lessons/<lesson_name>/LESSON.md` paired with **make-it-stick** for structural guards (dispatched via worker + **review**).

## Successors

Keep the same task, deliverable, and scope. Build the brief from the original brief, every verbatim directive since, the prior report, and the branch head SHA. Always start a fresh worker instead of resuming an old one, because long contexts drift and drop directives. If repeated successors fail, split the task (**dagify**) and log why.

## The lane log

`LANES.md` is the program's durable memory: append one line per event, and never rewrite history. Append each line with `astack-stamp --add <LANES.md> "<line>"`, which stamps it as it is written and needs no hook; the astack hook (when on) also stamps lines written with the file tools or a shell command that names `LANES.md`. Never write a time from memory, and run `astack-stamp <LANES.md>` on any line that has none: `astack-status` does not count unstamped lines. Query past choices with `astack-decisions` before revisiting them. Record any `RULES.md` change as `rules rev:` and notify active workers.

## Decisions

- Settle technical choices with **research-this**, **analyze-environment**, **play-with-me**, or **ab-test**, and log each as `decided:` with evidence.
- **Honor `autonomy` without extra pauses:** read-only and dry-run probes are always allowed. Under `unattended`, execute every action in `autonomy.allow` without asking confirmation.
- Check `astack-decisions`, the repo, docs, and `TOOLS.md` before escalating.
- Escalate only genuine human-only steps (interactive login/SSO/MFA after cataloging the tool in `TOOLS.md`, `sudo`, spending money), unavoidable functionality trade-offs, or actions in `autonomy.deny`.
- Ask outright, as a plain choice with your pick (**decisions-in-plain-words**), using `AskUserQuestion`, and keep working on everything else.
- Never ask for confirmation, re-ask prior approval, or ask about retries, flakes, merge mechanics, or whether to keep going.
- Log the person's answers verbatim and forward them to affected agents.

## Report

Write plainly, losses first (**wat**): proven issues and contradictions with concrete actions, what didn't land and why, verified SHAs that landed, DAG status, key decisions with evidence and the skills that shaped them, relevant Mermaid state/architecture diagrams (**show-the-states**, also placed in PRs and repo docs), and genuine human calls.

Never leak internal astack state into user replies or `"Open Items"` (no single-model reviewer pool, `reviewer_pool` size, `settings.json` defaults, pool-exhaustion labels, coverage-map paths, model rosters, worktree paths, or estimator formulas). If a risky change hasn't converged, frame it strictly as code risk: proven bugs found, likely remaining bugs with range, and the choice to approve deeper verification or accept the risk. Audit any human-facing PR comment via **leave-feedback** before posting. Name any skipped step (`plan reviewed`, check-ins, `verified`, `ledger`, `rules rev`, closing `lookback`) as a loss.

Referenced skills: `go` (`${CLAUDE_SKILL_DIR}/../go/SKILL.md`), `whatsup` (`${CLAUDE_SKILL_DIR}/../whatsup/SKILL.md`), `dagify` (`${CLAUDE_SKILL_DIR}/../dagify/SKILL.md`), `treeify` (`${CLAUDE_SKILL_DIR}/../treeify/SKILL.md`), `decisions-in-plain-words` (`${CLAUDE_SKILL_DIR}/../decisions-in-plain-words/SKILL.md`), `slates` (`${CLAUDE_SKILL_DIR}/../slates/SKILL.md`), `analyze-environment` (`${CLAUDE_SKILL_DIR}/../analyze-environment/SKILL.md`), `cross-repo` (`${CLAUDE_SKILL_DIR}/../cross-repo/SKILL.md`), `workflow-this` (`${CLAUDE_SKILL_DIR}/../workflow-this/SKILL.md`), `track-it` (`${CLAUDE_SKILL_DIR}/../track-it/SKILL.md`), `review` (`${CLAUDE_SKILL_DIR}/../review/SKILL.md`), `prove-it` (`${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`), `watch-pr` (`${CLAUDE_SKILL_DIR}/../watch-pr/SKILL.md`), `blast-radius` (`${CLAUDE_SKILL_DIR}/../blast-radius/SKILL.md`), `technical-writing` (`${CLAUDE_SKILL_DIR}/../technical-writing/SKILL.md`), `no-leaked-secrets` (`${CLAUDE_SKILL_DIR}/../no-leaked-secrets/SKILL.md`), `cleanup` (`${CLAUDE_SKILL_DIR}/../cleanup/SKILL.md`), `bugbash` (`${CLAUDE_SKILL_DIR}/../bugbash/SKILL.md`), `redteam` (`${CLAUDE_SKILL_DIR}/../redteam/SKILL.md`), `sprint` (`${CLAUDE_SKILL_DIR}/../sprint/SKILL.md`), `squish` (`${CLAUDE_SKILL_DIR}/../squish/SKILL.md`), `lookback` (`${CLAUDE_SKILL_DIR}/../lookback/SKILL.md`), `make-it-stick` (`${CLAUDE_SKILL_DIR}/../make-it-stick/SKILL.md`), `research-this` (`${CLAUDE_SKILL_DIR}/../research-this/SKILL.md`), `play-with-me` (`${CLAUDE_SKILL_DIR}/../play-with-me/SKILL.md`), `ab-test` (`${CLAUDE_SKILL_DIR}/../ab-test/SKILL.md`), `wat` (`${CLAUDE_SKILL_DIR}/../wat/SKILL.md`), `show-the-states` (`${CLAUDE_SKILL_DIR}/../show-the-states/SKILL.md`), `leave-feedback` (`${CLAUDE_SKILL_DIR}/../leave-feedback/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's Orchestrate, autopilot-full, and figure-it-out playbooks and poteto-mode Subagents section (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
