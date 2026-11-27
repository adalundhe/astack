---
name: cleanup
description: "Remove temp files, debug captures, scratch workspaces, and jobs you created while sparing others' state. Use post-review, at handoff, or after debugging."
---

# Cleanup

Remove temporary artifacts you created without touching anything else. Leftover files and processes pollute diffs and leak stale state into later runs.

## When to invoke

- **Post-review (mandatory):** run after `review` clears. Tear down review worktrees, scratch workspaces, ephemeral **slates** volumes (`slates unmount` + `slates volume destroy`), superseded repros (preserve PR proof), and stray processes. Keep durable program records.
- **During and right after debugging:** prune stale captures mid-session during `find-it`. Delete every `<file>_DEBUG_<shorthash>.<type>` file and temporary debug hook once fixed.
- **At handoff or after experiments:** clear throwaway prototypes, benchmark temp data, and background jobs you started.

## Steps

1. **Inventory what you created:** list `<file>_DEBUG_<shorthash>.<type>` captures, debug hooks, temp dirs, build outputs, caches, test DBs, and containers. Include background PIDs, dangling `astack-dispatch` runs, finished worktrees, and merged branches.
2. **Keep what is still needed:** preserve durable `~/.astack/<project>/` records (`lessons/`, `architecture/`, `research/`, `docs/`, `reviews/`, `repros/`, `automations/`, `logging/`) and program records (`RULES.md`, `LANES.md`, coverage maps, watch markers). Keep requested artifacts and standard project caches.
3. **Remove only verified leftovers:** confirm each item is untracked, unreferenced, and unused by any live process. Revert temporary instrumentation. Never touch other people's or other agents' files or processes.
4. **Clean safely inside your writable workspace:** run project clean commands (`make clean`, test teardown) first. Stop leftover cross-harness runs with `astack-dispatch kill --all`. Delete remaining items by exact path or PID—never broad globs or `pkill`, because they destroy parallel lanes.
5. **Verify cleanup:** confirm `git status` is clean of `*_DEBUG_*.*` or sensitive captures (**no-leaked-secrets**). Verify builds and tests still pass.

**Done when:** `git status` is clean of temporary captures, builds and tests pass, and your reply lists what you removed and kept.

Referenced skills: `slates` (`../slates/SKILL.md`), `no-leaked-secrets` (`../no-leaked-secrets/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's create-verification-skill (stop only what you started, never by process name; evidence survives cleanup) (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
