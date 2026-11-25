---
name: slates
description: "Provision, mount, snapshot, clone, merge, land, and clean up isolated in-memory VFS workspaces using Slates (https://github.com/hyper-light/slates)—preferred over git worktrees when available for workers, variants, and read-only reviewer verification."
disable-model-invocation: true
---

# Slates VFS volumes

[Slates](https://github.com/hyper-light/slates) provides RAM-backed copy-on-write virtual filesystem (VFS) overlays over a repository (`--base <repo>`) in microseconds. Normal tools (`git`, compilers, test runners) read untouched files from disk while edits stay isolated in memory. Concurrent edits merge by exact byte-range deltas, and nothing touches real disk until planned with `slates land` and approved by a human `slates grant`.

## Detection and fallback

Prefer a Slates volume when available; fall back immediately to `git worktree` when it is not, because workspace tooling should never block work.

1. **Check availability:**
   - **CLI / daemon:** `slates` is on `PATH` and `slates status` exits `0` (exit `3` means no daemon is running).
   - **MCP / SDK:** Slates MCP tools (`slates.status`, `slates.volume.*`, `slates.merge.*`) are attached.
2. **Fall back cleanly:** if `slates` is absent, `slates status` fails, or mounting is unavailable, use `git worktree add <path> -b <branch>` (or `--detach` for throwaway reviewer checks). Never block waiting for Slates to be installed unless asked.

## Core workflows

### 1. Overlay volume (worker lane or reviewer check)

```sh
slates volume create <name> --dynamic 4GiB --base <repo_path>   # or --bounded <size>
mkdir -p <mount_dir>
slates mount <volume_id> <mount_dir>                            # macOS NFS, Linux FUSE, Windows WinFsp
slates status <volume_id> --drift                               # check if base files changed on disk
```

- **Workers:** implement lanes, fixes, prototypes, and structural guards inside their mounted volume without touching the shared checkout, then resubmit to reviewers.
- **Reviewers:** inspect code read-only and run repros or stress tests on submitted volumes—never writing or applying fixes themselves.

### 2. Snapshots and clones (variants & prototypes)

Snapshots record a version without copying bytes, and clones branch copy-on-write in microseconds—ideal for **ab-test**, **swarm-hypothesis**, and competing prototypes in **bugbash**:

```sh
slates volume snapshot <volume_id>
slates volume clone <volume_id> <snapshot_num> <clone_name>
```

### 3. Deterministic concurrent merge (`green` + `work`)

Share one **green** target volume and give each concurrent worker its own **work** volume:

```sh
slates green <name>                      # shared target volume
slates work <green_id> <lane_name>       # isolated worker volume
slates rebase <work_id>                  # rebase onto current green head
slates submit <work_id> --json           # accepted version, already-there, or exact byte-range conflicts
```

Collisions return exact byte ranges (`path`, `at`, `len`) rather than conflict markers, so agents never overwrite each other.

### 4. Human-gated landing to disk

```sh
slates land <volume_id> <target_dir>     # previews manifest and prints: grant with: slates grant <n>
```

Agents cannot grant disk writes (`grant_required: true`). Only the person runs `slates grant <n>` (or the lead lands verified commits through normal git branches and PRs).

### 5. Cleanup (**cleanup**)

Always tear down finished or ephemeral volumes when done, and confirm none remain with `slates volume list`:

```sh
slates unmount <mount_dir>
slates volume destroy <volume_id>
```
