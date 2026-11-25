---
name: astack-status
description: "Show an astack program's active agents, timers, latest commits, lane states, and open questions. Use for $astack-status or progress checks."
---

# Status

Run `astack-status` from `PATH` (linked into `~/.local/bin` by `$astack-setup`) or from astack's bundled `bin/astack-status`.

## Log lookup and flags

- With no path argument, `astack-status` reads `./LANES.md` first. Otherwise it opens the newest `LANES.md` under `~/.cache/astack/`.
- Pass a program folder or `LANES.md` path to inspect another program, or `--repo DIR` to override the git checkout.
- Use `astack-status --line` for a one-line status-bar summary.
- If `astack-status` exits `1` (`No astack lane log found.`), report that no active program log exists rather than inventing status.

## Reporting output

Show the command output verbatim so clocks and commit SHAs stay exact. Then add one plain line flagging anything needing attention:

- any worker, reviewer, researcher, or cross-harness dispatch past its time limit (`PAST by ...`) or stalled;
- any open question under `Waiting on the person`;
- any unstamped-line warning (fix with `astack-stamp <LANES.md>` so those entries are counted).

**Reply:** verbatim `astack-status` output followed by one plain attention line (or `All lanes on track.`).
