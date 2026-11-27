---
type: llm
---

Evaluate the workspace provisioning against `slates`.

PASS if all of these hold:
- Checks environment availability for Slates and falls back immediately to `git worktree` without blocking when Slates is unavailable.
- Provisions two isolated, clean git worktrees strictly outside `./repo` on distinct branches `lane/auth` and `lane/billing`.
- Keeps `./repo` clean and checked out on `main`.
- Records the accurate lane branches, worktree paths, and fallback backend in `program/workspaces.json`.

FAIL otherwise.
