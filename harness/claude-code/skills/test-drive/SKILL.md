---
name: test-drive
description: "Give the project a scripted way to use the real app as its users do and capture proof, and keep it true as the app changes. Use to prove or review behaviour from the users' side, or when the project's drive skill is missing, failing or stale."
---

# Test drive

Prove behaviour by using the real app as its users do, from a recipe any agent can follow cold.

Find the project's drive skill: `drive-<app>`, or any project skill that launches and drives the app. None: create it. One: keep it true.

## Create

1. **Read the repo; ask the person only what you can't observe.**
   - **Surface:** what users touch: web UI, CLI or TUI, desktop or mobile app, API, library.
   - **Run:** the repo's documented start command, ports, environment, seed data, sign-in.
   - **Where:** local development wherever possible; otherwise only an environment the person approved, named in the skill with what's allowed there.
   - **Drive:** the repo's own harnesses first; then a browser over its debugging protocol for web and Electron, a PTY or terminal multiplexer for CLIs and TUIs, HTTP for services.
   - **Observe:** screenshots, transcripts, response bodies, logs, exit codes, stored state.
   - **Isolate:** can two instances run side by side?

   If it doesn't build or start, fix that first in its own change, or report exactly what fails.
2. **Write the drive skill** in your tool's project skills folder, its front matter naming the app, the surface and when to use it. No placeholders:
   - **Launch:** the exact command from an empty data folder, through migrations and seed data, and how to tell it's usable, not merely answering. A short-lived CLI is built once, then each drive gets a fresh session.
   - **Doctor:** one read-only check that this instance is worth driving: our process, the right build, our port, a valid sign-in. Run it first, and whenever something looks off.
   - **Drive:** the repo's real commands and selectors, by stable handles (labels, data attributes, prompts, routes) rather than coordinates, which break when the layout moves.
   - **Evidence:** what to capture and where. Use the real user path rather than internal setters or test-only endpoints, which skip what users go through. Capture the action and the resulting state, and check side effects: files, rows, messages. Mock only where production already isolates a system. Watch what a dry run actually skips.
   - **Cleanup:** stop only what you started, never by process name. Evidence survives.
   - **Helpers:** executable, with their invocation shown.
   - **Last proven at:** the commit it last ran end to end on.
3. **Map the features:** an index and one file per user-facing feature, most relied on first. Each gives, from the user's side, what it is, how to reach it, how to drive it, the end state that proves it works, and gotchas. A journey the seed data can't support fails, with the reason under gotchas. Never weaken a journey to pass.
4. **Prove it:** follow it end to end once, cold: launch, doctor, drive one feature, capture, clean up, then confirm the evidence survived. Clean up after failed attempts too. If you proved it on a stand-in for the real target, list what the stand-in did that the target won't.

## Keep it true

When the app has changed since **Last proven at**, a drive fails on the skill's own steps, or someone asks. Edit only the drive skill, its map and its helpers, never product code.

1. **Fix the index:** missing, extra, duplicate and dead entries.
2. **Read each feature from source,** one read-only subagent per feature, in parallel: how users meet it, drift with citations, one recipe to drive it. Add missing features, citing the source that shows them.
3. **Drive every feature live,** even when the source looks clean. Doctor before the first drive and after any failure; when doctor can't see the problem, reset or relaunch. Evidence survives every cleanup, and nothing a drive started outlives it. Mark an unreachable feature with its missing prerequisite and the route tried.
4. **Sort the findings.** The map is wrong: fix the map. The app works but can't be driven: fix the helper and drive again. The app is broken: report the bug, and keep it out of this change.
5. **Ship one change of proven corrections** and move **Last proven at**, or report it clean, or what blocked it.

<!-- Adapts pstack's create-verification-skill and maintain-verification-skill skills (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
