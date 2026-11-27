---
description: "In Go mode, fixing a swallowed-exception profile loader in ./repo routes to no-hidden-flow-control, replaces the catch-all with narrow catches and typed error values, and tests every failure path."
expected_outcome: "Reads no-hidden-flow-control/SKILL.md, removes `except Exception: return None` in ./repo/src/profile_loader.py, catches specific expected exceptions narrowly, returns typed result/error values, lets unexpected errors propagate, and tests each failure path."
timeout_seconds: 360
---

`/astack:go` Clean up the Python profile loader in `./repo` (`./repo/src/profile_loader.py`; see `./repo/README.md`). When it fails in production we only get `None` with no idea whether the file was missing, the JSON was corrupt, or a field was invalid, and real programming bugs get masked. Update `./repo/src/profile_loader.py` to handle each expected failure specifically, return typed result/error values instead of `None`, allow unexpected exceptions to propagate, and add unit tests in `./repo/tests/` covering every failure path.
