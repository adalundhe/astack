---
name: cleanup
description: "Remove temporary files, build artifacts, caches, test data, and processes created by your work without touching anything else or still needed. Use when finishing a task, handing off, or after experiments."
disable-model-invocation: true
---

# Cleanup

Clean up artifacts left behind by your work—temp files, build outputs, caches, scratch data, test state, and leftover processes—without touching anything you didn't create.

1. **Inventory what you created:** temp files/directories, build artifacts, caches, test databases/tables, containers/volumes, background processes/ports, downloaded files, finished git worktrees, and merged branches.
2. **Keep what's still needed:** evidence for your report (logs, screenshots, benchmark results), program records (`RULES.md`, `LANES.md`, reports), anything explicitly requested to stay, anything still in use, and standard project tool caches.
3. **Remove only verified leftovers:** confirm the item is untracked by git, unreferenced, and not held by a running process. Leave other people's and other agents' files, data, and processes untouched.
4. **Use project clean commands first** (`make clean`, build-tool clean, test teardown). Delete remaining leftovers by exact path or PID—never with broad globs or generic process names.
5. **Verify cleanup:** confirm your leftovers are gone from `git status`, disk space is reclaimed, and builds/tests still run cleanly.
6. **Report** concisely what you removed and what you intentionally kept.

<!-- Adapts pstack's create-verification-skill (stop only what you started, never by process name; evidence survives cleanup) (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
