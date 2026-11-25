---
name: test-drive
description: "Create or maintain a project-local drive-<app> skill that runs the real app and captures proof. Use to verify user flows or fix a stale drive skill."
disable-model-invocation: true
---

# Test drive

Verify behavior by driving the real application like a user. Capture the steps as a repeatable recipe any agent can run cold.

**Skip for pure libraries:** if the project has no runnable UI, CLI, TUI, or service surface, skip `test-drive` and test via `full-spectrum-testing` instead.

Check for an existing project drive skill (`drive-<app>` or equivalent). Create one if missing; keep it true if present.

## Create

1. **Inspect the repo first; ask only what you cannot observe:**
   - **Surface:** web UI, CLI/TUI, desktop/mobile app, or HTTP API.
   - **Startup:** documented build/run commands, ports, env vars, seed data, and auth.
   - **Target environment:** use local dev whenever possible. Otherwise use only a human-approved environment and document its rules.
   - **Driver:** use repo harnesses first. Otherwise use browser debugging protocol (web/Electron), PTY/tmux (CLI/TUI), or HTTP clients (services).
   - **Evidence:** screenshots, transcripts, response bodies, logs, exit codes, and persisted state.
   - **Isolation:** confirm whether multiple instances can run side by side.

   If the app fails to build or boot, fix that in a separate change or report the exact failure.
2. **Write `drive-<app>/SKILL.md`** in the project's skills folder (default `.agents/skills/drive-<app>/SKILL.md` if none exists). Include front matter naming the app, surface, and trigger, with zero placeholders:
   - **Launch:** give the exact command from an empty data directory through migrations and seeding. Document how to confirm true readiness, not just an open TCP port. For short-lived CLIs, build once and give each run a fresh session.
   - **Doctor:** add one read-only preflight check confirming process, build, port, and auth health. Run it before driving and whenever behavior looks odd.
   - **Drive:** use real commands and resilient selectors (labels, `data-*` attributes, prompts, routes) instead of fragile pixel coordinates.
   - **Evidence:** name what to save and where. Exercise the real user path instead of internal setters or test shortcuts. Capture the action, resulting state, and side effects (files, DB rows, emitted messages). Mock only external dependencies that production isolates, and note anything a dry run skips.
   - **Cleanup:** stop only processes you started (never `killall` by generic name) while keeping captured evidence intact.
   - **Helpers:** ship executable scripts with exact invocation examples.
   - **Last proven at:** record the commit SHA of the last full end-to-end run.
3. **Map features:** write an index plus one file per user-facing feature, most critical first. Cover what it does, navigation, steps, expected end state, and gotchas. If seed data blocks a journey, fail and record why under gotchas—never weaken a journey to pass.
4. **Prove it cold:** follow the skill verbatim once (launch -> doctor -> drive -> capture -> cleanup). Confirm evidence survives and cleanup works even after a failed run. Document any stand-in target differences explicitly.

## Keep it true

Run when the app changed since **Last proven at**, a step fails, or someone asks. Edit only the drive skill, feature map, and helpers—never product code.

1. **Clean up the index:** fix missing, stale, duplicate, or dead entries.
2. **Audit each feature against source:** Lead may dispatch parallel read-only `astack:researcher` subagents; Workers and Reviewers audit sequentially. Verify each flow, note drift with `file:line` citations, update drive steps, and add new features.
3. **Drive every feature live** even when source looks unchanged. Run doctor before the first drive and after any failure; relaunch if doctor misses an issue. Confirm evidence survives cleanup and no process lingers. Mark unreachable features with their missing prerequisite and route attempted.
4. **Classify findings:** wrong map -> update map; broken automation on a working app -> fix helper and re-drive; broken app -> report the bug separately without editing product code.
5. **Ship verified updates** in one change and advance **Last proven at**.

**Reply:** state the drive-skill path, features verified live, `Last proven at` SHA, captured proof paths, and any broken-app bugs or unreachable features.

<!-- Adapts pstack's create-verification-skill and maintain-verification-skill skills (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
