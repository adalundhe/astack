---
name: test-drive
description: "Create or update a project-local drive-<app> skill that launches the real app, exercises user flows, and captures proof (screenshots, transcripts, logs). Use to verify real user behavior or fix a stale drive skill."
disable-model-invocation: true
---

# Test drive

Verify behavior by driving the real application the way users do, captured as a repeatable recipe any agent can run cold.

Check for an existing project drive skill (`drive-<app>` or equivalent). If none exists, create it; if one exists, keep it accurate.

## Create

1. **Inspect the repo first; ask the person only what you can't observe:**
   - **Surface:** web UI, CLI/TUI, desktop/mobile app, HTTP API, or library.
   - **Startup:** documented build/run commands, ports, env vars, seed data, auth.
   - **Target environment:** local development whenever possible, otherwise only an environment the person explicitly approved (document what's allowed there).
   - **Driver:** repo's own harnesses first; otherwise browser debugging protocol (web/Electron), PTY/tmux (CLI/TUI), or HTTP client (services).
   - **Evidence:** screenshots, transcripts, response bodies, logs, exit codes, persisted state.
   - **Isolation:** confirm whether multiple instances can run side by side.

   If the app fails to build or boot, fix that first in a separate change or report the exact failure.
2. **Write the `drive-<app>` skill** in the project's skills folder (front matter naming app, surface, and trigger) with zero placeholders:
   - **Launch:** exact command from an empty data directory through migrations and seeding, plus how to confirm it's genuinely ready (not merely accepting TCP connections). For short-lived CLIs, build once and give each run a fresh session.
   - **Doctor:** one read-only preflight check confirming our process, build, port, and auth are healthy. Run before driving and whenever behavior looks odd.
   - **Drive:** real commands and resilient selectors (labels, `data-*` attributes, prompts, routes) rather than fragile pixel coordinates.
   - **Evidence:** what to save and where. Exercise the real user path instead of internal setters or test-only shortcuts. Capture both the action and resulting state, plus side effects (files, DB rows, emitted messages). Mock only where production isolates an external dependency, and note anything a dry run skips.
   - **Cleanup:** stop only processes you started (never `killall` by generic name) while keeping captured evidence intact.
   - **Helpers:** executable scripts with exact invocation examples.
   - **Last proven at:** commit SHA of the last full end-to-end run.
3. **Map features:** write an index plus one file per user-facing feature (most critical first) describing what it does, how to navigate there, steps to exercise it, expected end state, and gotchas. If seed data can't support a journey, fail and document why under gotchas—never weaken a journey to pass.
4. **Prove it cold:** follow the skill verbatim once (launch -> doctor -> drive a feature -> capture -> cleanup) and confirm evidence survived and cleanup works even after failed runs. If you had to test against a stand-in target, document every difference from the real target.

## Keep it true

Run when the app changed since **Last proven at**, a drive step fails, or someone asks. Edit only the drive skill, feature map, and helpers—never product code.

1. **Clean up the index:** fix missing, stale, duplicate, or dead entries.
2. **Audit each feature against source** (parallel read-only subagents): verify current user flow, note drift with `file:line` citations, update drive steps, and add newly discovered features.
3. **Drive every feature live** even when source looks unchanged. Run doctor before the first drive and after any failure (reset/relaunch if doctor misses an issue). Confirm evidence survives cleanup and no spawned process lingers. Mark unreachable features with their missing prerequisite and route attempted.
4. **Classify findings:** wrong map -> update map; working app with broken automation -> fix helper and re-drive; broken app -> report the bug separately without editing product code.
5. **Ship verified updates** in one change and advance **Last proven at** (or report clean / what blocked verification).

<!-- Adapts pstack's create-verification-skill and maintain-verification-skill skills (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
