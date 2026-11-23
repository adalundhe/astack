---
name: decide-by-data
description: "Settle a choice between two designs, settings or behaviours by building both and measuring them at the extremes, never by argument. Use when you are about to pick one approach over another, when someone asks which is better, or before you put a design question to the person."
---

# Decide by data

When two designs compete, build both behind one switch, force each one's failure modes at the extremes, and let the measurements choose.

Ada's words: "A|B both implementations at extremes, force their failure modes, gather metrics, traces, and logs, and make decisions from there."

**Why:** an argument about which design is better is not evidence. A design that wins in the middle of the range often loses at an edge, and the edges are where people feel it.

1. **Write the decision first.** Name the metric that decides (p50, p99 and p99.9 latency, throughput, errors, resources), the scenarios, and which result picks which side. **Why:** a decision rule written after the numbers bends to fit them.
2. **Build both arms behind one switch**, in the same build, with instruments that show why each wins or loses: counters, trace events, the reason a request waited. **Why:** two separate builds differ in more than the design, and counters explain the number.
3. **Go to the extremes the claim covers**: the smallest machine to the largest, one client to the most you claim, empty to larger than memory, idle to overloaded. Force each arm's failure mode, such as the queue that fills, the lock that convoys or the cache that misses. **Why:** a design's failure mode is its real cost, and it hides in the middle of the range.
4. **Hold everything else equal**: machine, client, data, build flags, warm state, and anything a binary learns at startup, such as a calibration. Alternate the arms (A, B, A, B), repeat until you know the run-to-run noise, and record the machine's load beside every run. **Why:** a difference smaller than the noise, or one the machine made, is no difference.
5. **Decide, then delete the loser.** The losing arm and its switch go in the same change. **Why:** two paths left in place cost upkeep forever and hide which one runs.
6. **Record it**: the command, the numbers (before and after, the noise, the run count), the winner and why, in the commit message. **Why:** the next person can rerun it instead of trusting it.

The data decides questions of fact. A trade between what the product does and what it costs is the person's, asked per **decisions-in-plain-words**, and **never-trade-functionality** limits which trades are on the table.

You skipped this when you chose a design because it "should" be faster, when the arms ran on different machines or builds, or when a result came from one run with no stated noise.

<!-- Adapts pstack's explain-the-number and benchmark-checklist skills (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
