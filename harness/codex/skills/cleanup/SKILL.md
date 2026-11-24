---
name: cleanup
description: "Remove the temporary files, build artifacts, caches, test data and other leftovers your work created, without touching anything you didn't create or that's still needed. Use when finishing a task, before handing work off, after tests or experiments, and when a checkout or disk is cluttered."
---

# Cleanup

Remove what your work left behind: temporary files, build artifacts, caches, test state and output, scratch data.

1. **List what you created:** temp files and folders, build output, caches, test databases and tables, containers and volumes, processes and ports, downloaded files, worktrees you've finished with, and branches that are merged.
2. **Keep what's still needed:** evidence you'll report (logs, screenshots, benchmark results), the program's records (rules, logs, reports), anything the person or another agent asked to keep, anything still in use, and the caches the project's own tools expect.
3. **Remove only what you made, or can show is unneeded:** version control doesn't track it, nothing references it, and no running process holds it. Leave other people's and other agents' files, data and processes alone.
4. **Use the project's own clean commands first,** such as `make clean`, the build tool's clean, or the test framework's teardown. Remove the rest by exact path or name, never by a broad pattern or a process name.
5. **Check it worked:** none of your leftovers show in `git status`, the space came back, and the build and tests still run.
6. **Report what you removed and what you kept.**

<!-- Adapts pstack's create-verification-skill (stop only what you started, never by process name; evidence survives cleanup) (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
