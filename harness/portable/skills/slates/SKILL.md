---
name: slates
description: "Provision, mount, snapshot, clone, merge, and clean up isolated Slates VFS workspaces. Use for worker lanes, variants, or read-only checks."
disable-model-invocation: true
---

# Slates VFS volumes

[Slates](https://github.com/hyper-light/slates) creates RAM-backed copy-on-write virtual filesystem (VFS) overlays over a repo (`--base <repo>`) in microseconds. Normal tools (`git`, compilers, test runners) read untouched files from disk while edits stay isolated in memory. Concurrent edits merge by exact byte-range deltas.

Normal `git push` works from inside a mounted volume to remote branches. Syncing dirty volume files back to the local base checkout requires `slates land` plus a human `slates grant`.

## Detection and fallback

Prefer a Slates volume when available. Fall back immediately to `git worktree` when it is not, because workspace tooling should never block work.

1. **Check availability:**
   - **CLI / daemon:** `slates` is in `PATH` and `slates status` exits `0` (exit `3` means no daemon is running).
   - **MCP / SDK:** Slates MCP tools (`slates.status`, `slates.volume.*`, `slates.merge.*`) are attached.
2. **Fall back cleanly:** if `slates` is missing, `slates status` fails, or mounting fails, use `git worktree add <path> -b <branch>`. Use `--detach` for throwaway reviewer checks. Never block waiting for Slates to be installed unless asked.

## Core workflows

### 1. Overlay volume (worker lane or reviewer check)

```sh
slates volume create <name> --dynamic 4GiB --base <repo_path>   # or --bounded <size>
mkdir -p <mount_dir>
slates mount <volume_id> <mount_dir>                            # macOS NFS, Linux FUSE, Windows WinFsp
slates status <volume_id> --drift                               # check if base files changed on disk
```

If `--drift` flags changed base files, commit or patch your edits and recreate the overlay from the updated base so changes never merge against stale files.

- **Workers:** build lanes, fixes, prototypes, and structural guards inside the mounted volume without touching the shared checkout. Push a branch or resubmit to reviewers.
- **Reviewers:** inspect code read-only and run repros or stress tests on submitted volumes—never writing or applying fixes themselves.

### 2. Snapshots and clones (variants & prototypes)

Snapshots record a version without copying bytes. Clones branch copy-on-write in microseconds—ideal for `ab-test`, `swarm-hypothesis`, and `bugbash` prototypes:

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

Collisions return exact byte ranges (`path`, `at`, `len`) instead of conflict markers, so agents never overwrite each other.

### 4. Human-gated landing to disk

```sh
slates land <volume_id> <target_dir>     # previews manifest and prints: grant with: slates grant <n>
```

Agents cannot grant local disk writes (`grant_required: true`). Only the person runs `slates grant <n>`. To ship via git instead, push verified commits from inside the mount to a feature branch and open a PR.

### 5. Cleanup (**cleanup**)

Tear down finished or ephemeral volumes when done, and verify none remain with `slates volume list`:

```sh
slates unmount <mount_dir>
slates volume destroy <volume_id>
```

**Done when:** verified work is pushed or landed via human `slates grant`, and `slates volume list` shows zero leftover scratch volumes.

Referenced skills: `cleanup` (`../cleanup/SKILL.md`). Read any cited skill file before acting when its trigger applies.
