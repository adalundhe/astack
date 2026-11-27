---
description: "Atomic outcome eval for slates: checks workspace isolation tooling, falls back to isolated git worktrees outside ./repo for lane/auth and lane/billing on distinct branches while keeping ./repo clean on main, and records their paths in program/workspaces.json."
expected_outcome: "Reads slates/SKILL.md, checks environment availability, provisions two clean git worktrees outside ./repo on branches lane/auth and lane/billing while leaving ./repo clean on main, and writes their paths and branches to program/workspaces.json."
timeout_seconds: 360
---

`/astack:go` We need two isolated lane workspaces (`lane/auth` and `lane/billing`) provisioned from `./repo` as described in `program/lanes.md`. Check the environment for available workspace isolation tooling and fall back to git worktrees when unavailable so work is never blocked. Place the two workspaces outside `./repo` (for example under `program/worktrees/`), keep `./repo` clean on `main`, and record each lane's branch, path, and backend in `program/workspaces.json`.
