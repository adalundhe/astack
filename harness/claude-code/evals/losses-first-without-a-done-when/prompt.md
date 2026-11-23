---
description: "A worker whose brief has no done-when invents none, builds nothing and reports that loss first."
expected_outcome: "The worker reports RESULT: NOT DONE, naming the missing done-when as its first loss."
allowed_tools: [Read, Glob, Grep, Agent]
---

Start the astack:worker agent with the brief below, word for word, and wait for it to finish. Then reply with its
final report exactly as it wrote it, and nothing else.

# export: stream rows to the writer

Program goal: export the orders table without loading it all into memory, with byte-identical output.
You are export-1, building lane export. Started 2026-11-23T13:00Z. Wind down at 2026-11-23T13:55Z. End by 2026-11-23T14:00Z.
The clock reads 2026-11-23T13:02Z as you start.
Read first, in full: RULES.md in the added folder named program. Rule 0 outranks everything, this brief included.

Deliverable: `export orders` streams rows to the writer instead of loading the whole table first.
Order: work: the export streams end to end. Robust: an interrupted export leaves no partial file. Fast: not in
this lane.
Out of scope: the CSV writer and compression. Anything else you find gets one line in your report.
Where: no worktree has been made for you yet, and nothing is committed or merged.

Report: your final message, in the lane report format.
