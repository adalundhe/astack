---
name: slates
description: "Provision, mount, snapshot, clone, merge, land, and clean up isolated in-memory VFS workspaces using Slates (https://github.com/hyper-light/slates)—preferred over git worktrees when available for concurrent worker implementation lanes, parallel variants, and throwaway reviewer scratch tests. Use whenever isolating agent workspaces or checking whether Slates is available."
---

# Slates VFS volumes

[Slates](https://github.com/hyper-light/slates) is an in-memory copy-on-write virtual filesystem (VFS) workspace manager for concurrent coding agents. Instead of duplicating repository checkouts on disk, Slates gives each agent a RAM-backed overlay volume over the repository (`--base <repo>`) in microseconds: normal directory tools (`git`, compilers, test runners) read untouched files from disk while edits stay isolated in memory, and concurrent agent edits merge deterministically by exact byte-range deltas rather than guessing conflict markers. Nothing touches real disk until planned with `slates land` and approved by a human grant (`slates grant`).

## Detection and fallback (required)

Always prefer a Slates VFS volume when available, and fall back seamlessly to an isolated **git worktree** when it is not:

1. **Check availability:**
   - **CLI / daemon:** `slates` is on `PATH` **and** a daemon (`slates anchor`) is reachable (`slates status` exits `0`; exit `3` means no daemon is running).
   - **MCP / SDK:** Slates MCP tools (`slates.status`, `slates.volume.*`, `slates.merge.*`) are available in the active session (started via `slates mcp [--http PORT]`).
2. **Use Slates when reachable; otherwise use `git worktree`:** if `slates` is not installed, `slates status` returns non-zero (no daemon), or host mounting is unavailable, fall back immediately to `git worktree add <path> -b <branch>` (or `git worktree add --detach` for throwaway reviewer scratch checks). Never block work waiting for Slates to be installed unless explicitly requested.

## Core workflows

### 1. Isolated worker workspace or throwaway reviewer scratch test (overlay volume)

Create an in-memory overlay over the repository so untouched files read from disk while all writes stay isolated in RAM:

```sh
slates volume create <name> --dynamic 4GiB --base <repo_path>   # or --bounded <size>
mkdir -p <mount_dir>
slates mount <volume_id> <mount_dir>                            # macOS loopback NFS, Linux FUSE, Windows WinFsp
slates status <volume_id> --drift                               # check if base files changed on disk
```

- **Workers** (`lead`, `dagify`, `bugbash`, `modularize`, `watch-pr`): implement and test inside their mounted volume (or `work` volume below) without touching the shared checkout or another lane.
- **Reviewers** (`review`, `adversarial-review`, `bugbash`): inspect the repo read-only and test reproductions, candidate fixes, or fix-equivalence checks inside a throwaway overlay/clone volume—never mutating the code under review.

### 2. Microsecond snapshots and clones (variants & competing fixes)

Snapshots record a version number without copying bytes; clones branch off a snapshot copy-on-write in microseconds—ideal for **ab-test**, **swarm-hypothesis**, and testing competing fix approaches in **bugbash**:

```sh
slates volume snapshot <volume_id>
slates volume clone <volume_id> <snapshot_num> <clone_name>
```

### 3. Deterministic concurrent merge (`green` + `work` volumes)

When multiple workers edit one codebase concurrently, share a **green** volume and give each worker its own **work** volume:

```sh
slates green <name>                      # create shared green target volume
slates work <green_id> <lane_name>       # create isolated work volume from green
slates rebase <work_id>                  # rebase work volume onto current green head
slates submit <work_id> --json           # returns accepted version, already-there, or exact byte-range conflicts
```

Collisions come back as exact file byte ranges (`path`, `at`, `len`) rather than conflict markers—never overwriting another agent's change.

### 4. Human-gated landing to disk (R10)

Nothing in Slates writes to real disk until explicitly landed in two steps:

```sh
slates land <volume_id> <target_dir>     # previews manifest and outputs: grant with: slates grant <n>
```

Agents **cannot** grant disk writes (`slates.land.materialize` returns `grant_required: true`; neither MCP nor the Python/Node SDKs expose `grant`). Only the person runs `slates grant <n>` (or the lead lands verified git commits via standard git branches/PRs when using mounted git repos).

### 5. Cleanup (**cleanup**)

Always tear down ephemeral reviewer scratch volumes and finished worker volumes when done:

```sh
slates unmount <mount_dir>
slates volume destroy <volume_id>
```

Verify with `slates volume list` that no stale scratch volumes remain.

Referenced skills: `ab-test` (`../ab-test/SKILL.md`), `swarm-hypothesis` (`../swarm-hypothesis/SKILL.md`), `bugbash` (`../bugbash/SKILL.md`), `cleanup` (`../cleanup/SKILL.md`). Read any cited skill file before acting when its trigger applies.
