---
name: cleanup
description: "Remove temporary files, debug logs/captures (<file>_DEBUG_<shorthash>.<type>), build artifacts, caches, scratch workspaces, and processes you created without touching anything else. Run post-review, at handoff, and right after debugging."
disable-model-invocation: true
---

# Cleanup

Remove temporary artifacts created by your work without touching anything you did not create, because leftover files and processes pollute diffs and leak stale state into later runs.

## When to invoke

- **Post-review (mandatory):** run after **review** clears to tear down review worktrees, scratch workspaces, ephemeral **slates** volumes (`slates unmount` + `slates volume destroy`), stray repros, and leftover processes. Keep durable program records.
- **During and right after debugging:** prune stale captures mid-session during **find-it**, and delete every `<file>_DEBUG_<shorthash>.<type>` file and temporary debug hook once fixed.
- **At handoff or after experiments:** clear throwaway prototypes, benchmark temp data, and background jobs you started.

## Steps

1. **Inventory what you created:** `<file>_DEBUG_<shorthash>.<type>` captures, temporary debug hooks, temp directories, build outputs, caches, test DBs, containers, background PIDs, finished worktrees, and merged branches.
2. **Keep what is still needed:** report evidence (final test output, screenshots, benchmarks), program records (`RULES.md`, `LANES.md`, coverage maps, watch markers, reports), requested artifacts, and standard project caches.
3. **Remove only verified leftovers:** confirm each item is untracked, unreferenced, and not held by a live process, and revert temporary instrumentation. Never touch other people's or other agents' files or processes.
4. **Use project clean commands first** (`make clean`, test teardown). Delete remaining items by exact path or PID—never broad globs or process names.
5. **Verify cleanup:** confirm `git status` is clean of `*_DEBUG_*.*` or sensitive captures (**no-leaked-secrets**), and verify builds and tests still pass.
6. **Report** concisely what you removed and what you intentionally kept.

Referenced skills: `review` (`../astack-review/SKILL.md`), `slates` (`../slates/SKILL.md`), `find-it` (`../find-it/SKILL.md`), `no-leaked-secrets` (`../no-leaked-secrets/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's create-verification-skill (stop only what you started, never by process name; evidence survives cleanup) (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
