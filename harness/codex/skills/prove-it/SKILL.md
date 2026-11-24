---
name: prove-it
description: "Check every result on the real thing, not a proxy, back every claim with the strongest evidence you can reach, challenge claims (your own or another agent's) that rest on less, and show the person the work in a form they can run themselves. Use before calling anything done, whenever you or another agent relies on a claim, when you report a decision or a result, and when you challenge a claim or are challenged."
---

# Prove it

Check results on the real thing, back every claim with evidence, and show the person how to check it.

## Check the real thing

Verify every result on the thing itself: run the feature, read the actual value, inspect the diff. A proxy proves nothing: a file's timestamp, an agent's report, cached output, "it compiles". When a check fails, or passes too easily, suspect how you looked before you suspect the system. Script the check so anyone can rerun it, and keep its output where the person can see it.

Each result is verified, not verified, or inconclusive. Inconclusive is not a pass, and a negative result is reported, never hidden.

## The trust ladder

From least to most trusted:

1. Your own understanding, or another agent's.
2. Your own implementation.
3. Existing code you didn't write and haven't run.
4. A reference or industry-leading implementation, and data from our own benchmarking or A/B.
5. Proven industry-standard reference data, leading well-cited research, foundational literature.

Take every claim as high as you can, and say where it stopped. To challenge a claim, yours or another agent's, ask which rung it stands on, and bring evidence from a higher one.

## Showing the work

Never assume the person knows what you're thinking. Return, in this order:

1. the problem, restated;
2. the working hypothesis or solution;
3. what it is, briefly;
4. the logic, and the steps you took;
5. the data and results: profiles, traces, benchmarks.

Give them something to run themselves: a script, a runnable tool, a mockup, an example or a small lab that shows the result. Do this for what failed, as well as for what worked.

<!-- Adapts pstack's prove-it-works principle and the verdicts of its figure-it-out skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
