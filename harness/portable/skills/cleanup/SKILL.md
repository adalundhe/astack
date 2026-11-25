---
name: cleanup
description: "Remove temporary files, debug logs/captures (<file>_DEBUG_<shorthash>.<type>), build artifacts, caches, test data, and processes created by your work without touching anything else or still needed. Always invoke post-review, when finishing/handing off, and during or right after debugging."
disable-model-invocation: true
---

# Cleanup

Remove artifacts left behind by your work—temp files, debug logs/data, build outputs, caches, scratch worktrees, test state, and leftover processes—without touching anything you didn't create.

## When to invoke

- **Post-review (mandatory):** run after **review** finishes (before declaring work done or a PR merge-ready) to clear review scratch worktrees, stray repo-side repros, audit drafts, and leftover processes while preserving program records.
- **During debugging and right after a fix:** invoke during active **find-it** / **diagnose** sessions to prune stale debug logs, captures, traces, and profiles—and always once the issue is fixed so every `<file>_DEBUG_<shorthash>.<type>` file and temporary debug print/instrumentation is removed.
- **At handoff or after experiments:** clear throwaway prototypes, benchmark temp data, and background jobs you started.

## Steps

1. **Inventory what you created:** `<file>_DEBUG_<shorthash>.<type>` captures and debug logs, temporary print/trace instrumentation, temp files/directories, build artifacts, caches, test databases/tables, containers/volumes, background processes/ports, downloaded files, finished git worktrees, and merged branches.
2. **Keep what's still needed:** evidence for your report (final test output, screenshots, benchmark results), program records (`RULES.md`, `LANES.md`, coverage maps, watch markers, reports), anything explicitly requested to stay, anything still in use, and standard project tool caches.
3. **Remove only verified leftovers:** confirm each item is untracked by git, unreferenced, and not held by a running process (and revert temporary debug instrumentation cleanly). Leave other people's and other agents' files, data, and processes untouched.
4. **Use project clean commands first** (`make clean`, build-tool clean, test teardown). Delete remaining leftovers by exact path or PID—never with broad globs or generic process names.
5. **Verify cleanup:** confirm no leftovers or `*_DEBUG_*.*` files remain in `git status`, no sensitive captures were left behind (**no-leaked-secrets**), disk space is reclaimed, and builds/tests still run cleanly.
6. **Report** concisely what you removed and what you intentionally kept.

Referenced skills: `review` (`../astack-review/SKILL.md`), `find-it` (`../find-it/SKILL.md`), `diagnose` (`../diagnose/SKILL.md`), `no-leaked-secrets` (`../no-leaked-secrets/SKILL.md`). Read any cited skill file before acting when its trigger applies.

<!-- Adapts pstack's create-verification-skill (stop only what you started, never by process name; evidence survives cleanup) (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
