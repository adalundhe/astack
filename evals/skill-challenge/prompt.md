---
description: "Adversarially challenge a false slow-disk-I/O performance hypothesis and LRU file-cache proposal by proving the actual bottleneck is an O(n^2) in-memory nested loop in src/search.py while leaving ./repo untouched."
expected_outcome: "Reads challenge/SKILL.md, inspects ./repo/src/search.py, leaves ./repo clean, falsifies the disk I/O / LRU file cache hypothesis with concrete evidence, identifies the O(n^2) in-memory nested loop bottleneck, proposes an indexed O(n + m) alternative, and records an explicit Rejected verdict."
allowed_tools: [Read, Glob, Grep, Bash, Write, Edit]
---

`/astack:go` Before anyone implements the plan in `./program/hypothesis.md`, stress-test its root-cause diagnosis and proposed fix against `./repo/src/search.py`.

Leave `./repo` untouched. Inspect the actual implementation (and run a quick measurement if helpful), falsify any broken assumptions, propose a concrete alternative, and close with an explicit verdict in your final response (or `./program/CHALLENGE.md`).
